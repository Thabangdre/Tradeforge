from __future__ import annotations

from typing import Protocol

from .models import Bar


class SpreadModel(Protocol):
    def get_spread(self, bar: Bar, symbol: str) -> float:
        ...


class FixedSpreadModel:
    def __init__(self, spread_points: float) -> None:
        self.spread_points = spread_points

    def get_spread(self, bar: Bar, symbol: str) -> float:
        return self.spread_points
