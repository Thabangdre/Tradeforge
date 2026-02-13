from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradeforge.strategy.user_ea import run_user_ea


def _buy_breakout_ticks():
    return [
        {"time": "t1", "bid": 1.0999, "ask": 1.1001, "high": 1.1002, "low": 1.0998},
        {"time": "t2", "bid": 1.1000, "ask": 1.1002, "high": 1.1003, "low": 1.0999},
        {"time": "t3", "bid": 1.1000, "ask": 1.1002, "high": 1.1003, "low": 1.0999},
        # Breakout above previous highs -> BUY entry
        {"time": "t4", "bid": 1.1004, "ask": 1.1007, "high": 1.1008, "low": 1.1002},
        # Hit TP on next tick
        {"time": "t5", "bid": 1.1010, "ask": 1.1012, "high": 1.1012, "low": 1.1006},
    ]


def _sell_sl_ticks():
    return [
        {"time": "s1", "bid": 1.2000, "ask": 1.2002, "high": 1.2003, "low": 1.1998},
        {"time": "s2", "bid": 1.1999, "ask": 1.2001, "high": 1.2002, "low": 1.1997},
        {"time": "s3", "bid": 1.1998, "ask": 1.2000, "high": 1.2001, "low": 1.1996},
        # Break below previous lows -> SELL entry
        {"time": "s4", "bid": 1.1994, "ask": 1.1996, "high": 1.1998, "low": 1.1992},
        # Rise to stop loss
        {"time": "s5", "bid": 1.1998, "ask": 1.2000, "high": 1.2000, "low": 1.1995},
    ]


def test_expected_breakout_signal_and_tp_exit():
    config = {
        "lot": 0.2,
        "sl_pips": 2,
        "tp_pips": 4,
        "breakout_window": 3,
        "pip_size": 0.0001,
    }

    events = run_user_ea(config, _buy_breakout_ticks())
    assert len(events) == 2

    entry, exit_evt = events
    assert entry.type == "ENTRY"
    assert entry.time == "t4"
    assert entry.direction == "BUY"
    assert entry.lot == 0.2
    assert entry.entry == 1.1007
    assert round(entry.stop_loss, 6) == 1.1005
    assert round(entry.take_profit, 6) == 1.1011

    assert exit_evt.type == "EXIT"
    assert exit_evt.time == "t5"
    assert exit_evt.reason == "TP"
    assert round(exit_evt.exit_price, 6) == 1.1011


def test_stop_loss_event_for_short_trade():
    config = {
        "lot": 0.1,
        "sl_pips": 3,
        "tp_pips": 6,
        "breakout_window": 3,
        "pip_size": 0.0001,
    }

    events = run_user_ea(config, _sell_sl_ticks())
    assert len(events) == 2

    entry, exit_evt = events
    assert entry.type == "ENTRY"
    assert entry.direction == "SELL"
    assert entry.time == "s4"

    assert exit_evt.type == "EXIT"
    assert exit_evt.reason == "SL"
    assert exit_evt.time == "s5"


def test_deterministic_trades_across_runs():
    config = {
        "lot": 0.3,
        "sl_pips": 2,
        "tp_pips": 5,
        "breakout_window": 3,
        "use_mid_price_filter": True,
        "pip_size": 0.0001,
    }
    tick_data = _buy_breakout_ticks() + _sell_sl_ticks()

    run_a = run_user_ea(copy.deepcopy(config), copy.deepcopy(tick_data))
    run_b = run_user_ea(copy.deepcopy(config), copy.deepcopy(tick_data))

    assert run_a == run_b
