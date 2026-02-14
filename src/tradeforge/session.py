from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SessionRunner:
    ticks: list[float]
    strategy: Any
    seed: int

    def run(self) -> list[float]:
        """Run a strategy session and return per-trade PnL values."""
        rng = random.Random(self.seed)
        if hasattr(self.strategy, "run"):
            return list(self.strategy.run(self.ticks, rng))
        raise TypeError("Strategy must implement run(ticks, rng) -> iterable[float]")
