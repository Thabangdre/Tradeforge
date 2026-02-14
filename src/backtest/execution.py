from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import Bar, Event, EventType, IntraBarPath, OrderType, PendingOrder, Position, Side


@dataclass(slots=True)
class ExecutionConfig:
    path: IntraBarPath = IntraBarPath.WORST_CASE
    partial_ratio: float = 0.5
    be_offset: float = 0.0
    commission_per_trade: float = 0.0
    slippage: float = 0.0
    sort_triggers_by_distance_from_open: bool = True


def bid_ask_from_mid(mid: float, spread: float) -> tuple[float, float]:
    half = spread / 2.0
    return mid - half, mid + half


def _sort_levels(levels: list[tuple[float, str]], bar: Bar, sort_by_distance: bool) -> list[tuple[float, str]]:
    if not sort_by_distance:
        return levels
    return sorted(levels, key=lambda item: (abs(item[0] - bar.open), item[1]))


def _order_triggered(order: PendingOrder, phase: str, bar: Bar) -> bool:
    if order.type == OrderType.MARKET:
        return phase == "OPEN"
    if phase == "HIGH":
        return (
            (order.side == Side.BUY and order.type == OrderType.STOP and order.price is not None and bar.high >= order.price)
            or (order.side == Side.SELL and order.type == OrderType.LIMIT and order.price is not None and bar.high >= order.price)
        )
    if phase == "LOW":
        return (
            (order.side == Side.BUY and order.type == OrderType.LIMIT and order.price is not None and bar.low <= order.price)
            or (order.side == Side.SELL and order.type == OrderType.STOP and order.price is not None and bar.low <= order.price)
        )
    return False


def _partial_level(pos: Position) -> float:
    risk = abs(pos.entry - pos.initial_sl)
    return pos.entry + risk if pos.side == Side.BUY else pos.entry - risk


def _be_level(pos: Position, offset: float) -> float:
    return pos.entry + offset if pos.side == Side.BUY else pos.entry - offset


def _apply_slippage(price: float, side: Side, opening: bool, slippage: float) -> float:
    if slippage == 0:
        return price
    direction = 1.0 if side == Side.BUY else -1.0
    signed = direction if opening else -direction
    return price + signed * slippage


def process_bar_ohlc(
    *,
    bar: Bar,
    pending_orders: list[PendingOrder],
    positions: list[Position],
    events: list[Event],
    config: ExecutionConfig,
    on_order_filled: Callable[[PendingOrder, float], None],
    close_position: Callable[[Position, float, str], None],
    partial_close: Callable[[Position, float, float], None],
    move_sl: Callable[[Position, float], None],
) -> None:
    for phase in ("OPEN", "HIGH", "LOW", "CLOSE"):
        triggered = [o for o in pending_orders if _order_triggered(o, phase, bar)]
        if triggered:
            levels = [(o.price if o.price is not None else bar.open, o.id) for o in triggered]
            order_map = {o.id: o for o in triggered}
            for _, oid in _sort_levels(levels, bar, config.sort_triggers_by_distance_from_open):
                order = order_map[oid]
                if order not in pending_orders:
                    continue
                trigger_price = order.price if order.price is not None else bar.open
                fill = _apply_slippage(trigger_price, order.side, True, config.slippage)
                pending_orders.remove(order)
                events.append(Event(EventType.ORDER_FILLED, bar.ts, {"order_id": order.id, "price": fill}))
                on_order_filled(order, fill)

        active_positions = list(positions)
        for pos in active_positions:
            if pos not in positions:
                continue
            if phase == "HIGH":
                if pos.side == Side.BUY and bar.high >= pos.tp:
                    close_position(pos, _apply_slippage(pos.tp, pos.side, False, config.slippage), "TP_HIT")
                    continue
                if pos.side == Side.SELL and bar.high >= pos.sl:
                    close_position(pos, _apply_slippage(pos.sl, pos.side, False, config.slippage), "STOP_HIT")
                    continue
                if pos.side == Side.BUY:
                    p_level = _partial_level(pos)
                    if not pos.partial_taken and bar.high >= p_level:
                        partial_close(pos, p_level, config.partial_ratio)
                    if pos in positions and not pos.be_moved and bar.high >= p_level:
                        move_sl(pos, _be_level(pos, config.be_offset))
            elif phase == "LOW":
                if pos.side == Side.BUY and bar.low <= pos.sl:
                    close_position(pos, _apply_slippage(pos.sl, pos.side, False, config.slippage), "STOP_HIT")
                    continue
                if pos.side == Side.SELL and bar.low <= pos.tp:
                    close_position(pos, _apply_slippage(pos.tp, pos.side, False, config.slippage), "TP_HIT")
                    continue
                if pos.side == Side.SELL:
                    p_level = _partial_level(pos)
                    if not pos.partial_taken and bar.low <= p_level:
                        partial_close(pos, p_level, config.partial_ratio)
                    if pos in positions and not pos.be_moved and bar.low <= p_level:
                        move_sl(pos, _be_level(pos, config.be_offset))


def process_bar_worst_case(
    *,
    bar: Bar,
    pending_orders: list[PendingOrder],
    positions: list[Position],
    events: list[Event],
    config: ExecutionConfig,
    on_order_filled: Callable[[PendingOrder, float], None],
    close_position: Callable[[Position, float, str], None],
    partial_close: Callable[[Position, float, float], None],
    move_sl: Callable[[Position, float], None],
) -> None:
    # Deterministic simplification: process all pending fills first using the bar range,
    # then evaluate exits where SL is chosen if both SL and TP are touched.
    triggered: list[PendingOrder] = []
    for order in pending_orders:
        if order.type == OrderType.MARKET:
            triggered.append(order)
        elif order.price is not None and bar.low <= order.price <= bar.high:
            triggered.append(order)

    levels = [(o.price if o.price is not None else bar.open, o.id) for o in triggered]
    order_map = {o.id: o for o in triggered}
    for _, oid in _sort_levels(levels, bar, config.sort_triggers_by_distance_from_open):
        order = order_map[oid]
        if order not in pending_orders:
            continue
        trigger_price = order.price if order.price is not None else bar.open
        fill = _apply_slippage(trigger_price, order.side, True, config.slippage)
        pending_orders.remove(order)
        events.append(Event(EventType.ORDER_FILLED, bar.ts, {"order_id": order.id, "price": fill}))
        on_order_filled(order, fill)

    for pos in list(positions):
        if pos.side == Side.BUY:
            tp_hit = bar.high >= pos.tp
            sl_hit = bar.low <= pos.sl
            if tp_hit and sl_hit:
                close_position(pos, _apply_slippage(pos.sl, pos.side, False, config.slippage), "STOP_HIT")
            elif sl_hit:
                close_position(pos, _apply_slippage(pos.sl, pos.side, False, config.slippage), "STOP_HIT")
            elif tp_hit:
                if not pos.partial_taken:
                    partial_close(pos, _partial_level(pos), config.partial_ratio)
                    if pos in positions and not pos.be_moved:
                        move_sl(pos, _be_level(pos, config.be_offset))
                close_position(pos, _apply_slippage(pos.tp, pos.side, False, config.slippage), "TP_HIT")
        else:
            tp_hit = bar.low <= pos.tp
            sl_hit = bar.high >= pos.sl
            if tp_hit and sl_hit:
                close_position(pos, _apply_slippage(pos.sl, pos.side, False, config.slippage), "STOP_HIT")
            elif sl_hit:
                close_position(pos, _apply_slippage(pos.sl, pos.side, False, config.slippage), "STOP_HIT")
            elif tp_hit:
                if not pos.partial_taken:
                    partial_close(pos, _partial_level(pos), config.partial_ratio)
                    if pos in positions and not pos.be_moved:
                        move_sl(pos, _be_level(pos, config.be_offset))
                close_position(pos, _apply_slippage(pos.tp, pos.side, False, config.slippage), "TP_HIT")
