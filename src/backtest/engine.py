from __future__ import annotations

from dataclasses import replace
from typing import Callable, Iterable

from .execution import fill_entry_price, process_bar_ohlc, process_bar_worst_case
from .models import (
    BacktestResult,
    Bar,
    Event,
    ExecutionConfig,
    IntraBarPath,
    Metrics,
    Order,
    Position,
    Side,
    Trade,
)
from .spread import bid_ask_from_mid


def _calc_pnl(side: Side, entry: float, exit_price: float, qty: float) -> float:
    if side == Side.BUY:
        return (exit_price - entry) * qty
    return (entry - exit_price) * qty


def _max_drawdown(equity_curve: list[tuple[object, float]]) -> float:
    peak = float("-inf")
    max_dd = 0.0
    for _, eq in equity_curve:
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    return max_dd


def run_backtest(
    bars: Iterable[Bar],
    strategy: Callable[[int, Bar, list[Position]], list[Order]] | object,
    symbol: str,
    spread_model,
    exec_config: ExecutionConfig,
    initial_cash: float = 0.0,
) -> BacktestResult:
    positions: list[Position] = []
    trades: list[Trade] = []
    events: list[Event] = []
    equity_curve: list[tuple[object, float]] = []
    realized_pnl = 0.0
    next_trade_id = 1

    bars_list = list(bars)
    for i, bar in enumerate(bars_list):
        spread = spread_model.get_spread(symbol, bar.ts)
        process_fn = process_bar_worst_case if exec_config.path == IntraBarPath.WORST_CASE else process_bar_ohlc

        # Process existing positions.
        for pos in list(positions):
            action = process_fn(pos, bar, spread, exec_config)
            if action["partial"]:
                qty = action["partial"]["qty"]
                price = action["partial"]["price"]
                pos.remaining_qty -= qty
                realized_pnl += _calc_pnl(pos.side, pos.entry_price, price, qty)
                pos.partial_done = True
                events.append(
                    Event(bar.ts, "PARTIAL_TP", pos.trade_id, {"qty": qty, "price": price})
                )
            if action["be_move"] and not pos.be_moved:
                pos.sl = action["be_move"]["new_sl"]
                pos.be_moved = True
                events.append(Event(bar.ts, "BE_MOVED", pos.trade_id, {"new_sl": pos.sl}))
            if action["close"] and pos.remaining_qty > 0:
                px = action["close"]["price"]
                rsn = action["close"]["reason"]
                qty = pos.remaining_qty
                realized_pnl += _calc_pnl(pos.side, pos.entry_price, px, qty)
                pos.remaining_qty = 0
                t = next(t for t in trades if t.trade_id == pos.trade_id)
                t.exit_ts = bar.ts
                t.exit_price = px
                t.reason = rsn
                t.pnl = _calc_pnl(pos.side, t.entry_price, px, t.qty)
                events.append(Event(bar.ts, "POSITION_CLOSED", pos.trade_id, {"price": px, "reason": rsn}))
                positions.remove(pos)

        # Strategy entries
        orders: list[Order]
        if callable(strategy):
            orders = strategy(i, bar, positions)
        else:
            orders = strategy.on_bar(i, bar, positions)
        for order in orders:
            price = fill_entry_price(order, bar, spread, exec_config)
            pos = Position(
                trade_id=next_trade_id,
                side=order.side,
                entry_ts=bar.ts,
                entry_price=price,
                qty=order.qty,
                remaining_qty=order.qty,
                tp=order.tp,
                sl=order.sl,
                partial_tp=order.partial_tp,
                partial_qty=order.partial_qty,
                move_be_on_partial=order.move_be_on_partial,
            )
            positions.append(pos)
            trades.append(Trade(next_trade_id, order.side, bar.ts, price, order.qty))
            events.append(Event(bar.ts, "ORDER_FILLED", next_trade_id, {"price": price, "side": order.side.value}))
            events.append(Event(bar.ts, "POSITION_OPENED", next_trade_id, {"price": price, "qty": order.qty}))
            next_trade_id += 1

        # Mark-to-market with close-derived bid/ask.
        bid, ask = bid_ask_from_mid(bar.close, spread)
        unrealized = 0.0
        for pos in positions:
            if pos.side == Side.BUY:
                unrealized += (bid - pos.entry_price) * pos.remaining_qty
            else:
                unrealized += (pos.entry_price - ask) * pos.remaining_qty
        equity_curve.append((bar.ts, initial_cash + realized_pnl + unrealized))

    wins = [t for t in trades if t.exit_price is not None and t.pnl > 0]
    losses = [t for t in trades if t.exit_price is not None and t.pnl < 0]
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0
    closed = [t for t in trades if t.exit_price is not None]
    metrics = Metrics(
        net_pnl=(equity_curve[-1][1] - initial_cash) if equity_curve else 0.0,
        profit_factor=profit_factor,
        max_drawdown=_max_drawdown(equity_curve),
        total_trades=len(closed),
        win_rate=(len(wins) / len(closed)) if closed else 0.0,
    )
    return BacktestResult(equity_curve=equity_curve, trades=trades, events=events, metrics=metrics)


def compare_paths(
    bars,
    strategy,
    symbol: str,
    spread_model,
    exec_config_base: ExecutionConfig,
    initial_cash: float = 0.0,
):
    worst = run_backtest(
        bars=bars,
        strategy=strategy,
        symbol=symbol,
        spread_model=spread_model,
        exec_config=replace(exec_config_base, path=IntraBarPath.WORST_CASE),
        initial_cash=initial_cash,
    )
    ohlc = run_backtest(
        bars=bars,
        strategy=strategy,
        symbol=symbol,
        spread_model=spread_model,
        exec_config=replace(exec_config_base, path=IntraBarPath.OHLC),
        initial_cash=initial_cash,
    )

    def summarize(res: BacktestResult):
        m = res.metrics
        return {
            "net_pnl": m.net_pnl,
            "profit_factor": m.profit_factor,
            "max_drawdown": m.max_drawdown,
            "total_trades": m.total_trades,
            "win_rate": m.win_rate,
        }

    return {"worst": worst, "ohlc": ohlc, "summary": {"worst": summarize(worst), "ohlc": summarize(ohlc)}}
