from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backtest.engine import BacktestEngine
from backtest.execution import ExecutionConfig
from backtest.models import Bar, IntraBarPath, OrderType, PendingOrder, Side
from backtest.spread import FixedSpreadModel


class DeterministicStrategy:
    def __init__(self) -> None:
        self.placed = False

    def on_bar(self, ctx):
        _ = ctx.get_spread()
        if self.placed:
            return []
        self.placed = True
        return [
            {
                "type": "PLACE_ORDER",
                "order": PendingOrder(
                    id="ord-1",
                    side=Side.BUY,
                    type=OrderType.LIMIT,
                    price=100.0,
                    sl=95.0,
                    tp=110.0,
                    qty=1.0,
                    setup_id="setup-a",
                ),
            }
        ]


def test_backtest_engine_is_deterministic():
    bars = [
        Bar(ts=i, open=100.0, high=101.0, low=99.0, close=100.0)
        if i == 0
        else Bar(ts=i, open=100.0, high=106.0 if i == 1 else 101.0, low=99.0, close=100.0)
        for i in range(20)
    ]

    cfg = ExecutionConfig(path=IntraBarPath.OHLC, partial_ratio=0.5)
    engine_1 = BacktestEngine("TEST", FixedSpreadModel(0.2), cfg)
    engine_2 = BacktestEngine("TEST", FixedSpreadModel(0.2), cfg)

    result_1 = engine_1.run(copy.deepcopy(bars), DeterministicStrategy())
    result_2 = engine_2.run(copy.deepcopy(bars), DeterministicStrategy())

    assert len(result_1.events) == len(result_2.events)
    assert [(e.type, e.data) for e in result_1.events] == [(e.type, e.data) for e in result_2.events]
    assert result_1.metrics == result_2.metrics
    assert result_1.trades == result_2.trades
