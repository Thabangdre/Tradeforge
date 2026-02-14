from tradeforge.strategies import STRATEGY_REGISTRY
from tradeforge.strategies.warisan import WarisanConfig, WarisanStrategy


def _flat_bars(count: int, low: float = 100.0, high: float = 110.0):
    return [{"open": 105.0, "high": high, "low": low, "close": 106.0} for _ in range(count)]


def test_bullish_impulse_retrace_triggers_buy():
    strategy = WarisanStrategy(WarisanConfig(swing_lookback=3))
    for bar in _flat_bars(3, low=100.0, high=110.0):
        assert strategy.on_bar(bar) is None

    assert strategy.on_bar({"open": 110.0, "high": 120.0, "low": 108.0, "close": 118.0}) is None

    signal = strategy.on_bar({"open": 106.0, "high": 112.0, "low": 105.0, "close": 111.0})
    assert signal is not None
    assert signal["side"] == "buy"


def test_bearish_impulse_retrace_triggers_sell():
    strategy = WarisanStrategy(WarisanConfig(swing_lookback=3))
    for bar in _flat_bars(3, low=100.0, high=110.0):
        assert strategy.on_bar(bar) is None

    assert strategy.on_bar({"open": 100.0, "high": 101.0, "low": 90.0, "close": 92.0}) is None

    signal = strategy.on_bar({"open": 105.0, "high": 104.0, "low": 95.0, "close": 103.0})
    assert signal is not None
    assert signal["side"] == "sell"


def test_no_entry_outside_fib_zone():
    strategy = WarisanStrategy(WarisanConfig(swing_lookback=3))
    for bar in _flat_bars(3, low=100.0, high=110.0):
        strategy.on_bar(bar)

    strategy.on_bar({"open": 110.0, "high": 120.0, "low": 108.0, "close": 118.0})

    signal = strategy.on_bar({"open": 118.0, "high": 121.0, "low": 118.0, "close": 119.0})
    assert signal is None


def test_deterministic_behavior_and_registration():
    bars = _flat_bars(3, low=100.0, high=110.0) + [
        {"open": 110.0, "high": 120.0, "low": 108.0, "close": 118.0},
        {"open": 106.0, "high": 112.0, "low": 105.0, "close": 111.0},
    ]

    strat_a = WarisanStrategy(WarisanConfig(swing_lookback=3))
    strat_b = WarisanStrategy(WarisanConfig(swing_lookback=3))

    out_a = [strat_a.on_bar(b) for b in bars]
    out_b = [strat_b.on_bar(b) for b in bars]

    assert out_a == out_b
    assert "warisan" in STRATEGY_REGISTRY
