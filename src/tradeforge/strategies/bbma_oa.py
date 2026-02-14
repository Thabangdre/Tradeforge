from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any


@dataclass(frozen=True)
class BBMAOAConfig:
    bb_period: int = 20
    bb_dev: float = 2.0
    ma_period: int = 50
    tp_rr: float = 2.0
    volume: float = 1.0


class BBMAOAStrategy:
    """Bar-based BBMA OA strategy with explicit non-repainting state transitions."""

    def __init__(self, config: BBMAOAConfig | None = None) -> None:
        self.config = config or BBMAOAConfig()
        self._bars: list[dict[str, float]] = []

        # Persisted extreme state (required by spec).
        self.last_long_extreme_low: float | None = None
        self.last_short_extreme_high: float | None = None
        self._long_reentry_ready = False
        self._short_reentry_ready = False

    def on_bar(self, timeframe: str, bar: Any, ctx: Any) -> None:
        if timeframe != "1m":
            return

        self._bars.append(self._normalize_bar(bar))

        lookback = max(self.config.bb_period, self.config.ma_period)
        if len(self._bars) < lookback + 1:
            return

        closes = [b["close"] for b in self._bars]
        highs = [b["high"] for b in self._bars]
        lows = [b["low"] for b in self._bars]

        ema = self._ema(closes, self.config.ma_period)
        upper, lower = self._bollinger(closes, self.config.bb_period, self.config.bb_dev)

        prev_idx = len(self._bars) - 2
        curr_idx = len(self._bars) - 1
        prev_bar = self._bars[prev_idx]
        curr_bar = self._bars[curr_idx]

        # 1) Extreme detection on the previous closed bar.
        if lower[prev_idx] is not None and lows[prev_idx] <= lower[prev_idx]:
            self.last_long_extreme_low = lows[prev_idx]
            self._long_reentry_ready = False

        if upper[prev_idx] is not None and highs[prev_idx] >= upper[prev_idx]:
            self.last_short_extreme_high = highs[prev_idx]
            self._short_reentry_ready = False

        ma_now = ema[curr_idx]

        # 2) Re-entry into MA zone.
        if self.last_long_extreme_low is not None and ma_now is not None and curr_bar["close"] > ma_now:
            self._long_reentry_ready = True

        if self.last_short_extreme_high is not None and ma_now is not None and curr_bar["close"] < ma_now:
            self._short_reentry_ready = True

        if self._has_open_position(ctx):
            return

        # 3) Momentum confirmation on current bar.
        if (
            self._long_reentry_ready
            and curr_bar["close"] > curr_bar["open"]
            and curr_bar["close"] > prev_bar["high"]
            and self.last_long_extreme_low is not None
        ):
            entry = curr_bar["close"]
            sl = self.last_long_extreme_low - 1e-8
            risk = entry - sl
            if risk > 0:
                tp = entry + (risk * self.config.tp_rr)
                self._place_market(ctx, "BUY", self.config.volume, sl, tp)
                self._reset_state()
            return

        if (
            self._short_reentry_ready
            and curr_bar["close"] < curr_bar["open"]
            and curr_bar["close"] < prev_bar["low"]
            and self.last_short_extreme_high is not None
        ):
            entry = curr_bar["close"]
            sl = self.last_short_extreme_high + 1e-8
            risk = sl - entry
            if risk > 0:
                tp = entry - (risk * self.config.tp_rr)
                self._place_market(ctx, "SELL", self.config.volume, sl, tp)
                self._reset_state()

    def _reset_state(self) -> None:
        self.last_long_extreme_low = None
        self.last_short_extreme_high = None
        self._long_reentry_ready = False
        self._short_reentry_ready = False

    @staticmethod
    def _normalize_bar(bar: Any) -> dict[str, float]:
        if isinstance(bar, dict):
            return {
                "open": float(bar["open"]),
                "high": float(bar["high"]),
                "low": float(bar["low"]),
                "close": float(bar["close"]),
            }
        return {
            "open": float(getattr(bar, "open")),
            "high": float(getattr(bar, "high")),
            "low": float(getattr(bar, "low")),
            "close": float(getattr(bar, "close")),
        }

    @staticmethod
    def _ema(values: list[float], period: int) -> list[float | None]:
        out: list[float | None] = [None] * len(values)
        if len(values) < period:
            return out

        seed = sum(values[:period]) / period
        out[period - 1] = seed
        k = 2.0 / (period + 1)
        prev = seed
        for i in range(period, len(values)):
            prev = (values[i] * k) + (prev * (1 - k))
            out[i] = prev
        return out

    @staticmethod
    def _bollinger(values: list[float], period: int, dev: float) -> tuple[list[float | None], list[float | None]]:
        upper: list[float | None] = [None] * len(values)
        lower: list[float | None] = [None] * len(values)
        for i in range(period - 1, len(values)):
            window = values[i - period + 1 : i + 1]
            mean = sum(window) / period
            var = sum((x - mean) ** 2 for x in window) / period
            std = sqrt(var)
            upper[i] = mean + (dev * std)
            lower[i] = mean - (dev * std)
        return upper, lower

    @staticmethod
    def _has_open_position(ctx: Any) -> bool:
        if hasattr(ctx, "has_open_position"):
            attr = ctx.has_open_position
            return bool(attr() if callable(attr) else attr)
        if hasattr(ctx, "position"):
            return bool(ctx.position)
        if hasattr(ctx, "positions"):
            return bool(ctx.positions)
        return False

    @staticmethod
    def _place_market(ctx: Any, side: str, volume: float, sl: float, tp: float) -> None:
        ctx.place_market(side, volume, sl, tp)
