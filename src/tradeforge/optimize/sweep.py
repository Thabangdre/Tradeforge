"""Parameter sweep utilities for strategy optimization."""

from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path

from tradeforge.registry import create_strategy
from tradeforge.runner import SessionRunner
from tradeforge import strategies as _strategies  # noqa: F401


_METRIC_KEYS = (
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
) -> list[dict]:
    """Run a full Cartesian parameter sweep and collect core metrics."""
    grid_keys = sorted(param_grid.keys())
    grid_values = [param_grid[key] for key in grid_keys]
    results: list[dict] = []

    for combo in itertools.product(*grid_values):
        params = dict(zip(grid_keys, combo, strict=True))
        config = {**base_config, **params}
        strategy = create_strategy(strategy_name, config, seed)
        metrics = SessionRunner(ticks=ticks, strategy=strategy, seed=seed).run()
        results.append(
            {
                "strategy": strategy_name,
                "seed": seed,
                "params": params,
                **{k: metrics[k] for k in _METRIC_KEYS},
            }
        )

    return results


def to_csv(results, path) -> None:
    """Write sweep results to CSV."""
    rows = list(results)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serializable = dict(row)
            if isinstance(serializable.get("params"), dict):
                serializable["params"] = json.dumps(serializable["params"], sort_keys=True)
            writer.writerow(serializable)


def top_n(results, key: str = "total_pnl", n: int = 20) -> list[dict]:
    """Return top N ranked results by metric key with deterministic tie-breaking."""
    rows = list(results)
    return sorted(
        rows,
        key=lambda row: (
            row.get(key, float("-inf")),
            json.dumps(row.get("params", {}), sort_keys=True),
            row.get("strategy", ""),
        ),
        reverse=True,
    )[:n]
