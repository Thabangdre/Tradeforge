from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_TIMEFRAMES = {"1m", "5m", "15m", "1h"}


@dataclass(frozen=True)
class Bar:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    timeframe: str = "1m"


@dataclass(frozen=True)
class Signal:
    side: str
    entry: float
    stop_loss: float
    take_profit: float
    reason: str
