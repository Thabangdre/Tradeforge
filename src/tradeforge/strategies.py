"""Reference strategy implementations used in tests and examples."""

from __future__ import annotations

from dataclasses import dataclass

from .registry import register_strategy


@dataclass
class BBMAStrategy:
    config: dict
    seed: int

    def signal(self, index: int, tick: dict) -> int:
        threshold = float(self.config.get("threshold", 0.2))
        sensitivity = float(self.config.get("sensitivity", 1.0))
        momentum = float(tick.get("momentum", 0.0)) * sensitivity
        if momentum > threshold:
            return 1
        if momentum < -threshold:
            return -1
        return 0


@dataclass
class FiboStrategy:
    config: dict
    seed: int

    def signal(self, index: int, tick: dict) -> int:
        retrace = float(self.config.get("retrace", 0.5))
        price = float(tick.get("price", 0.0))
        baseline = float(tick.get("baseline", price))
        delta = price - baseline
        trigger = retrace * 0.1
        if delta > trigger:
            return 1
        if delta < -trigger:
            return -1
        return 0


register_strategy("bbma", lambda config, seed: BBMAStrategy(config=config, seed=seed))
register_strategy("fibo", lambda config, seed: FiboStrategy(config=config, seed=seed))
