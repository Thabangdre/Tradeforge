from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backtest.engine import BacktestEngine
from backtest.execution import ExecutionConfig
from backtest.models import Bar, EventType, IntraBarPath, Position, Side
from backtest.spread import FixedSpreadModel


class NoopStrategy:
    def on_bar(self, ctx):
        return []


def test_partial_then_be_then_stop_on_remaining_qty():
    engine = BacktestEngine(
        "TEST",
        FixedSpreadModel(0.0),
        ExecutionConfig(path=IntraBarPath.OHLC, partial_ratio=0.5, be_offset=0.0),
    )
    engine.positions.append(
        Position(id="pos-1", side=Side.BUY, entry=100.0, sl=95.0, tp=120.0, qty=1.0, open_ts=0)
    )

    bars = [
        Bar(ts=1, open=100.0, high=106.0, low=100.5, close=105.0),
        Bar(ts=2, open=105.0, high=106.0, low=99.0, close=100.0),
    ]
    result = engine.run(bars, NoopStrategy())

    assert len(result.trades) == 2
    partial_trade = result.trades[0]
    final_trade = result.trades[1]

    assert partial_trade.reason == "PARTIAL_TP"
    assert partial_trade.qty == 0.5
    assert partial_trade.exit == 105.0
    assert partial_trade.pnl == 2.5

    assert final_trade.reason == "STOP_HIT"
    assert final_trade.qty == 0.5
    assert final_trade.exit == 100.0

    event_types = [e.type for e in result.events]
    assert EventType.PARTIAL_TP in event_types
    assert EventType.BE_MOVED in event_types
    assert EventType.STOP_HIT in event_types
    assert EventType.POSITION_CLOSED in event_types

    partial_idx = event_types.index(EventType.PARTIAL_TP)
    be_idx = event_types.index(EventType.BE_MOVED)
    stop_idx = event_types.index(EventType.STOP_HIT)
    close_idx = event_types.index(EventType.POSITION_CLOSED)

    assert partial_idx < be_idx < stop_idx < close_idx
