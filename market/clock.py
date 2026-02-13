"""Simulation clock driven strictly by tick timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class TickLike(Protocol):
    """Protocol for ticks used by the replay engine."""

    timestamp_ms: int


@dataclass
class SimulationClock:
    """Clock whose time is always sourced from replayed ticks."""

    current_timestamp_ms: Optional[int] = None

    def advance_to_tick(self, tick: TickLike) -> int:
        """Advance simulation time to the given tick timestamp."""
        self.current_timestamp_ms = int(tick.timestamp_ms)
        return self.current_timestamp_ms
