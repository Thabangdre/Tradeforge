from tradeforge.broker.account import Account


def test_buy_floating_pnl_updates_with_bid() -> None:
    account = Account(initial_balance=1000.0)
    account.on_order_filled(side="BUY", volume=2.0, entry_price=100.0)

    account.on_price_update(bid=101.5, ask=101.7)

    assert account.floating_pnl == 3.0
    assert account.equity == 1003.0


def test_sell_floating_pnl_updates_with_ask() -> None:
    account = Account(initial_balance=1000.0)
    account.on_order_filled(side="SELL", volume=2.0, entry_price=100.0)

    account.on_price_update(bid=98.0, ask=98.5)

    assert account.floating_pnl == 3.0
    assert account.equity == 1003.0


def test_sl_close_updates_balance_correctly() -> None:
    account = Account(initial_balance=1000.0)
    account.on_order_filled(side="BUY", volume=2.0, entry_price=100.0, sl=99.0)

    account.on_price_update(bid=98.5, ask=98.7)

    assert len(account.open_positions) == 0
    assert len(account.closed_trades) == 1
    assert account.realized_pnl == -2.0
    assert account.balance == 998.0
    assert account.floating_pnl == 0.0
    assert account.equity == 998.0


def _run_deterministic_scenario() -> float:
    account = Account(initial_balance=1000.0)
    account.on_order_filled(side="BUY", volume=2.0, entry_price=100.0, tp=101.0)
    account.on_order_filled(side="SELL", volume=1.0, entry_price=105.0, sl=106.0)

    prices = [
        (100.5, 100.7),
        (101.1, 101.3),
        (105.5, 106.1),
    ]
    for bid, ask in prices:
        account.on_price_update(bid=bid, ask=ask)

    return account.equity


def test_deterministic_equity_across_runs() -> None:
    results = [_run_deterministic_scenario() for _ in range(10)]

    assert len(set(results)) == 1
    assert results[0] == 1001.0
