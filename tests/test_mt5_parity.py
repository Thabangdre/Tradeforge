from __future__ import annotations

from pathlib import Path

from tradeforge.validate.mt5_parity import (
    MatchTolerances,
    TradeRecord,
    load_mt5_trades_csv,
    match_trades,
    parity_report,
)


def _trade(
    sid: str,
    side: str,
    entry_time: int,
    entry_price: float,
    exit_time: int,
    exit_price: float,
    pnl: float,
) -> TradeRecord:
    return TradeRecord(
        source_id=sid,
        side=side,
        entry_time=entry_time,
        entry_price=entry_price,
        exit_time=exit_time,
        exit_price=exit_price,
        volume=1.0,
        pnl=pnl,
    )


def test_match_trades_small_synthetic_sample() -> None:
    tf = [
        _trade("tf1", "buy", 1_000_000, 1.1000, 1_005_000, 1.1010, 10.0),
        _trade("tf2", "sell", 2_000_000, 1.2000, 2_005_000, 1.1990, 8.0),
    ]
    mt5 = [
        _trade("m1", "buy", 1_001_500, 1.1001, 1_005_100, 1.1011, 9.95),
        _trade("m2", "sell", 2_001_000, 1.2001, 2_005_200, 1.1990, 8.01),
    ]

    result = match_trades(tf, mt5, MatchTolerances(entry_time_ms=2000, entry_price=0.0003, exit_price=0.0003, pnl=0.1))

    assert len(result["matched"]) == 2
    assert not result["unmatched_tradeforge"]
    assert not result["unmatched_mt5"]
    assert not result["mismatches"]


def test_tolerances_filter_mismatches_and_unmatched(tmp_path: Path) -> None:
    tf = [_trade("tf1", "buy", 1_000_000, 1.1000, 1_005_000, 1.1010, 10.0)]
    mt5 = [_trade("m1", "buy", 1_010_500, 1.1010, 1_005_000, 1.1040, 5.0)]

    too_strict = match_trades(tf, mt5, MatchTolerances(entry_time_ms=2000, entry_price=0.0002, exit_price=0.0002, pnl=0.1))
    assert len(too_strict["matched"]) == 0
    assert len(too_strict["unmatched_tradeforge"]) == 1
    assert len(too_strict["unmatched_mt5"]) == 1

    loose = match_trades(tf, mt5, MatchTolerances(entry_time_ms=20_000, entry_price=0.002, exit_price=0.005, pnl=10.0))
    assert len(loose["matched"]) == 1
    assert len(loose["mismatches"]) == 0

    summary = parity_report(tf, mt5, MatchTolerances(entry_time_ms=20_000, entry_price=0.0002, exit_price=0.0002, pnl=0.1), tmp_path / "mismatch.csv")
    assert summary["match_rate"] == 1.0
    assert summary["mean_abs_entry_diff"] > 0
    assert (tmp_path / "mismatch.csv").exists()


def test_deterministic_matching_order_and_mt5_loader(tmp_path: Path) -> None:
    tf = [
        _trade("tfA", "buy", 10_000, 1.1000, 12_000, 1.1005, 1.0),
        _trade("tfB", "buy", 10_000, 1.1002, 12_000, 1.1007, 1.1),
    ]

    mt5_csv = tmp_path / "mt5.csv"
    mt5_csv.write_text(
        "Ticket,Type,Time,Price,Time.1,Price.1,Volume,Profit\n"
        "2,Buy,1970-01-01 00:00:10,1.1002,1970-01-01 00:00:12,1.1007,1.0,1.1\n"
        "1,Buy,1970-01-01 00:00:10,1.1000,1970-01-01 00:00:12,1.1005,1.0,1.0\n",
        encoding="utf-8",
    )

    mt5 = load_mt5_trades_csv(mt5_csv)
    result1 = match_trades(tf, mt5, MatchTolerances(entry_time_ms=1000, entry_price=0.0003, exit_price=0.0003, pnl=0.2))
    result2 = match_trades(tf, mt5, MatchTolerances(entry_time_ms=1000, entry_price=0.0003, exit_price=0.0003, pnl=0.2))

    pairs1 = [(a.source_id, b.source_id) for a, b in result1["matched"]]
    pairs2 = [(a.source_id, b.source_id) for a, b in result2["matched"]]
    assert pairs1 == [("tfA", "1"), ("tfB", "2")]
    assert pairs1 == pairs2
