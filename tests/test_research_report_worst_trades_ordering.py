from backtest import BacktestResult, Event, Trade, build_research_report


class OrderingStrategy:
    def run(self, bars, symbol, exec_config, initial_cash, path, spread=0.0):
        if path == "WORST_CASE":
            trades = [
                Trade("B", "LONG", 100.0, 99.0, -1.0, "b", 1, 8),
                Trade("A", "LONG", 100.0, 99.0, -1.0, "a", 1, 7),
                Trade("C", "SHORT", 102.0, 98.0, -2.0, "c", 2, 9),
                Trade("D", "SHORT", 101.0, 100.0, 1.0, "d", 3, 10),
            ]
        else:
            trades = [
                Trade("A", "LONG", 100.0, 100.5, 0.5, "a", 1, 7),
                Trade("B", "LONG", 100.0, 100.4, 0.4, "b", 1, 8),
                Trade("C", "SHORT", 102.0, 101.9, 0.1, "c", 2, 9),
            ]
        events = [Event(trade.open_ts, trade.trade_id, "FILL", {}) for trade in trades]
        total_pnl = sum(t.pnl for t in trades)
        return BacktestResult(
            trades=trades,
            events=events,
            total_pnl=total_pnl,
            ending_cash=initial_cash + total_pnl,
        )


def test_worst_trades_stable_ordering_with_tie_breakers():
    report = build_research_report(
        bars=[{"ts": i} for i in range(10)],
        strategy=OrderingStrategy(),
        symbol="TEST",
        exec_config={},
        spreads={"x": 0.1, "y": 0.2, "z": 0.3},
        initial_cash=500.0,
        top_n_losses=3,
    )

    ordered_ids = [trade["trade_id"] for trade in report["worst_trades"]]
    assert ordered_ids == ["C", "A", "B"]

    ordered_pnls = [trade["pnl"] for trade in report["worst_trades"]]
    assert ordered_pnls == sorted(ordered_pnls)
