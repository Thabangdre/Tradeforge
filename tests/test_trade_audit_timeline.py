from backtest import (
    Bar,
    ExecutionConfig,
    FixedSpreadModel,
    IntraBarPath,
    Order,
    Side,
    build_trade_audit,
    run_backtest,
)


def test_trade_audit_contains_partial_be_and_exit_ordering():
    bars = [
        Bar(1, 100, 100, 100, 100),
        Bar(2, 100, 103, 99, 102),
        Bar(3, 102, 106, 101, 104),
    ]

    def strategy(i, bar, positions):
        if i == 0:
            return [
                Order(
                    side=Side.BUY,
                    qty=2,
                    tp=105,
                    sl=95,
                    partial_tp=103,
                    partial_qty=1,
                    move_be_on_partial=True,
                )
            ]
        return []

    res = run_backtest(
        bars,
        strategy,
        "X",
        FixedSpreadModel(2.0),
        ExecutionConfig(path=IntraBarPath.OHLC),
    )
    audit = build_trade_audit(res.events, res.trades)
    row = audit[0]

    assert row["partial_ts"] == 2
    assert row["be_ts"] == 2
    assert row["exit_ts"] == 3
    assert row["partial_ts"] <= row["be_ts"] <= row["exit_ts"]
    assert row["partial_price"] is not None
    assert row["exit_price"] is not None
