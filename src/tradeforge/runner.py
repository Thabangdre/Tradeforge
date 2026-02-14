from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable

from .strategies import Strategy


@dataclass
class SessionRunner:
    strategy: Strategy
    ticks: Iterable[float]
    config: dict
    seed: int

    def run(self) -> dict:
        rng = Random(self.seed)
        risk = float(self.config.get("risk", 1.0))

        total_pnl = 0.0
        wins = 0
        gross_profit = 0.0
        gross_loss = 0.0
        trade_count = 0

        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0

        for step, tick in enumerate(self.ticks):
            signal = self.strategy.signal(float(tick), self.config, step)
            noise = (rng.random() - 0.5) * 0.02
            pnl = (signal + noise) * risk

            if abs(signal) < 1e-9:
                continue

            trade_count += 1
            total_pnl += pnl
            equity += pnl

            if pnl > 0:
                wins += 1
                gross_profit += pnl
            elif pnl < 0:
                gross_loss += pnl

            peak = max(peak, equity)
            drawdown = peak - equity
            max_drawdown = max(max_drawdown, drawdown)

        win_rate = (wins / trade_count) if trade_count else 0.0
        profit_factor = (gross_profit / abs(gross_loss)) if gross_loss < 0 else float("inf")
        expectancy = (total_pnl / trade_count) if trade_count else 0.0

        return {
            "total_pnl": total_pnl,
            "max_drawdown": max_drawdown,
            "trade_count": trade_count,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
        }
