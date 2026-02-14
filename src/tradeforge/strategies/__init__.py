"""Strategy registry."""

from tradeforge.strategies.bbma_oa import BBMAOAConfig, BBMAOAStrategy

STRATEGY_REGISTRY = {
    "bbma": BBMAOAStrategy,
}

__all__ = ["BBMAOAConfig", "BBMAOAStrategy", "STRATEGY_REGISTRY"]
