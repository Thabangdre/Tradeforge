"""Deterministic replay controller."""

from __future__ import annotations

from bisect import bisect_left
from typing import Any

from .clock import SimulationClock
from .feed import TickFeed


class ReplayController:
    """Controls deterministic replay over a tick feed.

    Behavior is fully driven by input tick data. No wall-clock time is used.
    """

    def __init__(self, feed: TickFeed, clock: SimulationClock | None = None) -> None:
        self.feed = feed
        self.clock = clock or SimulationClock()
        self._next_index = 0
        self._is_playing = False
        self._timestamps = [self.feed.timestamp_at(i) for i in range(len(self.feed))]

    @property
    def next_index(self) -> int:
        return self._next_index

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def play(self) -> None:
        self._is_playing = True

    def pause(self) -> None:
        self._is_playing = False

    def step_tick(self) -> Any | None:
        if self._next_index >= len(self.feed):
            return None

        tick = self.feed.tick_at(self._next_index)
        self.clock.set_time(self._timestamps[self._next_index])
        self._next_index += 1
        return tick

    def jump_to_timestamp(self, ts_ms: int) -> Any | None:
        """Move replay pointer to first tick whose timestamp is >= ts_ms.

        Returns that tick (and advances simulation clock to it) when found,
        otherwise returns ``None`` and sets pointer to end of feed.
        """
        self._next_index = bisect_left(self._timestamps, int(ts_ms))
        if self._next_index >= len(self.feed):
            return None

        tick = self.feed.tick_at(self._next_index)
        self.clock.set_time(self._timestamps[self._next_index])
        return tick
