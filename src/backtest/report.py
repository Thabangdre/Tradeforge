from __future__ import annotations

from typing import Any


def build_research_report(
    *,
    bars: list[dict[str, Any]],
    strategy: Any,
    symbol: str,
    exec_config: dict[str, Any],
    spreads: dict[str, float],
    initial_cash: float,
    top_n_losses: int,
) -> dict[str, Any]:
    signal_count = 0
    if hasattr(strategy, "generate"):
        try:
            generated = strategy.generate(bars)
            signal_count = len(generated) if generated is not None else 0
        except Exception:
            signal_count = 0

    sorted_spreads = dict(sorted(spreads.items(), key=lambda kv: kv[1]))
    closes = [b["close"] for b in bars]
    pnl = (closes[-1] - closes[0]) if len(closes) > 1 else 0.0

    return {
        "headline": {
            "symbol": symbol,
            "bars": len(bars),
            "path": "WORST_CASE",
            "approx_pnl": round(float(pnl), 5),
            "signals": signal_count,
        },
        "diagnostic": {
            "initial_cash": initial_cash,
            "top_n_losses": top_n_losses,
            "exec_config": exec_config,
        },
        "fragility": {"score": 0.0, "note": "placeholder"},
        "spread_stress": sorted_spreads,
        "fill_flip": {"flips": 0},
        "worst_trades": [],
    }


def format_research_report(report: dict[str, Any]) -> str:
    headline = report.get("headline", {})
    return (
        "US30 Research Report\n"
        f"Symbol: {headline.get('symbol', '-') }\n"
        f"Bars: {headline.get('bars', 0)}\n"
        f"Path: {headline.get('path', 'WORST_CASE')}"
    )
