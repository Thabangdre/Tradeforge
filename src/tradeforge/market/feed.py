"""Deterministic feed over a fixed tick sequence."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class TickFeed:
    """Index-based feed over a stable in-memory tick sequence."""

    def __init__(self, ticks: Sequence[Any]) -> None:
        self._ticks = list(ticks)

    def __len__(self) -> int:
        return len(self._ticks)

    def tick_at(self, index: int) -> Any:
        return self._ticks[index]

    def timestamp_at(self, index: int) -> int:
        return _tick_timestamp_ms(self._ticks[index])


def _tick_timestamp_ms(tick: Any) -> int:
    """Extract timestamp in milliseconds from a tick object or mapping."""
    if hasattr(tick, "timestamp_ms"):
        return int(getattr(tick, "timestamp_ms"))
    if isinstance(tick, dict) and "timestamp_ms" in tick:
        return int(tick["timestamp_ms"])
    raise TypeError("Tick must expose timestamp_ms attribute or key")
