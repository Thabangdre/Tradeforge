from tradeforge.optimize.sweep import run_parameter_sweep, top_n


def _ticks():
    return [
        {"price": 100.0, "baseline": 99.8, "return": 1.0, "momentum": 0.40},
        {"price": 99.5, "baseline": 99.8, "return": -0.8, "momentum": -0.30},
        {"price": 100.2, "baseline": 100.0, "return": 0.6, "momentum": 0.20},
        {"price": 99.4, "baseline": 99.9, "return": -0.7, "momentum": -0.25},
        {"price": 100.4, "baseline": 100.1, "return": 0.9, "momentum": 0.35},
    ]


def test_sweep_runs_multiple_combinations_deterministically():
    ticks = _ticks()
    base_config = {"sensitivity": 1.0}
    param_grid = {"threshold": [0.15, 0.25], "sensitivity": [0.8, 1.0]}

    first = run_parameter_sweep("bbma", ticks, base_config, param_grid, seed=7)
    second = run_parameter_sweep("bbma", ticks, base_config, param_grid, seed=7)

    assert len(first) == 4
    assert first == second


def test_top_n_ranking_is_stable_across_runs():
    ticks = _ticks()
    param_grid = {"threshold": [0.10, 0.20, 0.30]}
    results = run_parameter_sweep("bbma", ticks, {}, param_grid, seed=2)

    ranked_once = top_n(results, key="total_pnl", n=3)
    ranked_twice = top_n(results, key="total_pnl", n=3)

    assert ranked_once == ranked_twice


def test_sweep_supports_bbma_and_fibo_strategies():
    ticks = _ticks()

    bbma_results = run_parameter_sweep(
        "bbma",
        ticks,
        base_config={"sensitivity": 1.0},
        param_grid={"threshold": [0.15, 0.25]},
        seed=11,
    )
    fibo_results = run_parameter_sweep(
        "fibo",
        ticks,
        base_config={"retrace": 0.5},
        param_grid={"retrace": [0.3, 0.7]},
        seed=11,
    )

    assert len(bbma_results) == 2
    assert len(fibo_results) == 2
    for row in bbma_results + fibo_results:
        assert set(
            [
                "total_pnl",
                "max_drawdown",
                "trade_count",
                "win_rate",
                "profit_factor",
                "expectancy",
            ]
        ).issubset(row.keys())
