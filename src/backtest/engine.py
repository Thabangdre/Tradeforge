from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from backtest.models import Bar


@dataclass(frozen=True)
class BacktestResult:
    trades: List[float]
    equity_curve: List[float]


class BacktestEngine:
    def __init__(
        self,
        bars: list[Bar],
        *,
        symbol: str,
        strategy: Any,
        spread_model: Any,
        exec_config: Any,
        spreads: dict[str, float],
        initial_cash: float = 0.0,
    ) -> None:
        self._bars = bars
        self._strategy = strategy
        self._initial_cash = float(initial_cash)
        self._symbol = symbol
        self._spread_model = spread_model
        self._exec_config = exec_config
        self._spreads = spreads

    def run(self) -> BacktestResult:
        trade_pnls = self._strategy.generate_trade_pnls(self._bars)
        equity = [self._initial_cash]
        running = self._initial_cash
        for pnl in trade_pnls:
            running += float(pnl)
            equity.append(running)
        return BacktestResult(trades=[float(v) for v in trade_pnls], equity_curve=equity)
