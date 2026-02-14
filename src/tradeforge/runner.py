"""Session runner for deterministic strategy evaluation."""

from __future__ import annotations


class SessionRunner:
    """Runs a strategy over ticks and computes core performance metrics."""

    def __init__(self, ticks, strategy, seed: int):
        self.ticks = list(ticks)
        self.strategy = strategy
        self.seed = seed

    def run(self) -> dict:
        pnl_series: list[float] = []
        trade_pnls: list[float] = []
        cumulative = 0.0

        for index, tick in enumerate(self.ticks):
            signal = int(self.strategy.signal(index, tick))
            ret = float(tick.get("return", 0.0))
            pnl = signal * ret
            cumulative += pnl
            pnl_series.append(cumulative)
            if signal != 0:
                trade_pnls.append(pnl)

        gross_profit = sum(x for x in trade_pnls if x > 0)
        gross_loss = abs(sum(x for x in trade_pnls if x < 0))
        wins = sum(1 for x in trade_pnls if x > 0)
        trade_count = len(trade_pnls)

        peak = float("-inf")
        max_dd = 0.0
        for value in pnl_series:
            peak = max(peak, value)
            max_dd = max(max_dd, peak - value)

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        win_rate = wins / trade_count if trade_count else 0.0
        expectancy = sum(trade_pnls) / trade_count if trade_count else 0.0

        return {
            "total_pnl": cumulative,
            "max_drawdown": max_dd,
            "trade_count": trade_count,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
        }
