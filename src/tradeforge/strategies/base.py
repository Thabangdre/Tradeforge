from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class StrategyContext:
    """Runtime context shared with strategies."""

    spread: Optional[float] = None

    def get_spread(self) -> Optional[float]:
        return self.spread
