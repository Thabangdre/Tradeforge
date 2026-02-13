from tradeforge.broker.execution import BrokerSimulator
from tradeforge.broker.orders import Order


def test_buy_fills_at_ask() -> None:
    broker = BrokerSimulator()
    broker.submit_order(Order(id="1", type="MARKET", side="BUY", price=None, sl=None, tp=None, volume=1.0))

    fills = broker.process_tick(timestamp_ms=1000, bid=10.0, ask=10.2)

    assert len(fills) == 1
    assert fills[0].price == 10.2
    assert fills[0].reason == "market"


def test_sell_fills_at_bid() -> None:
    broker = BrokerSimulator()
    broker.submit_order(Order(id="1", type="MARKET", side="SELL", price=None, sl=None, tp=None, volume=1.0))

    fills = broker.process_tick(timestamp_ms=1000, bid=10.0, ask=10.2)

    assert len(fills) == 1
    assert fills[0].price == 10.0
    assert fills[0].reason == "market"


def test_buy_sl_triggered_when_bid_below_or_equal_sl() -> None:
    broker = BrokerSimulator()
    broker.submit_order(Order(id="1", type="MARKET", side="BUY", price=None, sl=9.8, tp=None, volume=1.0))

    broker.process_tick(timestamp_ms=1000, bid=10.0, ask=10.2)
    fills = broker.process_tick(timestamp_ms=1100, bid=9.8, ask=10.0)

    assert len(fills) == 1
    assert fills[0].reason == "sl"
    assert fills[0].price == 9.8


def test_sell_sl_triggered_when_ask_above_or_equal_sl() -> None:
    broker = BrokerSimulator()
    broker.submit_order(Order(id="1", type="MARKET", side="SELL", price=None, sl=10.3, tp=None, volume=1.0))

    broker.process_tick(timestamp_ms=1000, bid=10.0, ask=10.2)
    fills = broker.process_tick(timestamp_ms=1100, bid=10.1, ask=10.3)

    assert len(fills) == 1
    assert fills[0].reason == "sl"
    assert fills[0].price == 10.3


def test_deterministic_fills_across_runs() -> None:
    ticks = [
        (1000, 10.0, 10.2),
        (1100, 9.9, 10.1),
        (1200, 9.7, 9.9),
    ]

    def run_once():
        broker = BrokerSimulator()
        broker.submit_order(Order(id="2", type="MARKET", side="SELL", price=None, sl=10.3, tp=9.8, volume=1.0))
        broker.submit_order(Order(id="1", type="MARKET", side="BUY", price=None, sl=9.8, tp=10.5, volume=1.0))
        all_fills = []
        for ts, bid, ask in ticks:
            all_fills.extend(broker.process_tick(timestamp_ms=ts, bid=bid, ask=ask))
        return all_fills

    first = run_once()
    second = run_once()

    assert first == second
