from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bar:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
