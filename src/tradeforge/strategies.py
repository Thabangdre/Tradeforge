from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .registry import register_strategy


@dataclass(slots=True)
class BBMAStrategy:
    config: dict

    def run(self, ticks: list[float], rng: Random):
        window = max(2, int(self.config.get("window", 5)))
        threshold = float(self.config.get("threshold", 0.8))
        risk = float(self.config.get("risk", 1.0))

        for idx in range(window, len(ticks)):
            segment = ticks[idx - window : idx]
            mean = sum(segment) / window
            diff = ticks[idx] - mean
            if abs(diff) >= threshold:
                drift = 1 if diff > 0 else -1
                noise = (rng.random() - 0.5) * 0.05
                yield (diff * drift - threshold * 0.25 + noise) * risk


@dataclass(slots=True)
class FiboStrategy:
    config: dict

    def run(self, ticks: list[float], rng: Random):
        step = max(2, int(self.config.get("step", 3)))
        retrace = float(self.config.get("retrace", 0.618))
        leverage = float(self.config.get("leverage", 1.0))

        for idx in range(step, len(ticks), step):
            move = ticks[idx] - ticks[idx - step]
            if abs(move) >= retrace:
                noise = (rng.random() - 0.5) * 0.03
                yield (move * retrace + noise) * leverage


def register_builtin_strategies() -> None:
    register_strategy("bbma", BBMAStrategy)
    register_strategy("fibo", FiboStrategy)


register_builtin_strategies()
