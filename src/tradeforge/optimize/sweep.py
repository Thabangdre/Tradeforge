from __future__ import annotations

import csv
from itertools import product
from pathlib import Path
from typing import Any

from tradeforge.runner import SessionRunner
from tradeforge.strategies import registry


METRIC_KEYS = (
    "total_pnl",
    "max_drawdown",
    "trade_count",
    "win_rate",
    "profit_factor",
    "expectancy",
)


def run_parameter_sweep(
    strategy_name: str,
    ticks,
    base_config: dict,
    param_grid: dict,
    seed: int,
) -> list[dict[str, Any]]:
    param_names = list(param_grid.keys())
    param_values = [param_grid[name] for name in param_names]

    results: list[dict[str, Any]] = []
    for combo_id, values in enumerate(product(*param_values)):
        combo = dict(zip(param_names, values))
        merged_config = {**base_config, **combo}

        strategy = registry.create(strategy_name)
        runner = SessionRunner(strategy=strategy, ticks=ticks, config=merged_config, seed=seed)
        metrics = runner.run()

        result = {
            "strategy": strategy_name,
            "combo_id": combo_id,
            **combo,
            **{key: metrics[key] for key in METRIC_KEYS},
        }
        results.append(result)

    return results


def to_csv(results: list[dict[str, Any]], path: str | Path) -> None:
    if not results:
        Path(path).write_text("")
        return

    fieldnames: list[str] = list(results[0].keys())
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def top_n(results: list[dict[str, Any]], key: str = "total_pnl", n: int = 20) -> list[dict[str, Any]]:
    ranked = sorted(
        results,
        key=lambda item: (
            -float(item.get(key, float("-inf"))),
            int(item.get("combo_id", 0)),
        ),
    )
    return ranked[:n]
