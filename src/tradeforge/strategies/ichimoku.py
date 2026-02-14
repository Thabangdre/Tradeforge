from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class Bar:
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class IchimokuConfig:
    bias_tf: str = "1h"
    entry_tf: str = "5m"
    tenkan_period: int = 9
    kijun_period: int = 26
    senkou_b_period: int = 52
    displacement: int = 26
    sl_buffer: float = 0.0
    tp_rr: float = 2.0
    volume: float = 1.0
    single_position: bool = True


class StrategyContext(Protocol):
    def get_series(self, timeframe: str, length: int) -> Sequence[Bar]:
        ...

    def has_open_position(self) -> bool:
        ...

    def submit_order(
        self,
        *,
        side: str,
        volume: float,
        sl: float,
        tp: float,
        meta: dict[str, Any] | None = None,
    ) -> None:
        ...


def _rolling_midpoint(bars: Sequence[Bar], period: int, idx: int) -> float | None:
    if period <= 0 or idx < period - 1:
        return None
    window = bars[idx - period + 1 : idx + 1]
    highest = max(bar.high for bar in window)
    lowest = min(bar.low for bar in window)
    return (highest + lowest) / 2.0


def tenkan_series(bars: Sequence[Bar], period: int) -> list[float | None]:
    return [_rolling_midpoint(bars, period, idx) for idx in range(len(bars))]


def kijun_series(bars: Sequence[Bar], period: int) -> list[float | None]:
    return [_rolling_midpoint(bars, period, idx) for idx in range(len(bars))]


def senkou_a_series(
    bars: Sequence[Bar], tenkan_period: int, kijun_period: int
) -> list[float | None]:
    tenkan = tenkan_series(bars, tenkan_period)
    kijun = kijun_series(bars, kijun_period)
    series: list[float | None] = []
    for t, k in zip(tenkan, kijun):
        if t is None or k is None:
            series.append(None)
        else:
            series.append((t + k) / 2.0)
    return series


def senkou_b_series(bars: Sequence[Bar], period: int) -> list[float | None]:
    return [_rolling_midpoint(bars, period, idx) for idx in range(len(bars))]


class IchimokuStrategy:
    def __init__(self, config: IchimokuConfig | None = None) -> None:
        self.config = config or IchimokuConfig()

    def _is_bullish_bias(self, bars: Sequence[Bar]) -> bool:
        if not bars:
            return False
        tenkan = tenkan_series(bars, self.config.tenkan_period)[-1]
        kijun = kijun_series(bars, self.config.kijun_period)[-1]
        cloud_a = senkou_a_series(
            bars,
            tenkan_period=self.config.tenkan_period,
            kijun_period=self.config.kijun_period,
        )[-1]
        cloud_b = senkou_b_series(bars, self.config.senkou_b_period)[-1]
        if None in (tenkan, kijun, cloud_a, cloud_b):
            return False
        return bars[-1].close > max(cloud_a, cloud_b) and tenkan > kijun

    def _is_bearish_bias(self, bars: Sequence[Bar]) -> bool:
        if not bars:
            return False
        tenkan = tenkan_series(bars, self.config.tenkan_period)[-1]
        kijun = kijun_series(bars, self.config.kijun_period)[-1]
        cloud_a = senkou_a_series(
            bars,
            tenkan_period=self.config.tenkan_period,
            kijun_period=self.config.kijun_period,
        )[-1]
        cloud_b = senkou_b_series(bars, self.config.senkou_b_period)[-1]
        if None in (tenkan, kijun, cloud_a, cloud_b):
            return False
        return bars[-1].close < min(cloud_a, cloud_b) and tenkan < kijun

    def on_bar(self, ctx: StrategyContext) -> None:
        lookback = max(
            self.config.tenkan_period,
            self.config.kijun_period,
            self.config.senkou_b_period,
        ) + 2
        entry_bars = list(ctx.get_series(self.config.entry_tf, lookback))
        bias_bars = list(ctx.get_series(self.config.bias_tf, lookback))

        if len(entry_bars) < 2 or len(bias_bars) < 1:
            return

        if self.config.single_position and ctx.has_open_position():
            return

        bullish_bias = self._is_bullish_bias(bias_bars)
        bearish_bias = self._is_bearish_bias(bias_bars)
        if not bullish_bias and not bearish_bias:
            return

        tenkan = tenkan_series(entry_bars, self.config.tenkan_period)
        kijun = kijun_series(entry_bars, self.config.kijun_period)

        prev_tenkan, curr_tenkan = tenkan[-2], tenkan[-1]
        prev_kijun, curr_kijun = kijun[-2], kijun[-1]
        if None in (prev_tenkan, curr_tenkan, prev_kijun, curr_kijun):
            return

        bullish_cross = prev_tenkan <= prev_kijun and curr_tenkan > curr_kijun
        bearish_cross = prev_tenkan >= prev_kijun and curr_tenkan < curr_kijun
        price = entry_bars[-1].close

        if bullish_bias and bullish_cross:
            sl = curr_kijun - self.config.sl_buffer
            distance = abs(price - sl)
            tp = price + (distance * self.config.tp_rr)
            ctx.submit_order(
                side="buy",
                volume=self.config.volume,
                sl=sl,
                tp=tp,
                meta={"strategy": "ichimoku", "timeframe": self.config.entry_tf},
            )
        elif bearish_bias and bearish_cross:
            sl = curr_kijun + self.config.sl_buffer
            distance = abs(price - sl)
            tp = price - (distance * self.config.tp_rr)
            ctx.submit_order(
                side="sell",
                volume=self.config.volume,
                sl=sl,
                tp=tp,
                meta={"strategy": "ichimoku", "timeframe": self.config.entry_tf},
            )
