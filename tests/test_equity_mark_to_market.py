from backtest import Bar, ExecutionConfig, FixedSpreadModel, IntraBarPath, Order, Side, run_backtest


def test_equity_curve_marks_to_market_unrealized_pnl():
    bars = [
        Bar(1, 100, 101, 99, 100),
        Bar(2, 100, 100, 90, 92),
        Bar(3, 92, 105, 91, 104),
    ]

    def strategy(i, bar, positions):
        if i == 0:
            return [Order(side=Side.BUY, qty=1, tp=104)]
        return []

    result = run_backtest(
        bars,
        strategy,
        symbol="X",
        spread_model=FixedSpreadModel(2.0),
        exec_config=ExecutionConfig(path=IntraBarPath.OHLC),
        initial_cash=1000.0,
    )

    # Entry at ask=101. Bar2 mid=92 => bid=91 => unrealized -10.
    assert result.equity_curve[1][1] == 990.0
    assert result.equity_curve[1][1] < result.equity_curve[0][1]
    assert result.metrics.max_drawdown > 0
