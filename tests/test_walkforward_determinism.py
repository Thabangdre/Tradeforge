from backtest.execution import ExecutionConfig
from backtest.models import Bar
from backtest.spread import SpreadModel
from backtest.walkforward import WalkForwardSpec, walk_forward


class DeterministicStrategy:
    def __init__(self, seg_id: int, mode: str) -> None:
        self.seg_id = seg_id
        self.mode = mode

    def generate_trade_pnls(self, bars: list[Bar]) -> list[float]:
        if len(bars) < 2:
            return []
        base = 0.2 if self.mode == "test" else 0.1
        pnls: list[float] = []
        for idx in range(1, len(bars), 2):
            diff = bars[idx].close - bars[idx - 1].close
            pnls.append(round(diff + base + self.seg_id * 0.01, 6))
        return pnls


def _bars(n: int) -> list[Bar]:
    return [
        Bar(timestamp=i, open=100 + i, high=101 + i, low=99 + i, close=100 + i + (i % 3) * 0.1, volume=1_000)
        for i in range(n)
    ]


def test_walk_forward_is_deterministic() -> None:
    bars = _bars(90)
    spec = WalkForwardSpec(train_bars=20, test_bars=10, step_bars=10)

    def strategy_factory(ctx: dict[str, object]) -> DeterministicStrategy:
        return DeterministicStrategy(seg_id=int(ctx["seg_id"]), mode=str(ctx["mode"]))

    kwargs = {
        "bars": bars,
        "strategy_factory": strategy_factory,
        "symbol": "BTCUSD",
        "spread_model": SpreadModel(default_spread=0.0),
        "exec_config": ExecutionConfig(),
        "spreads": {"BTCUSD": 0.5},
        "spec": spec,
        "run_train": True,
        "initial_cash": 1000.0,
    }

    run_1 = walk_forward(**kwargs)
    run_2 = walk_forward(**kwargs)

    assert run_1 == run_2
