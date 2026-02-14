from __future__ import annotations

from statistics import median
from typing import Any

from backtest.engine import BacktestResult


def _profit_factor(trades: list[float]) -> float | None:
    gains = sum(p for p in trades if p > 0)
    losses = -sum(p for p in trades if p < 0)
    if losses == 0:
        return None if gains == 0 else float("inf")
    return gains / losses


def _max_drawdown(equity_curve: list[float]) -> float:
    peak = float("-inf")
    max_dd = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        max_dd = max(max_dd, peak - value)
    return max_dd


def build_research_report(result: BacktestResult, *, top_n_losses: int = 10) -> dict[str, Any]:
    trades = [float(v) for v in result.trades]
    headline = {
        "profit_factor": _profit_factor(trades),
        "max_drawdown": _max_drawdown(result.equity_curve),
        "net_pnl": float(sum(trades)),
    }
    losses = sorted((p for p in trades if p < 0), key=lambda x: x)
    top_losses = losses[:top_n_losses]
    fragility = float(median(abs(v) for v in top_losses)) if top_losses else 0.0
    return {
        "headline": headline,
        "fragility": fragility,
        "trades": {"count": len(trades), "top_losses": top_losses},
    }
