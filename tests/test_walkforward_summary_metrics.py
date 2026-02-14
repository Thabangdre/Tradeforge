from backtest.execution import ExecutionConfig
from backtest.models import Bar
from backtest.spread import SpreadModel
from backtest.walkforward import WalkForwardSpec, walk_forward


class SegmentPatternStrategy:
    def __init__(self, seg_id: int) -> None:
        self.seg_id = seg_id

    def generate_trade_pnls(self, bars: list[Bar]) -> list[float]:
        return [2.0, -1.0] if self.seg_id % 2 == 0 else [1.0, -2.0]


def _bars(n: int) -> list[Bar]:
    return [Bar(timestamp=i, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0) for i in range(n)]


def test_walk_forward_summary_metrics() -> None:
    def factory(ctx: dict[str, object]) -> SegmentPatternStrategy:
        return SegmentPatternStrategy(seg_id=int(ctx["seg_id"]))

    result = walk_forward(
        _bars(80),
        factory,
        symbol="X",
        spread_model=SpreadModel(),
        exec_config=ExecutionConfig(),
        spreads={"X": 0.0},
        spec=WalkForwardSpec(train_bars=20, test_bars=10, step_bars=10),
        dd_pass_threshold=1.5,
    )

    summary = result["summary"]
    segments = summary["segments"]

    assert segments == 6
    assert len(summary["net_pnl_worst_by_segment"]) == segments
    assert len(summary["pf_worst_by_segment"]) == segments
    assert len(summary["dd_worst_by_segment"]) == segments
    assert summary["pass_rate_pf"] == 0.5
    assert summary["pass_rate_dd"] == 0.5
