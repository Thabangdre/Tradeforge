from backtest import BacktestResult, Event, Trade, build_research_report, format_research_report


class DummyStrategy:
    def run(self, bars, symbol, exec_config, initial_cash, path, spread=0.0):
        if path == "WORST_CASE":
            trades = [
                Trade("T1", "LONG", 100.0, 98.0, -2.0 - spread, "stop", 1, 4),
                Trade("T2", "SHORT", 99.0, 95.0, 4.0 - spread, "target", 5, 8),
            ]
            events = [
                Event(1, "T1", "FILL", {"price": 100.0}),
                Event(2, "T1", "PARTIAL", {"qty": 0.5}),
                Event(3, "T1", "BREAKEVEN", {"armed": True}),
                Event(4, "T1", "FILL", {"price": 98.0}),
                Event(5, "T2", "FILL", {"price": 99.0}),
                Event(6, "T2", "FLIP", {"side": "SHORT"}),
                Event(8, "T2", "FILL", {"price": 95.0}),
            ]
        else:
            trades = [
                Trade("T1", "LONG", 100.0, 99.0, -1.0, "stop", 1, 4),
                Trade("T2", "SHORT", 99.0, 96.0, 3.0, "target", 5, 8),
            ]
            events = [
                Event(1, "T1", "FILL", {"price": 100.0}),
                Event(4, "T1", "FILL", {"price": 99.0}),
                Event(5, "T2", "FILL", {"price": 99.0}),
                Event(8, "T2", "FILL", {"price": 96.0}),
            ]

        total_pnl = round(sum(t.pnl for t in trades), 6)
        return BacktestResult(
            trades=trades,
            events=events,
            total_pnl=total_pnl,
            ending_cash=initial_cash + total_pnl,
        )


def test_research_report_is_deterministic_and_complete():
    bars = [{"ts": i, "open": 100 + i} for i in range(12)]
    strategy = DummyStrategy()
    spreads = {"stress": 0.25, "base": 0.05, "calm": 0.01}

    report_a = build_research_report(
        bars=bars,
        strategy=strategy,
        symbol="TEST",
        exec_config={"mode": "sim"},
        spreads=spreads,
        initial_cash=1000.0,
        top_n_losses=10,
    )
    report_b = build_research_report(
        bars=bars,
        strategy=strategy,
        symbol="TEST",
        exec_config={"mode": "sim"},
        spreads=spreads,
        initial_cash=1000.0,
        top_n_losses=10,
    )

    assert set(report_a) == {
        "headline",
        "diagnostic",
        "fragility",
        "spread_stress",
        "fill_flip",
        "worst_trades",
    }
    assert report_a == report_b

    text_a = format_research_report(report_a)
    text_b = format_research_report(report_b)
    assert text_a == text_b
