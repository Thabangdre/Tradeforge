from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backtest.engine import BacktestEngine
from backtest.execution import ExecutionConfig
from backtest.models import Bar, IntraBarPath, Position, Side
from backtest.spread import FixedSpreadModel


class NoopStrategy:
    def on_bar(self, ctx):
        return []


def _run_with_mode(mode: IntraBarPath):
    engine = BacktestEngine("TEST", FixedSpreadModel(0.0), ExecutionConfig(path=mode))
    engine.positions.append(
        Position(id="pos-1", side=Side.BUY, entry=100.0, sl=90.0, tp=110.0, qty=1.0, open_ts=0)
    )
    bar = Bar(ts=1, open=100.0, high=111.0, low=89.0, close=100.0)
    return engine.run([bar], NoopStrategy())


def test_ohlc_prefers_tp_before_low_for_long():
    result = _run_with_mode(IntraBarPath.OHLC)
    assert result.trades[-1].reason == "TP_HIT"
    assert result.trades[-1].exit == 110.0


def test_worst_case_prefers_sl_when_both_touched():
    result = _run_with_mode(IntraBarPath.WORST_CASE)
    assert result.trades[-1].reason == "STOP_HIT"
    assert result.trades[-1].exit == 90.0
