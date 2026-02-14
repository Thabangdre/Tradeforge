from dataclasses import dataclass, field
from math import isclose

from tradeforge.strategies.bbma_oa import BBMAOAConfig, BBMAOAStrategy


@dataclass
class MockCtx:
    orders: list[tuple[str, float, float, float]] = field(default_factory=list)

    def has_open_position(self) -> bool:
        return False

    def place_market(self, side: str, volume: float, sl: float, tp: float) -> None:
        self.orders.append((side, volume, sl, tp))


def _stable_bars(count: int, price: float = 100.0) -> list[dict[str, float]]:
    return [{"open": price, "high": price + 0.2, "low": price - 0.2, "close": price} for _ in range(count)]


def test_known_sequence_triggers_long_and_sets_sl_tp() -> None:
    strategy = BBMAOAStrategy(BBMAOAConfig(bb_period=5, ma_period=5, tp_rr=2.0, volume=1.0))
    ctx = MockCtx()

    bars = _stable_bars(8)
    bars.append({"open": 100.0, "high": 100.1, "low": 95.0, "close": 100.0})  # extreme setup
    bars.append({"open": 100.0, "high": 100.05, "low": 99.8, "close": 100.02})  # re-entry without momentum
    bars.append({"open": 100.0, "high": 102.5, "low": 99.9, "close": 102.2})  # momentum breakout

    for bar in bars:
        strategy.on_bar("1m", bar, ctx)

    assert len(ctx.orders) == 1
    side, volume, sl, tp = ctx.orders[0]
    assert side == "BUY"
    assert volume == 1.0
    assert sl < 100.0
    expected_tp = 102.2 + ((102.2 - sl) * 2.0)
    assert isclose(tp, expected_tp, rel_tol=0, abs_tol=1e-9)


def test_known_sequence_triggers_short() -> None:
    strategy = BBMAOAStrategy(BBMAOAConfig(bb_period=5, ma_period=5, tp_rr=2.0, volume=1.0))
    ctx = MockCtx()

    bars = _stable_bars(8)
    bars.append({"open": 100.0, "high": 105.0, "low": 99.9, "close": 100.0})  # extreme setup
    bars.append({"open": 100.0, "high": 100.2, "low": 99.95, "close": 99.98})  # re-entry without momentum
    bars.append({"open": 100.0, "high": 99.9, "low": 97.0, "close": 97.5})  # momentum breakdown

    for bar in bars:
        strategy.on_bar("1m", bar, ctx)

    assert len(ctx.orders) == 1
    side, _, sl, tp = ctx.orders[0]
    assert side == "SELL"
    assert sl > 100.0
    expected_tp = 97.5 - ((sl - 97.5) * 2.0)
    assert isclose(tp, expected_tp, rel_tol=0, abs_tol=1e-9)


def test_deterministic_repeatability() -> None:
    bars = _stable_bars(8)
    bars.extend(
        [
            {"open": 100.0, "high": 100.1, "low": 95.0, "close": 100.0},
            {"open": 100.0, "high": 100.05, "low": 99.8, "close": 100.02},
            {"open": 100.0, "high": 102.5, "low": 99.9, "close": 102.2},
        ]
    )

    config = BBMAOAConfig(bb_period=5, ma_period=5)

    strategy_a = BBMAOAStrategy(config)
    ctx_a = MockCtx()
    for bar in bars:
        strategy_a.on_bar("1m", bar, ctx_a)

    strategy_b = BBMAOAStrategy(config)
    ctx_b = MockCtx()
    for bar in bars:
        strategy_b.on_bar("1m", bar, ctx_b)

    assert ctx_a.orders == ctx_b.orders
