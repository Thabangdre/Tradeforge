from __future__ import annotations

from dataclasses import dataclass, field

from tradeforge.strategies.ichimoku import Bar, IchimokuConfig, IchimokuStrategy


@dataclass
class FakeContext:
    series: dict[str, list[Bar]]
    open_position: bool = False
    orders: list[dict] = field(default_factory=list)

    def get_series(self, timeframe: str, length: int):
        return self.series[timeframe][-length:]

    def has_open_position(self) -> bool:
        return self.open_position

    def submit_order(self, **kwargs):
        self.orders.append(kwargs)


def mkbar(price: float, spread: float = 0.6) -> Bar:
    return Bar(open=price, high=price + spread, low=price - spread, close=price)


def mkbar_hlc(low: float, high: float, close: float) -> Bar:
    return Bar(open=close, high=high, low=low, close=close)


def test_bullish_bias_with_cross_triggers_buy():
    cfg = IchimokuConfig(tenkan_period=3, kijun_period=5, senkou_b_period=7, tp_rr=2.0)
    strategy = IchimokuStrategy(cfg)

    bias = [mkbar(p) for p in [90, 91, 92, 94, 96, 99, 103, 107, 110]]
    entry = [
        mkbar_hlc(105.33, 113.03, 108.57),
        mkbar_hlc(87.77, 93.12, 89.94),
        mkbar_hlc(103.51, 106.9, 105.13),
        mkbar_hlc(97.5, 106.63, 102.11),
        mkbar_hlc(88.46, 96.14, 93.2),
        mkbar_hlc(87.52, 96.66, 96.5),
        mkbar_hlc(104.31, 113.38, 107.12),
        mkbar_hlc(101.89, 110.93, 108.08),
        mkbar_hlc(94.16, 95.62, 94.8),
    ]
    ctx = FakeContext(series={"1h": bias, "5m": entry})

    strategy.on_bar(ctx)

    assert len(ctx.orders) == 1
    order = ctx.orders[0]
    assert order["side"] == "buy"
    assert order["tp"] > order["sl"]


def test_bearish_bias_with_cross_triggers_sell():
    cfg = IchimokuConfig(tenkan_period=3, kijun_period=5, senkou_b_period=7, tp_rr=2.0)
    strategy = IchimokuStrategy(cfg)

    bias = [mkbar(p) for p in [110, 109, 108, 106, 104, 101, 97, 94, 90]]
    entry = [
        mkbar_hlc(96.54, 97.71, 96.62),
        mkbar_hlc(99.06, 102.32, 101.65),
        mkbar_hlc(94.8, 103.49, 96.14),
        mkbar_hlc(95.04, 103.1, 95.66),
        mkbar_hlc(108.48, 110.62, 110.14),
        mkbar_hlc(109.55, 117.85, 112.2),
        mkbar_hlc(83.21, 88.59, 88.16),
        mkbar_hlc(88.8, 97.8, 90.08),
        mkbar_hlc(107.31, 108.12, 107.57),
    ]
    ctx = FakeContext(series={"1h": bias, "5m": entry})

    strategy.on_bar(ctx)

    assert len(ctx.orders) == 1
    order = ctx.orders[0]
    assert order["side"] == "sell"
    assert order["tp"] < order["sl"]


def test_bias_filter_blocks_trades_inside_cloud():
    cfg = IchimokuConfig(tenkan_period=3, kijun_period=5, senkou_b_period=7)
    strategy = IchimokuStrategy(cfg)

    bias = [mkbar(p) for p in [100, 102, 101, 99, 100, 102, 101, 100, 101]]
    entry = [mkbar(p) for p in [99, 98, 97, 96, 95, 95, 94, 106, 108]]
    ctx = FakeContext(series={"1h": bias, "5m": entry})

    strategy.on_bar(ctx)

    assert ctx.orders == []


def test_deterministic_repeatability():
    cfg = IchimokuConfig(tenkan_period=3, kijun_period=5, senkou_b_period=7, tp_rr=1.5)
    strategy = IchimokuStrategy(cfg)

    bias = [mkbar(p) for p in [90, 91, 92, 94, 96, 99, 103, 107, 110]]
    entry = [
        mkbar_hlc(105.33, 113.03, 108.57),
        mkbar_hlc(87.77, 93.12, 89.94),
        mkbar_hlc(103.51, 106.9, 105.13),
        mkbar_hlc(97.5, 106.63, 102.11),
        mkbar_hlc(88.46, 96.14, 93.2),
        mkbar_hlc(87.52, 96.66, 96.5),
        mkbar_hlc(104.31, 113.38, 107.12),
        mkbar_hlc(101.89, 110.93, 108.08),
        mkbar_hlc(94.16, 95.62, 94.8),
    ]

    ctx_a = FakeContext(series={"1h": bias, "5m": entry})
    ctx_b = FakeContext(series={"1h": bias, "5m": entry})

    strategy.on_bar(ctx_a)
    strategy.on_bar(ctx_b)

    assert ctx_a.orders == ctx_b.orders
