from user_ea import run_fibo_ea


def test_fib_zone_entry_on_known_ticks():
    # Confirmed bullish swing: low=100 (idx1), high=120 (idx3)
    # 0.618 retrace ~107.64, 0.786 retrace ~104.28
    ticks = [110, 100, 108, 120, 111, 108, 106, 109, 121]
    result = run_fibo_ea(
        {
            "fib_low": 0.618,
            "fib_high": 0.786,
            "sl_buffer": 1.0,
            "tp_rr": 2.0,
        },
        ticks,
    )

    assert len(result["trades"]) == 1
    trade = result["trades"][0]
    assert trade["opened_at"] == 6
    assert trade["entry"] == 106
    assert trade["sl"] == 99.0
    assert trade["tp"] == 120


def test_sl_and_tp_events():
    tp_ticks = [110, 100, 108, 120, 112, 107, 106, 119, 121]
    tp_result = run_fibo_ea(
        {
            "fib_low": 0.618,
            "fib_high": 0.786,
            "sl_buffer": 1.0,
            "tp_rr": 1.2,
        },
        tp_ticks,
    )
    assert tp_result["trades"][0]["exit_reason"] == "tp"

    sl_ticks = [110, 100, 108, 120, 111, 107, 106, 98, 95]
    sl_result = run_fibo_ea(
        {
            "fib_low": 0.618,
            "fib_high": 0.786,
            "sl_buffer": 1.0,
            "tp_rr": 1.2,
        },
        sl_ticks,
    )
    assert sl_result["trades"][0]["exit_reason"] == "sl"


def test_deterministic_trades():
    ticks = [110, 100, 108, 120, 111, 107, 106, 109, 121, 105, 122]
    config = {
        "fib_low": 0.618,
        "fib_high": 0.786,
        "sl_buffer": 1.0,
        "tp_rr": 1.8,
    }

    run1 = run_fibo_ea(config, ticks)
    run2 = run_fibo_ea(config, ticks)

    assert run1 == run2
