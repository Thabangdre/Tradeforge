"""Strategy registry for instantiating strategies by name."""

from __future__ import annotations

from typing import Callable


StrategyFactory = Callable[[dict, int], object]
_REGISTRY: dict[str, StrategyFactory] = {}


def register_strategy(name: str, factory: StrategyFactory) -> None:
    """Register a strategy factory under a normalized name."""
    _REGISTRY[name.lower()] = factory


def create_strategy(name: str, config: dict, seed: int) -> object:
    """Create a strategy instance using a registered factory."""
    key = name.lower()
    if key not in _REGISTRY:
        raise ValueError(f"Unknown strategy: {name}")
    return _REGISTRY[key](config, seed)
