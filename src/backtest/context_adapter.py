from __future__ import annotations

from dataclasses import dataclass

from .models import Bar, PendingOrder, Position


@dataclass(slots=True)
class StrategyContext:
    bar: Bar
    history: list[Bar]
    _spread: float
    pending_orders: tuple[PendingOrder, ...]
    positions: tuple[Position, ...]

    def get_spread(self) -> float:
        return self._spread
