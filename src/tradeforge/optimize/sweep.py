from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path
from typing import Any

from tradeforge.registry import create_strategy
from tradeforge.session import SessionRunner

# Ensure built-in strategies are registered.
from tradeforge import strategies as _strategies  # noqa: F401


METRIC_KEYS = (
    "total_pnl",
    "max_drawdown",
    "trade_count",
    "win_rate",
    "profit_factor",
    "expectancy",
)


def _param_combinations(param_grid: dict[str, list[Any]]):
    if not param_grid:
        yield {}
        return

    keys = list(param_grid.keys())
    values_product = itertools.product(*(param_grid[key] for key in keys))
    for values in values_product:
        yield dict(zip(keys, values, strict=True))


def _compute_metrics(trades: list[float]) -> dict[str, float | int]:
    total_pnl = sum(trades)
    trade_count = len(trades)

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for pnl in trades:
        equity += pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)

    wins = [x for x in trades if x > 0]
    losses = [x for x in trades if x < 0]
    win_rate = (len(wins) / trade_count) if trade_count else 0.0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    expectancy = (total_pnl / trade_count) if trade_count else 0.0

    return {
        "total_pnl": total_pnl,
        "max_drawdown": max_drawdown,
        "trade_count": trade_count,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
    }


def run_parameter_sweep(
    strategy_name: str,
    ticks,
    base_config: dict,
    param_grid: dict,
    seed: int,
):
    results: list[dict[str, Any]] = []
    tick_list = list(ticks)

    for params in _param_combinations(param_grid):
        config = {**base_config, **params}
        strategy = create_strategy(strategy_name, config)
        runner = SessionRunner(ticks=tick_list, strategy=strategy, seed=seed)
        trades = runner.run()

        metrics = _compute_metrics(trades)
        results.append(
            {
                "strategy_name": strategy_name,
                "seed": seed,
                "config": config,
                **metrics,
            }
        )

    return results


def to_csv(results, path):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if not results:
        destination.write_text("")
        return destination

    base_fields = ["strategy_name", "seed", "config", *METRIC_KEYS]
    extra_fields = sorted({k for row in results for k in row.keys()} - set(base_fields))
    fieldnames = [*base_fields, *extra_fields]

    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            prepared = dict(row)
            if "config" in prepared:
                prepared["config"] = json.dumps(prepared["config"], sort_keys=True)
            writer.writerow(prepared)

    return destination


def top_n(results, key="total_pnl", n=20):
    def sort_key(row: dict[str, Any]):
        key_value = row.get(key, float("-inf"))
        config_blob = json.dumps(row.get("config", {}), sort_keys=True)
        return (-key_value, row.get("strategy_name", ""), config_blob)

    return sorted(results, key=sort_key)[:n]
