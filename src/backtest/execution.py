from __future__ import annotations

from .models import Bar, ExecutionConfig, Order, OrderType, Position, Side
from .spread import bid_ask_from_mid


def _apply_slippage(price: float, side: Side, slippage: float) -> float:
    # Deterministic directional slippage: BUY worsens up, SELL worsens down.
    if side == Side.BUY:
        return price + slippage
    return price - slippage


def fill_entry_price(order: Order, bar: Bar, spread: float, config: ExecutionConfig) -> float:
    bid, ask = bid_ask_from_mid(bar.close, spread)
    if order.side == Side.BUY:
        if order.order_type == OrderType.MARKET:
            raw = ask
        else:
            trigger = order.trigger_price if order.trigger_price is not None else ask
            raw = max(trigger, ask)
    else:
        if order.order_type == OrderType.MARKET:
            raw = bid
        else:
            trigger = order.trigger_price if order.trigger_price is not None else bid
            raw = min(trigger, bid)
    return _apply_slippage(raw, order.side, config.slippage)


def _exit_fill_price(position: Position, level_price: float, bid: float, ask: float, config: ExecutionConfig) -> float:
    if position.side == Side.BUY:
        raw = min(level_price, bid)
        return _apply_slippage(raw, Side.SELL, config.slippage)
    raw = max(level_price, ask)
    return _apply_slippage(raw, Side.BUY, config.slippage)


def _hits(position: Position, bar: Bar) -> tuple[bool, bool, bool]:
    if position.side == Side.BUY:
        tp_hit = position.tp is not None and bar.high >= position.tp
        sl_hit = position.sl is not None and bar.low <= position.sl
        partial_hit = (
            position.partial_tp is not None and not position.partial_done and bar.high >= position.partial_tp
        )
    else:
        tp_hit = position.tp is not None and bar.low <= position.tp
        sl_hit = position.sl is not None and bar.high >= position.sl
        partial_hit = (
            position.partial_tp is not None and not position.partial_done and bar.low <= position.partial_tp
        )
    return tp_hit, sl_hit, partial_hit


def process_bar_ohlc(position: Position, bar: Bar, spread: float, config: ExecutionConfig) -> dict:
    bid, ask = bid_ask_from_mid(bar.close, spread)
    tp_hit, sl_hit, partial_hit = _hits(position, bar)
    action = {"partial": None, "be_move": None, "close": None}

    if partial_hit and position.partial_qty:
        action["partial"] = {
            "qty": min(position.partial_qty, position.remaining_qty),
            "price": _exit_fill_price(position, position.partial_tp, bid, ask, config),
            "reason": "partial_tp",
        }
        if position.move_be_on_partial and position.sl is not None:
            action["be_move"] = {"new_sl": position.entry_price}

    if tp_hit and sl_hit:
        reason = "tp"
        level = position.tp
    elif tp_hit:
        reason = "tp"
        level = position.tp
    elif sl_hit:
        reason = "sl"
        level = position.sl
    else:
        reason = None
        level = None

    if reason and level is not None:
        action["close"] = {
            "price": _exit_fill_price(position, level, bid, ask, config),
            "reason": reason,
        }
    return action


def process_bar_worst_case(position: Position, bar: Bar, spread: float, config: ExecutionConfig) -> dict:
    bid, ask = bid_ask_from_mid(bar.close, spread)
    tp_hit, sl_hit, partial_hit = _hits(position, bar)
    action = {"partial": None, "be_move": None, "close": None}

    if partial_hit and position.partial_qty:
        action["partial"] = {
            "qty": min(position.partial_qty, position.remaining_qty),
            "price": _exit_fill_price(position, position.partial_tp, bid, ask, config),
            "reason": "partial_tp",
        }
        if position.move_be_on_partial and position.sl is not None:
            action["be_move"] = {"new_sl": position.entry_price}

    if tp_hit and sl_hit:
        reason = "sl"
        level = position.sl
    elif sl_hit:
        reason = "sl"
        level = position.sl
    elif tp_hit:
        reason = "tp"
        level = position.tp
    else:
        reason = None
        level = None

    if reason and level is not None:
        action["close"] = {
            "price": _exit_fill_price(position, level, bid, ask, config),
            "reason": reason,
        }
    return action
