from backtest import (
    Bar,
    ExecutionConfig,
    FixedSpreadModel,
    IntraBarPath,
    Order,
    Side,
    run_backtest,
)


def test_long_entry_and_exit_use_ask_and_bid_sides():
    bars = [Bar(1, 100, 101, 99, 100), Bar(2, 100, 105, 99, 102)]

    def strategy(i, bar, positions):
        if i == 0:
            return [Order(side=Side.BUY, qty=1, tp=103)]
        return []

    res = run_backtest(
        bars,
        strategy,
        "X",
        FixedSpreadModel(2.0),
        ExecutionConfig(path=IntraBarPath.OHLC, slippage=0.0),
    )
    trade = res.trades[0]
    assert trade.entry_price == 101.0  # ask at first bar close
    # TP level 103, second bar bid=101 => executable sell side is bid=min(level,bid)
    assert trade.exit_price == 101.0


def test_short_entry_and_exit_use_bid_and_ask_sides():
    bars = [Bar(1, 100, 101, 99, 100), Bar(2, 100, 101, 94, 96)]

    def strategy(i, bar, positions):
        if i == 0:
            return [Order(side=Side.SELL, qty=1, tp=95)]
        return []

    res = run_backtest(
        bars,
        strategy,
        "X",
        FixedSpreadModel(2.0),
        ExecutionConfig(path=IntraBarPath.OHLC, slippage=0.0),
    )
    trade = res.trades[0]
    assert trade.entry_price == 99.0  # bid at first bar close
    # TP level 95, second bar ask=97 => executable buy side is ask=max(level,ask)
    assert trade.exit_price == 97.0
