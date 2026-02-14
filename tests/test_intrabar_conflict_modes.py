from backtest import Bar, ExecutionConfig, FixedSpreadModel, IntraBarPath, Order, Side, run_backtest


def _run(path):
    bars = [Bar(1, 100, 100, 100, 100), Bar(2, 100, 106, 94, 100)]

    def strategy(i, bar, positions):
        if i == 0:
            return [Order(side=Side.BUY, qty=1, tp=105, sl=95)]
        return []

    return run_backtest(
        bars,
        strategy,
        "X",
        FixedSpreadModel(2.0),
        ExecutionConfig(path=path, slippage=0.0),
    )


def test_conflict_ohlc_prefers_tp():
    res = _run(IntraBarPath.OHLC)
    assert res.trades[0].reason == "tp"


def test_conflict_worst_case_prefers_sl():
    res = _run(IntraBarPath.WORST_CASE)
    assert res.trades[0].reason == "sl"
