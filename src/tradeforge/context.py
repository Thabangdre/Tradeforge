from __future__ import annotations

from dataclasses import dataclass, field

from .models import Bar, SUPPORTED_TIMEFRAMES


@dataclass
class StrategyContext:
    bars_by_tf: dict[str, list[Bar]] = field(default_factory=lambda: {tf: [] for tf in SUPPORTED_TIMEFRAMES})

    def update_bar(self, bar: Bar) -> None:
        if bar.timeframe not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {bar.timeframe}")
        self.bars_by_tf[bar.timeframe].append(bar)

    def get_bar(self, tf: str, index: int = 0) -> Bar:
        self._validate_tf(tf)
        bars = self.bars_by_tf[tf]
        if not bars:
            raise IndexError(f"No bars for timeframe {tf}")
        if index < 0:
            raise IndexError("index must be >= 0")
        if index >= len(bars):
            raise IndexError(f"Requested index {index} but only {len(bars)} bars in {tf}")
        return bars[-1 - index]

    def get_series(self, tf: str, n: int) -> list[Bar]:
        self._validate_tf(tf)
        if n <= 0:
            raise ValueError("n must be > 0")
        bars = self.bars_by_tf[tf]
        if len(bars) < n:
            raise IndexError(f"Requested {n} bars but only {len(bars)} in {tf}")
        return bars[-n:]

    @staticmethod
    def _validate_tf(tf: str) -> None:
        if tf not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {tf}")
