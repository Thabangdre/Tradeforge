from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .base import StrategyContext

Direction = Literal["bullish", "bearish"]


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


@dataclass
class FibsDontLieConfig:
    entry_tf: str = "5m"
    fib_low: float = 0.62
    fib_high: float = 0.79
    allow_deep_retrace: bool = True
    deep_retrace_extra: float = 0.05
    sl_buffer: float = 0.0
    tp_rr: float = 2.0
    volume: float = 1.0
    single_position: bool = True
    partial_tp_rr: float = 1.0
    partial_close_fraction: float = 0.5
    breakeven_after_rr: float = 1.0
    breakeven_offset: float = 0.0
    spread_limit: Optional[float] = None


@dataclass
class Setup:
    direction: Direction
    impulse_high: float
    impulse_low: float
    fib_zone_low: float
    fib_zone_high: float


@dataclass
class Position:
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    initial_volume: float
    remaining_volume: float
    realized_pnl: float = 0.0
    partial_taken: bool = False
    breakeven_moved: bool = False


class FibsDontLie:
    def __init__(self, config: Optional[FibsDontLieConfig] = None, swing_lookback: int = 3):
        self.config = config or FibsDontLieConfig()
        self.swing_lookback = swing_lookback
        self.candles: list[Candle] = []
        self.active_setup: Optional[Setup] = None
        self.position: Optional[Position] = None

    def on_candle(self, candle: Candle, ctx: Optional[StrategyContext] = None) -> None:
        ctx = ctx or StrategyContext()

        if self.position:
            self._manage_trade(candle)

        setup = self._detect_structure(candle)
        if setup:
            if self.position is None:
                if self.active_setup is None or self.active_setup.direction != setup.direction:
                    self.active_setup = setup
                else:
                    self.active_setup = setup

        if self.position is None and self.active_setup:
            self._maybe_enter(candle, ctx)

        self.candles.append(candle)

    def _detect_structure(self, candle: Candle) -> Optional[Setup]:
        if len(self.candles) < self.swing_lookback:
            return None
        window = self.candles[-self.swing_lookback :]
        swing_high = max(c.high for c in window)
        swing_low = min(c.low for c in window)

        if candle.close > swing_high:
            return self._build_setup("bullish", impulse_high=candle.high, impulse_low=swing_low)
        if candle.close < swing_low:
            return self._build_setup("bearish", impulse_high=swing_high, impulse_low=candle.low)
        return None

    def _build_setup(self, direction: Direction, impulse_high: float, impulse_low: float) -> Setup:
        impulse_range = max(impulse_high - impulse_low, 1e-9)
        if direction == "bullish":
            fib_zone_low = impulse_high - impulse_range * self.config.fib_high
            fib_zone_high = impulse_high - impulse_range * self.config.fib_low
            if self.config.allow_deep_retrace:
                fib_zone_low -= impulse_range * self.config.deep_retrace_extra
        else:
            fib_zone_low = impulse_low + impulse_range * self.config.fib_low
            fib_zone_high = impulse_low + impulse_range * self.config.fib_high
            if self.config.allow_deep_retrace:
                fib_zone_high += impulse_range * self.config.deep_retrace_extra
        return Setup(
            direction=direction,
            impulse_high=impulse_high,
            impulse_low=impulse_low,
            fib_zone_low=min(fib_zone_low, fib_zone_high),
            fib_zone_high=max(fib_zone_low, fib_zone_high),
        )

    def _maybe_enter(self, candle: Candle, ctx: StrategyContext) -> None:
        if self.config.single_position and self.position is not None:
            return
        spread = ctx.get_spread()
        if self.config.spread_limit is not None and spread is not None and spread > self.config.spread_limit:
            return

        setup = self.active_setup
        assert setup is not None
        touched_zone = candle.low <= setup.fib_zone_high and candle.high >= setup.fib_zone_low

        if setup.direction == "bullish" and touched_zone and candle.close > candle.open:
            entry = candle.close
            sl = setup.impulse_low - self.config.sl_buffer
            risk = max(entry - sl, 1e-9)
            tp = entry + risk * self.config.tp_rr
            self.position = Position("bullish", entry, sl, tp, self.config.volume, self.config.volume)
            self.active_setup = None
        elif setup.direction == "bearish" and touched_zone and candle.close < candle.open:
            entry = candle.close
            sl = setup.impulse_high + self.config.sl_buffer
            risk = max(sl - entry, 1e-9)
            tp = entry - risk * self.config.tp_rr
            self.position = Position("bearish", entry, sl, tp, self.config.volume, self.config.volume)
            self.active_setup = None

    def _manage_trade(self, candle: Candle) -> None:
        pos = self.position
        assert pos is not None

        risk = max(
            pos.entry_price - pos.stop_loss if pos.direction == "bullish" else pos.stop_loss - pos.entry_price,
            1e-9,
        )
        rr_max = (
            (candle.high - pos.entry_price) / risk
            if pos.direction == "bullish"
            else (pos.entry_price - candle.low) / risk
        )

        if not pos.partial_taken and rr_max >= self.config.partial_tp_rr:
            close_vol = min(pos.remaining_volume, pos.initial_volume * self.config.partial_close_fraction)
            partial_exit_price = (
                pos.entry_price + self.config.partial_tp_rr * risk
                if pos.direction == "bullish"
                else pos.entry_price - self.config.partial_tp_rr * risk
            )
            pnl_per_unit = (
                partial_exit_price - pos.entry_price
                if pos.direction == "bullish"
                else pos.entry_price - partial_exit_price
            )
            pos.realized_pnl += pnl_per_unit * close_vol
            pos.remaining_volume -= close_vol
            pos.partial_taken = True

        if not pos.breakeven_moved and rr_max >= self.config.breakeven_after_rr:
            pos.stop_loss = (
                pos.entry_price + self.config.breakeven_offset
                if pos.direction == "bullish"
                else pos.entry_price - self.config.breakeven_offset
            )
            pos.breakeven_moved = True

        if pos.direction == "bullish":
            if candle.low <= pos.stop_loss:
                self._close_remaining(pos.stop_loss)
            elif candle.high >= pos.take_profit:
                self._close_remaining(pos.take_profit)
        else:
            if candle.high >= pos.stop_loss:
                self._close_remaining(pos.stop_loss)
            elif candle.low <= pos.take_profit:
                self._close_remaining(pos.take_profit)

    def _close_remaining(self, exit_price: float) -> None:
        pos = self.position
        assert pos is not None
        if pos.remaining_volume > 0:
            pnl_per_unit = (
                exit_price - pos.entry_price
                if pos.direction == "bullish"
                else pos.entry_price - exit_price
            )
            pos.realized_pnl += pnl_per_unit * pos.remaining_volume
            pos.remaining_volume = 0.0
        self.position = None
