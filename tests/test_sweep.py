from tradeforge.optimize.sweep import run_parameter_sweep, top_n


def test_sweep_runs_multiple_combinations_deterministically():
    ticks = [100 + i * 0.5 for i in range(50)]
    base = {"risk": 1.25}
    grid = {"window": [5, 10], "alpha": [0.1, 0.2]}

    first = run_parameter_sweep("bbma", ticks, base, grid, seed=7)
    second = run_parameter_sweep("bbma", ticks, base, grid, seed=7)

    assert len(first) == 4
    assert first == second


def test_ranking_is_stable_across_runs():
    ticks = [50 + i for i in range(30)]
    base = {"risk": 0.9}
    grid = {"window": [4, 8, 12], "alpha": [0.05, 0.1]}

    results_a = run_parameter_sweep("bbma", ticks, base, grid, seed=99)
    results_b = run_parameter_sweep("bbma", ticks, base, grid, seed=99)

    top_a = top_n(results_a, key="total_pnl", n=3)
    top_b = top_n(results_b, key="total_pnl", n=3)

    assert top_a == top_b


def test_sweep_supports_bbma_and_fibo_strategies():
    ticks = [80 + i * 0.2 for i in range(40)]
    base = {"risk": 1.0}

    bbma_results = run_parameter_sweep(
        "bbma",
        ticks,
        base,
        {"window": [6, 12], "alpha": [0.1]},
        seed=123,
    )
    fibo_results = run_parameter_sweep(
        "fibo",
        ticks,
        base,
        {"ratio": [1.2, 1.618], "sensitivity": [0.2]},
        seed=123,
    )

    assert len(bbma_results) == 2
    assert len(fibo_results) == 2

    expected_keys = {
        "total_pnl",
        "max_drawdown",
        "trade_count",
        "win_rate",
        "profit_factor",
        "expectancy",
    }

    assert expected_keys.issubset(bbma_results[0].keys())
    assert expected_keys.issubset(fibo_results[0].keys())
