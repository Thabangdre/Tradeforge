from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context_adapter import StrategyContext
from .execution import ExecutionConfig, process_bar_ohlc, process_bar_worst_case
from .metrics import compute_metrics
from .models import Bar, Event, EventType, IntraBarPath, PendingOrder, Position, Trade
from .spread import SpreadModel


@dataclass(slots=True)
class BacktestResult:
    trades: list[Trade]
    events: list[Event]
    metrics: dict[str, Any]
    equity_curve: list[tuple[Any, float]]


class BacktestEngine:
    def __init__(self, symbol: str, spread_model: SpreadModel, exec_config: ExecutionConfig) -> None:
        self.symbol = symbol
        self.spread_model = spread_model
        self.exec_config = exec_config
        self.pending_orders: list[PendingOrder] = []
        self.positions: list[Position] = []
        self.trades: list[Trade] = []
        self.events: list[Event] = []
        self.equity_curve: list[tuple[Any, float]] = []
        self.realized_pnl: float = 0.0
        self._trade_seq: int = 0

    def _intent_type(self, intent: Any) -> str:
        if isinstance(intent, dict):
            return intent.get("type", "")
        return getattr(intent, "type", "")

    def _intent_get(self, intent: Any, key: str, default: Any = None) -> Any:
        if isinstance(intent, dict):
            return intent.get(key, default)
        return getattr(intent, key, default)

    def _open_position(self, bar: Bar, order: PendingOrder, fill_price: float) -> None:
        pos = Position(
            id=order.id,
            side=order.side,
            entry=fill_price,
            sl=order.sl,
            tp=order.tp,
            qty=order.qty,
            setup_id=order.setup_id,
            open_ts=bar.ts,
        )
        self.positions.append(pos)
        self.events.append(Event(EventType.POSITION_OPENED, bar.ts, {"position_id": pos.id, "entry": fill_price}))
        self.realized_pnl -= self.exec_config.commission_per_trade

    def _close_qty(self, pos: Position, exit_price: float, qty: float, ts: Any, reason: str) -> None:
        pnl = (exit_price - pos.entry) * qty if pos.side.value == "BUY" else (pos.entry - exit_price) * qty
        pnl -= self.exec_config.commission_per_trade
        self.realized_pnl += pnl
        self._trade_seq += 1
        self.trades.append(
            Trade(
                id=f"{pos.id}:{self._trade_seq}",
                side=pos.side,
                entry=pos.entry,
                exit=exit_price,
                qty=qty,
                pnl=pnl,
                open_ts=pos.open_ts,
                close_ts=ts,
                reason=reason,
            )
        )

    def _close_position(self, bar: Bar, pos: Position, exit_price: float, reason: str) -> None:
        qty = pos.remaining_qty or 0.0
        if qty <= 0:
            return
        self._close_qty(pos, exit_price, qty, bar.ts, reason)
        evt = EventType.STOP_HIT if reason == "STOP_HIT" else EventType.TP_HIT
        self.events.append(Event(evt, bar.ts, {"position_id": pos.id, "price": exit_price}))
        self.events.append(Event(EventType.POSITION_CLOSED, bar.ts, {"position_id": pos.id, "reason": reason, "price": exit_price}))
        self.positions.remove(pos)

    def _partial_close(self, bar: Bar, pos: Position, level: float, ratio: float) -> None:
        rem = pos.remaining_qty or 0.0
        qty = rem * ratio
        if qty <= 0:
            return
        pos.remaining_qty = rem - qty
        pos.partial_taken = True
        self._close_qty(pos, level, qty, bar.ts, "PARTIAL_TP")
        self.events.append(Event(EventType.PARTIAL_TP, bar.ts, {"position_id": pos.id, "price": level, "qty": qty}))

    def _move_sl(self, bar: Bar, pos: Position, new_sl: float) -> None:
        pos.sl = new_sl
        pos.be_moved = True
        self.events.append(Event(EventType.BE_MOVED, bar.ts, {"position_id": pos.id, "new_sl": new_sl}))

    def _apply_intents(self, bar: Bar, intents: list[Any]) -> None:
        cancels = [i for i in intents if self._intent_type(i) == "CANCEL_ORDERS"]
        placements = [i for i in intents if self._intent_type(i) == "PLACE_ORDER"]
        sl_updates = [i for i in intents if self._intent_type(i) == "UPDATE_POSITION_SL"]

        for intent in cancels:
            setup_id = self._intent_get(intent, "setup_id")
            for order in list(self.pending_orders):
                if setup_id is None or order.setup_id == setup_id:
                    self.pending_orders.remove(order)
                    self.events.append(Event(EventType.ORDER_CANCELED, bar.ts, {"order_id": order.id}))

        for intent in placements:
            order = self._intent_get(intent, "order")
            if not isinstance(order, PendingOrder):
                continue
            self.pending_orders.append(order)
            self.events.append(Event(EventType.ORDER_PLACED, bar.ts, {"order_id": order.id}))

        for intent in sl_updates:
            pid = self._intent_get(intent, "position_id")
            new_sl = self._intent_get(intent, "new_sl")
            for pos in self.positions:
                if pos.id == pid:
                    pos.sl = float(new_sl)
                    self.events.append(Event(EventType.BE_MOVED, bar.ts, {"position_id": pos.id, "new_sl": pos.sl}))
                    break

    def run(self, bars: list[Bar], strategy: Any, initial_cash: float = 0.0, history_limit: int = 500) -> BacktestResult:
        history: list[Bar] = []
        for bar in bars:
            spread = self.spread_model.get_spread(bar, self.symbol)
            ctx = StrategyContext(
                bar=bar,
                history=history[-history_limit:],
                _spread=spread,
                pending_orders=tuple(self.pending_orders),
                positions=tuple(self.positions),
            )
            intents = strategy.on_bar(ctx) or []
            self._apply_intents(bar, intents)

            def on_order_filled(order: PendingOrder, fill_price: float) -> None:
                self._open_position(bar, order, fill_price)

            def close_position(pos: Position, exit_price: float, reason: str) -> None:
                self._close_position(bar, pos, exit_price, reason)

            def partial_close(pos: Position, level: float, ratio: float) -> None:
                self._partial_close(bar, pos, level, ratio)

            def move_sl(pos: Position, new_sl: float) -> None:
                self._move_sl(bar, pos, new_sl)

            if self.exec_config.path == IntraBarPath.OHLC:
                process_bar_ohlc(
                    bar=bar,
                    pending_orders=self.pending_orders,
                    positions=self.positions,
                    events=self.events,
                    config=self.exec_config,
                    on_order_filled=on_order_filled,
                    close_position=close_position,
                    partial_close=partial_close,
                    move_sl=move_sl,
                )
            else:
                process_bar_worst_case(
                    bar=bar,
                    pending_orders=self.pending_orders,
                    positions=self.positions,
                    events=self.events,
                    config=self.exec_config,
                    on_order_filled=on_order_filled,
                    close_position=close_position,
                    partial_close=partial_close,
                    move_sl=move_sl,
                )

            self.equity_curve.append((bar.ts, initial_cash + self.realized_pnl))
            history.append(bar)

        metrics = compute_metrics(self.trades, self.equity_curve, initial_cash)
        return BacktestResult(
            trades=list(self.trades),
            events=list(self.events),
            metrics=metrics,
            equity_curve=list(self.equity_curve),
        )
