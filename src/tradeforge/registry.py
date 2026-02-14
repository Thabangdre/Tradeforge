from __future__ import annotations

from collections.abc import Callable
from typing import Any


StrategyFactory = Callable[[dict[str, Any]], Any]
_REGISTRY: dict[str, StrategyFactory] = {}


def register_strategy(name: str, factory: StrategyFactory) -> None:
    _REGISTRY[name.lower()] = factory


def create_strategy(name: str, config: dict[str, Any]) -> Any:
    try:
        factory = _REGISTRY[name.lower()]
    except KeyError as exc:
        available = ", ".join(sorted(_REGISTRY)) or "<empty>"
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}") from exc
    return factory(config)
