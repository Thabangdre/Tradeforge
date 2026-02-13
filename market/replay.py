"""Deterministic replay controller for market ticks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, List, Optional, TypeVar

from .clock import SimulationClock, TickLike
from .feed import TickFeed

T = TypeVar("T", bound=TickLike)


@dataclass
class ReplayController(Generic[T]):
    """Controls deterministic replay over a tick feed."""

    feed: TickFeed[T]
    clock: SimulationClock = field(default_factory=SimulationClock)
    _playing: bool = field(default=False, init=False, repr=False)

    @property
    def is_playing(self) -> bool:
        return self._playing

    def play(self) -> List[T]:
        """Replay ticks sequentially until paused or feed is exhausted."""
        self._playing = True
        replayed: List[T] = []
        while self._playing and self.feed.has_next():
            tick = self.step_tick()
            if tick is None:
                break
            replayed.append(tick)

        if not self.feed.has_next():
            self._playing = False

        return replayed

    def pause(self) -> None:
        """Pause replay without consuming additional ticks."""
        self._playing = False

    def step_tick(self) -> Optional[T]:
        """Advance replay by exactly one tick."""
        tick = self.feed.next_tick()
        if tick is None:
            return None
        self.clock.advance_to_tick(tick)
        return tick

    def jump_to_timestamp(self, timestamp_ms: int) -> Optional[T]:
        """Seek to first tick with timestamp >= timestamp_ms."""
        self.feed.jump_to_timestamp(timestamp_ms)
        tick = self.feed.peek()
        if tick is not None:
            self.clock.advance_to_tick(tick)
        return tick
