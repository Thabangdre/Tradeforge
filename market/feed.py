"""Deterministic feed iteration over an in-memory tick sequence."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from typing import Generic, Iterable, Iterator, Optional, Sequence, TypeVar

from .clock import TickLike

T = TypeVar("T", bound=TickLike)


@dataclass
class TickFeed(Generic[T]):
    """Iterator-like deterministic feed over ordered tick data."""

    ticks: Sequence[T]
    _index: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._timestamps = [int(t.timestamp_ms) for t in self.ticks]

    def __iter__(self) -> Iterator[T]:
        while True:
            tick = self.next_tick()
            if tick is None:
                break
            yield tick

    @property
    def index(self) -> int:
        return self._index

    def has_next(self) -> bool:
        return self._index < len(self.ticks)

    def peek(self) -> Optional[T]:
        if not self.has_next():
            return None
        return self.ticks[self._index]

    def next_tick(self) -> Optional[T]:
        if not self.has_next():
            return None
        tick = self.ticks[self._index]
        self._index += 1
        return tick

    def reset(self) -> None:
        self._index = 0

    def jump_to_timestamp(self, timestamp_ms: int) -> int:
        """Jump to first tick with timestamp >= timestamp_ms."""
        self._index = bisect_left(self._timestamps, int(timestamp_ms))
        return self._index
