from __future__ import annotations

from typing import Any

from .analysis import (
    build_trade_audit,
    compare_paths,
    fill_flip_stats,
    intrabar_fragility,
    stress_spread,
)


def _result_metrics(result) -> dict[str, Any]:
    return {
        "total_pnl": result.total_pnl,
        "ending_cash": result.ending_cash,
        "trade_count": len(result.trades),
        "event_count": len(result.events),
    }


def build_research_report(
    bars,
    strategy,
    symbol: str,
    exec_config,
    spreads: dict[str, float],
    initial_cash: float = 0.0,
    top_n_losses: int = 10,
) -> dict[str, Any]:
    paths = compare_paths(
        bars=bars,
        strategy=strategy,
        symbol=symbol,
        exec_config=exec_config,
        initial_cash=initial_cash,
    )
    worst = paths["WORST_CASE"]
    ohlc = paths["OHLC"]

    fragility = intrabar_fragility(worst, ohlc)
    spread_stress = stress_spread(
        bars=bars,
        strategy=strategy,
        symbol=symbol,
        exec_config=exec_config,
        spreads=spreads,
        initial_cash=initial_cash,
    )
    fill_flip = fill_flip_stats(worst.events)

    audit_entries = build_trade_audit(worst.events, worst.trades)
    audit_by_trade_id = {entry["trade_id"]: entry for entry in audit_entries}

    sorted_worst = sorted(
        worst.trades,
        key=lambda trade: (trade.pnl, trade.close_ts, trade.trade_id),
    )
    worst_trades = []
    for trade in sorted_worst[:top_n_losses]:
        worst_trades.append(
            {
                "trade_id": trade.trade_id,
                "side": trade.side,
                "entry": trade.entry,
                "exit": trade.exit,
                "pnl": trade.pnl,
                "reason": trade.reason,
                "open_ts": trade.open_ts,
                "close_ts": trade.close_ts,
                "audit": audit_by_trade_id.get(trade.trade_id),
            }
        )

    return {
        "headline": _result_metrics(worst),
        "diagnostic": _result_metrics(ohlc),
        "fragility": fragility,
        "spread_stress": spread_stress,
        "fill_flip": fill_flip,
        "worst_trades": worst_trades,
    }


def format_research_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    headline = report["headline"]
    diagnostic = report["diagnostic"]
    lines.append(
        "headline: pnl={total_pnl:.2f} cash={ending_cash:.2f} trades={trade_count} events={event_count}".format(
            **headline
        )
    )
    lines.append(
        "diagnostic: pnl={total_pnl:.2f} cash={ending_cash:.2f} trades={trade_count} events={event_count}".format(
            **diagnostic
        )
    )
    lines.append(f"fragility: {report['fragility']:.6f}")

    lines.append("spread_stress:")
    summary = report["spread_stress"].get("summary", {})
    for regime in sorted(summary):
        metrics = summary[regime]
        lines.append(
            "  {regime}: spread={spread:.4f} pnl={total_pnl:.2f} cash={ending_cash:.2f} trades={trade_count:.0f}".format(
                regime=regime,
                **metrics,
            )
        )

    fill_flip = report["fill_flip"]
    ordered_fill_flip = ", ".join(f"{k}={fill_flip[k]}" for k in sorted(fill_flip))
    lines.append(f"fill_flip: {ordered_fill_flip}")

    lines.append("worst_trades:")
    for trade in report.get("worst_trades", []):
        lines.append(
            "  {trade_id}: pnl={pnl:.2f} reason={reason}".format(
                trade_id=trade["trade_id"],
                pnl=trade["pnl"],
                reason=trade["reason"],
            )
        )

    return "\n".join(lines)
