from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpreadModel:
    default_spread: float = 0.0

    def get_spread(self, symbol: str, spreads: dict[str, float]) -> float:
        return float(spreads.get(symbol, self.default_spread))
