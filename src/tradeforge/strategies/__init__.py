"""Strategy registry for Tradeforge."""

from __future__ import annotations

from typing import Any, Callable, Dict, Type

STRATEGY_REGISTRY: Dict[str, Type[Any]] = {}


def register_strategy(name: str, strategy_cls: Type[Any]) -> None:
    """Register a strategy class under a stable string name."""
    STRATEGY_REGISTRY[name] = strategy_cls


def get_strategy(name: str) -> Type[Any]:
    """Fetch a strategy class by name."""
    return STRATEGY_REGISTRY[name]


# Import modules that self-register strategies.
from .warisan import WarisanStrategy  # noqa: E402,F401
