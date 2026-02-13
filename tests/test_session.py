from pathlib import Path

from tradeforge.engine.session import Session, SessionConfig


FIXTURE = Path(__file__).parent / "fixtures" / "sample_ticks.csv"


def test_session_produces_deterministic_equity_curve_for_fixture_ticks():
    session = Session(SessionConfig(tick_file=str(FIXTURE), seed=7, starting_balance=1_000.0))

    result = session.run()

    assert [point["equity"] for point in result.equity_curve] == [
        1000.0,
        1001.0,
        1001.0,
        1001.0,
        1002.0,
        997.0,
    ]


def test_same_seed_and_data_produces_identical_results():
    config = SessionConfig(tick_file=str(FIXTURE), seed=11, starting_balance=1_000.0)

    result_one = Session(config).run()
    result_two = Session(config).run()

    assert result_one.final_balance == result_two.final_balance
    assert result_one.equity_curve == result_two.equity_curve
    assert [trade.__dict__ for trade in result_one.trades] == [trade.__dict__ for trade in result_two.trades]


def test_trade_list_matches_expected_events():
    session = Session(SessionConfig(tick_file=str(FIXTURE), seed=7, starting_balance=1_000.0))

    result = session.run()

    observed = [
        {
            "timestamp": trade.timestamp,
            "side": trade.side,
            "qty": trade.qty,
            "price": trade.price,
        }
        for trade in result.trades
    ]

    assert observed == [
        {"timestamp": "2024-01-01T00:00:00Z", "side": "BUY", "qty": 1, "price": 100.0},
        {"timestamp": "2024-01-01T00:01:00Z", "side": "SELL", "qty": 1, "price": 101.0},
        {"timestamp": "2024-01-01T00:03:00Z", "side": "BUY", "qty": 1, "price": 102.0},
        {"timestamp": "2024-01-01T00:05:00Z", "side": "SELL", "qty": 1, "price": 98.0},
    ]
