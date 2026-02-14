from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict


@dataclass(frozen=True)
class Strategy:
    name: str
    signal_fn: Callable[[float, dict, int], float]

    def signal(self, tick: float, config: dict, step: int) -> float:
        return self.signal_fn(tick, config, step)


class StrategyRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Callable[[], Strategy]] = {
            "bbma": self._build_bbma,
            "fibo": self._build_fibo,
        }

    def create(self, strategy_name: str) -> Strategy:
        if strategy_name not in self._registry:
            available = ", ".join(sorted(self._registry))
            raise ValueError(f"Unknown strategy '{strategy_name}'. Available: {available}")
        return self._registry[strategy_name]()

    @staticmethod
    def _build_bbma() -> Strategy:
        def signal(tick: float, config: dict, step: int) -> float:
            window = float(config.get("window", 10))
            alpha = float(config.get("alpha", 0.2))
            momentum = (tick - window) / max(window, 1.0)
            return alpha * momentum + (step % 3 - 1) * 0.01

        return Strategy(name="bbma", signal_fn=signal)

    @staticmethod
    def _build_fibo() -> Strategy:
        def signal(tick: float, config: dict, step: int) -> float:
            ratio = float(config.get("ratio", 1.618))
            sensitivity = float(config.get("sensitivity", 0.3))
            oscillation = ((step % 5) - 2) / 10
            return sensitivity * ((tick / max(ratio, 0.1)) - 1) + oscillation

        return Strategy(name="fibo", signal_fn=signal)


registry = StrategyRegistry()
