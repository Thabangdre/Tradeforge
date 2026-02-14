from backtest import (
    Bar,
    ExecutionConfig,
    FixedSpreadModel,
    IntraBarPath,
    Order,
    Side,
    compare_paths,
)


def test_compare_paths_outputs_and_is_deterministic():
    bars = [Bar(1, 100, 100, 100, 100), Bar(2, 100, 106, 94, 100)]

    def strategy(i, bar, positions):
        if i == 0:
            return [Order(side=Side.BUY, qty=1, tp=105, sl=95)]
        return []

    cfg = ExecutionConfig(path=IntraBarPath.OHLC)
    first = compare_paths(bars, strategy, "X", FixedSpreadModel(2.0), cfg)
    second = compare_paths(bars, strategy, "X", FixedSpreadModel(2.0), cfg)

    assert "worst" in first and "ohlc" in first and "summary" in first
    for key in ["net_pnl", "profit_factor", "max_drawdown", "total_trades", "win_rate"]:
        assert key in first["summary"]["worst"]
        assert key in first["summary"]["ohlc"]
    assert first["summary"] == second["summary"]
