from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from .models import BacktestResult, Event


def compare_paths(
    bars,
    strategy,
    symbol: str,
    exec_config,
    initial_cash: float = 0.0,
) -> dict[str, BacktestResult]:
    return {
        "WORST_CASE": strategy.run(
            bars=bars,
            symbol=symbol,
            exec_config=exec_config,
            initial_cash=initial_cash,
            path="WORST_CASE",
        ),
        "OHLC": strategy.run(
            bars=bars,
            symbol=symbol,
            exec_config=exec_config,
            initial_cash=initial_cash,
            path="OHLC",
        ),
    }


def stress_spread(
    bars,
    strategy,
    symbol: str,
    exec_config,
    spreads: dict[str, float],
    initial_cash: float = 0.0,
) -> dict[str, Any]:
    summary: dict[str, dict[str, float]] = {}
    for regime, spread in sorted(spreads.items(), key=lambda item: item[0]):
        result = strategy.run(
            bars=bars,
            symbol=symbol,
            exec_config=exec_config,
            initial_cash=initial_cash,
            path="WORST_CASE",
            spread=spread,
        )
        summary[regime] = {
            "spread": spread,
            "total_pnl": result.total_pnl,
            "ending_cash": result.ending_cash,
            "trade_count": float(len(result.trades)),
        }

    return {"summary": summary}


def intrabar_fragility(worst: BacktestResult, ohlc: BacktestResult) -> float:
    denom = max(1.0, abs(ohlc.total_pnl))
    return round(abs(worst.total_pnl - ohlc.total_pnl) / denom, 6)


def fill_flip_stats(events: list[Event]) -> dict[str, Any]:
    counts = Counter(event.type for event in events)
    fills = counts.get("FILL", 0)
    flips = counts.get("FLIP", 0)
    partials = counts.get("PARTIAL", 0)
    breakeven = counts.get("BREAKEVEN", 0)
    return {
        "fills": fills,
        "flips": flips,
        "partials": partials,
        "breakeven": breakeven,
        "fill_to_flip_ratio": round(flips / fills, 6) if fills else 0.0,
    }


def build_trade_audit(events: list[Event], trades) -> list[dict[str, Any]]:
    by_trade: dict[str, list[dict[str, Any]]] = {trade.trade_id: [] for trade in trades}
    for event in sorted(events, key=lambda e: (e.ts, e.trade_id, e.type)):
        if event.trade_id in by_trade:
            by_trade[event.trade_id].append(asdict(event))

    audits = []
    for trade in trades:
        audits.append(
            {
                "trade_id": trade.trade_id,
                "event_count": len(by_trade[trade.trade_id]),
                "timeline": by_trade[trade.trade_id],
            }
        )
    return audits
