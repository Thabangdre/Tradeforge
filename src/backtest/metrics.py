from __future__ import annotations

from typing import Any

from .models import Trade


def compute_metrics(trades: list[Trade], equity_curve: list[tuple[Any, float]], initial_cash: float) -> dict[str, Any]:
    total = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = sum(t.pnl for t in losses)
    net_pnl = sum(t.pnl for t in trades)

    peak = initial_cash
    max_dd = 0.0
    for _, equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd

    profit_factor = float("inf") if gross_loss == 0 and gross_profit > 0 else (gross_profit / abs(gross_loss) if gross_loss != 0 else 0.0)

    return {
        "total_trades": total,
        "win_rate": (len(wins) / total) if total else 0.0,
        "net_pnl": net_pnl,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "expectancy": (net_pnl / total) if total else 0.0,
        "max_drawdown": max_dd,
        "avg_r": None,
    }
