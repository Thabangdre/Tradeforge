"""Warisan fib retracement strategy plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, TypedDict

from . import register_strategy

Direction = Literal["bullish", "bearish"]


class Signal(TypedDict):
    side: Literal["buy", "sell"]
    entry: float
    stop_loss: float
    take_profit: float


@dataclass(frozen=True)
class WarisanConfig:
    entry_tf: str = "5m"
    fib_low: float = 0.62
    fib_high: float = 0.79
    swing_lookback: int = 20
    sl_buffer: float = 0.0
    tp_rr: float = 2.0
    volume: float = 1.0
    single_position: bool = True


@dataclass
class ImpulseState:
    impulse_high: float
    impulse_low: float
    direction: Direction


class WarisanStrategy:
    """Detect impulses and trade fib-zone retracements."""

    def __init__(self, config: Optional[WarisanConfig] = None) -> None:
        self.config = config or WarisanConfig()
        self._bars: List[Dict[str, float]] = []
        self.last_impulse: Optional[ImpulseState] = None
        self.in_position = False

    def on_bar(self, bar: Dict[str, float], timeframe: Optional[str] = None) -> Optional[Signal]:
        """Process a new bar and return an entry signal when conditions are met."""
        tf = timeframe or self.config.entry_tf
        if tf != self.config.entry_tf:
            return None

        self._detect_impulse(bar)
        signal = self._entry_signal(bar)
        self._bars.append(bar)
        return signal

    def _detect_impulse(self, bar: Dict[str, float]) -> None:
        if len(self._bars) < self.config.swing_lookback:
            return

        window = self._bars[-self.config.swing_lookback :]
        swing_high = max(b["high"] for b in window)
        swing_low = min(b["low"] for b in window)

        if bar["high"] > swing_high:
            self.last_impulse = ImpulseState(
                impulse_high=bar["high"],
                impulse_low=swing_low,
                direction="bullish",
            )
        elif bar["low"] < swing_low:
            self.last_impulse = ImpulseState(
                impulse_high=swing_high,
                impulse_low=bar["low"],
                direction="bearish",
            )

    def _entry_signal(self, bar: Dict[str, float]) -> Optional[Signal]:
        if self.last_impulse is None:
            return None
        if self.config.single_position and self.in_position:
            return None

        impulse = self.last_impulse
        range_size = impulse.impulse_high - impulse.impulse_low
        if range_size <= 0:
            return None

        if impulse.direction == "bullish":
            zone_low = impulse.impulse_high - (self.config.fib_high * range_size)
            zone_high = impulse.impulse_high - (self.config.fib_low * range_size)
            touched = zone_low <= bar["low"] <= zone_high
            bullish_close = bar["close"] > bar["open"]
            if touched and bullish_close:
                entry = bar["close"]
                stop_loss = impulse.impulse_low - self.config.sl_buffer
                take_profit = entry + ((entry - stop_loss) * self.config.tp_rr)
                self.in_position = True
                return {
                    "side": "buy",
                    "entry": entry,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                }
            return None

        zone_low = impulse.impulse_low + (self.config.fib_low * range_size)
        zone_high = impulse.impulse_low + (self.config.fib_high * range_size)
        touched = zone_low <= bar["high"] <= zone_high
        bearish_close = bar["close"] < bar["open"]
        if touched and bearish_close:
            entry = bar["close"]
            stop_loss = impulse.impulse_high + self.config.sl_buffer
            take_profit = entry - ((stop_loss - entry) * self.config.tp_rr)
            self.in_position = True
            return {
                "side": "sell",
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            }
        return None


def register() -> None:
    """Register the strategy plugin."""
    register_strategy("warisan", WarisanStrategy)


register()
