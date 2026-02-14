from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionConfig:
    allow_short: bool = True
    commission_per_trade: float = 0.0
