"""Simulation clock for deterministic market replay."""

from __future__ import annotations


class SimulationClock:
    """Clock driven exclusively by replay ticks.

    The clock has no dependency on wall-clock APIs. It only advances when
    tick timestamps are applied by the replay controller.
    """

    def __init__(self) -> None:
        self._timestamp_ms: int | None = None

    @property
    def now_ms(self) -> int | None:
        """Return the current simulation timestamp in milliseconds."""
        return self._timestamp_ms

    def set_time(self, timestamp_ms: int) -> None:
        """Set simulation time to an exact tick timestamp."""
        self._timestamp_ms = int(timestamp_ms)

    def reset(self) -> None:
        """Reset the clock to the pre-replay state."""
        self._timestamp_ms = None
