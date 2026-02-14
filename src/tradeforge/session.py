from __future__ import annotations

from dataclasses import dataclass

from .context import StrategyContext
from .models import Bar


TIMEFRAME_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}


@dataclass
class BarBuilder:
    """Simple 1m bar builder.

    Input ticks are represented by minute-closed OHLC tuples for deterministic tests.
    """

    def build_1m_bar(self, timestamp: int, open_: float, high: float, low: float, close: float) -> Bar:
        return Bar(timestamp=timestamp, open=open_, high=high, low=low, close=close, timeframe="1m")


class TimeframeAggregator:
    def __init__(self, target_tf: str):
        if target_tf not in {"5m", "15m", "1h"}:
            raise ValueError(f"Unsupported aggregation tf: {target_tf}")
        self.target_tf = target_tf
        self._bucket: list[Bar] = []

    @property
    def factor(self) -> int:
        return TIMEFRAME_MINUTES[self.target_tf] // TIMEFRAME_MINUTES["1m"]

    def push(self, one_min_bar: Bar) -> Bar | None:
        if one_min_bar.timeframe != "1m":
            raise ValueError("TimeframeAggregator accepts only 1m bars")
        self._bucket.append(one_min_bar)
        if len(self._bucket) < self.factor:
            return None
        chunk = self._bucket
        self._bucket = []
        return Bar(
            timestamp=chunk[-1].timestamp,
            open=chunk[0].open,
            high=max(b.high for b in chunk),
            low=min(b.low for b in chunk),
            close=chunk[-1].close,
            timeframe=self.target_tf,
        )


class SessionRunner:
    def __init__(self) -> None:
        self.context = StrategyContext()
        self.bar_builder = BarBuilder()
        self.aggregators = {
            "5m": TimeframeAggregator("5m"),
            "15m": TimeframeAggregator("15m"),
            "1h": TimeframeAggregator("1h"),
        }

    def on_one_minute_ohlc(self, timestamp: int, open_: float, high: float, low: float, close: float) -> None:
        one_min_bar = self.bar_builder.build_1m_bar(timestamp, open_, high, low, close)
        self.context.update_bar(one_min_bar)

        for aggregator in self.aggregators.values():
            aggregated = aggregator.push(one_min_bar)
            if aggregated is not None:
                self.context.update_bar(aggregated)
