from tradeforge.strategy.ea_adapter import (
    Action,
    AccountState,
    EAAdapter,
    Tick,
    run_strategy,
    sma_cross_signal,
)


def test_ea_adapter_calls_signal_each_tick():
    calls = []

    def signal(ticks, account):
        calls.append((len(ticks), account.position))
        return Action.HOLD

    adapter = EAAdapter(signal_fn=signal, max_history=10)
    account = AccountState()
    ticks = [Tick(timestamp=i, price=100 + i) for i in range(6)]

    for tick in ticks:
        adapter.on_tick(tick, account)

    assert len(calls) == len(ticks)
    assert calls[-1][0] == 6


def test_signals_produce_expected_orders():
    actions = [Action.BUY, Action.HOLD, Action.CLOSE, Action.SELL, Action.CLOSE]

    def signal(_ticks, _account):
        return actions.pop(0)

    adapter = EAAdapter(signal_fn=signal, order_size=2)
    account = AccountState()
    ticks = [Tick(timestamp=i, price=100 + i) for i in range(5)]

    orders = run_strategy(adapter, ticks, account)

    assert [(o.side, o.quantity) for o in orders] == [
        ("BUY", 2),
        ("SELL", 2),
        ("SELL", 2),
        ("BUY", 2),
    ]
    assert account.position == 0


def test_trade_list_is_deterministic_across_runs():
    ticks = [
        Tick(timestamp=1, price=100),
        Tick(timestamp=2, price=101),
        Tick(timestamp=3, price=102),
        Tick(timestamp=4, price=103),
        Tick(timestamp=5, price=102),
        Tick(timestamp=6, price=101),
        Tick(timestamp=7, price=100),
    ]

    def replay_once():
        strategy = EAAdapter(signal_fn=sma_cross_signal(short_window=2, long_window=3))
        return run_strategy(strategy, ticks, AccountState())

    first = replay_once()
    second = replay_once()

    assert first == second
    assert len(first) > 0
