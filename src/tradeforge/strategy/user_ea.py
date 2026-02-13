"""Custom user EA logic integration.

This module provides a deterministic EA implementation that can carry indicator
state and generate executable trades from incoming tick data.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class Tick:
    """Single market tick/candle point used by the EA."""

    time: str
    bid: float
    ask: float
    high: float
    low: float


@dataclass(frozen=True)
class Position:
    """Represents an active market position."""

    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    opened_at: str


@dataclass(frozen=True)
class TradeEvent:
    """Event emitted by the EA simulation loop."""

    type: str
    time: str
    direction: Optional[str] = None
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    reason: Optional[str] = None
    lot: Optional[float] = None


class EAAdapter:
    """Small adapter contract for deterministic EA implementations."""

    def on_tick(self, tick: Tick) -> List[TradeEvent]:
        """Process a tick and return zero or more trade events."""
        raise NotImplementedError


class UserEA(EAAdapter):
    """Example breakout EA with persistent indicator/state handling.

    Strategy summary:
    - Maintains rolling high/low levels for breakout detection.
    - Computes simple Fibonacci retracement levels from recent range.
    - Opens one position at a time when price breaks above/below recent range.
    - Uses configurable stop-loss / take-profit distances.
    - Emits deterministic events for testability.
    """

    def __init__(
        self,
        *,
        lot: float = 0.1,
        sl_pips: float = 20.0,
        tp_pips: float = 40.0,
        breakout_window: int = 3,
        use_mid_price_filter: bool = False,
        pip_size: float = 0.0001,
    ) -> None:
        if breakout_window < 2:
            raise ValueError("breakout_window must be at least 2")
        self.lot = lot
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.breakout_window = breakout_window
        self.use_mid_price_filter = use_mid_price_filter
        self.pip_size = pip_size

        self._highs: Deque[float] = deque(maxlen=breakout_window)
        self._lows: Deque[float] = deque(maxlen=breakout_window)
        self.position: Optional[Position] = None
        self.fib_levels: Dict[str, float] = {}

    @staticmethod
    def _mid_price(tick: Tick) -> float:
        return (tick.bid + tick.ask) / 2.0

    def _update_indicators(self, tick: Tick) -> None:
        self._highs.append(tick.high)
        self._lows.append(tick.low)
        if len(self._highs) < self.breakout_window:
            return

        recent_high = max(self._highs)
        recent_low = min(self._lows)
        span = recent_high - recent_low

        self.fib_levels = {
            "0.0": recent_high,
            "0.236": recent_high - 0.236 * span,
            "0.382": recent_high - 0.382 * span,
            "0.5": recent_high - 0.5 * span,
            "0.618": recent_high - 0.618 * span,
            "1.0": recent_low,
        }

    def _close_for_risk(self, tick: Tick) -> Optional[TradeEvent]:
        if self.position is None:
            return None

        pos = self.position
        if pos.direction == "BUY":
            if tick.low <= pos.stop_loss:
                self.position = None
                return TradeEvent(
                    type="EXIT",
                    time=tick.time,
                    direction=pos.direction,
                    exit_price=pos.stop_loss,
                    reason="SL",
                )
            if tick.high >= pos.take_profit:
                self.position = None
                return TradeEvent(
                    type="EXIT",
                    time=tick.time,
                    direction=pos.direction,
                    exit_price=pos.take_profit,
                    reason="TP",
                )
        else:
            if tick.high >= pos.stop_loss:
                self.position = None
                return TradeEvent(
                    type="EXIT",
                    time=tick.time,
                    direction=pos.direction,
                    exit_price=pos.stop_loss,
                    reason="SL",
                )
            if tick.low <= pos.take_profit:
                self.position = None
                return TradeEvent(
                    type="EXIT",
                    time=tick.time,
                    direction=pos.direction,
                    exit_price=pos.take_profit,
                    reason="TP",
                )

        return None

    def _open_if_breakout(self, tick: Tick) -> Optional[TradeEvent]:
        if self.position is not None or len(self._highs) < self.breakout_window:
            return None

        # Use history before current candle to avoid look-ahead.
        highs = list(self._highs)[:-1]
        lows = list(self._lows)[:-1]
        if not highs or not lows:
            return None

        recent_high = max(highs)
        recent_low = min(lows)
        mid = self._mid_price(tick)

        if tick.ask > recent_high and (
            not self.use_mid_price_filter or mid > self.fib_levels.get("0.5", mid)
        ):
            entry = tick.ask
            stop_loss = entry - self.sl_pips * self.pip_size
            take_profit = entry + self.tp_pips * self.pip_size
            self.position = Position("BUY", entry, stop_loss, take_profit, tick.time)
            return TradeEvent(
                type="ENTRY",
                time=tick.time,
                direction="BUY",
                entry=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                lot=self.lot,
            )

        if tick.bid < recent_low and (
            not self.use_mid_price_filter or mid < self.fib_levels.get("0.5", mid)
        ):
            entry = tick.bid
            stop_loss = entry + self.sl_pips * self.pip_size
            take_profit = entry - self.tp_pips * self.pip_size
            self.position = Position("SELL", entry, stop_loss, take_profit, tick.time)
            return TradeEvent(
                type="ENTRY",
                time=tick.time,
                direction="SELL",
                entry=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                lot=self.lot,
            )

        return None

    def on_tick(self, tick: Tick) -> List[TradeEvent]:
        events: List[TradeEvent] = []

        risk_event = self._close_for_risk(tick)
        if risk_event is not None:
            events.append(risk_event)

        self._update_indicators(tick)

        # Avoid exiting and immediately re-entering on the same tick.
        if risk_event is not None:
            return events

        entry_event = self._open_if_breakout(tick)
        if entry_event is not None:
            events.append(entry_event)

        return events


def _normalize_ticks(tick_data: Iterable[dict | Tick]) -> List[Tick]:
    normalized: List[Tick] = []
    for tick in tick_data:
        if isinstance(tick, Tick):
            normalized.append(tick)
            continue
        normalized.append(
            Tick(
                time=str(tick["time"]),
                bid=float(tick["bid"]),
                ask=float(tick["ask"]),
                high=float(tick["high"]),
                low=float(tick["low"]),
            )
        )
    return normalized


def run_user_ea(config: dict, tick_data: Iterable[dict | Tick]) -> List[TradeEvent]:
    """Execute `UserEA` against tick data and return deterministic event stream."""

    ea = UserEA(**config)
    events: List[TradeEvent] = []
    for tick in _normalize_ticks(tick_data):
        events.extend(ea.on_tick(tick))
    return events
