from __future__ import annotations

from tradeforge.optimize.sweep import run_parameter_sweep, top_n


def sample_ticks():
    return [100.0, 101.2, 99.7, 102.3, 101.0, 103.6, 102.2, 104.1, 103.2, 105.0]


def test_sweep_runs_multiple_combinations_deterministically():
    ticks = sample_ticks()
    base = {"risk": 1.0}
    grid = {"window": [2, 3], "threshold": [0.6, 1.0]}

    first = run_parameter_sweep("bbma", ticks, base, grid, seed=7)
    second = run_parameter_sweep("bbma", ticks, base, grid, seed=7)

    assert len(first) == 4
    assert first == second


def test_top_n_ranking_stable_across_runs():
    ticks = sample_ticks()
    base = {"risk": 1.0}
    grid = {"window": [2, 3, 4], "threshold": [0.6, 0.8]}

    results_a = run_parameter_sweep("bbma", ticks, base, grid, seed=11)
    results_b = run_parameter_sweep("bbma", ticks, base, grid, seed=11)

    assert top_n(results_a, key="total_pnl", n=3) == top_n(results_b, key="total_pnl", n=3)


def test_sweep_supports_two_strategies_bbma_and_fibo():
    ticks = sample_ticks()

    bbma_results = run_parameter_sweep(
        "bbma",
        ticks,
        {"risk": 1.0},
        {"window": [2, 3], "threshold": [0.6]},
        seed=5,
    )
    fibo_results = run_parameter_sweep(
        "fibo",
        ticks,
        {"leverage": 1.0},
        {"step": [2, 3], "retrace": [0.5]},
        seed=5,
    )

    assert len(bbma_results) == 2
    assert len(fibo_results) == 2

    for result in [*bbma_results, *fibo_results]:
        assert set(["total_pnl", "max_drawdown", "trade_count", "win_rate", "profit_factor", "expectancy"]).issubset(result)
