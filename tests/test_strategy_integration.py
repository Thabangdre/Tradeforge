from tradeforge.models import Tick, Trade
from tradeforge.session import SessionRunner
from tradeforge.strategy.examples import BuyFirstTickCloseAfterN
from tradeforge.strategy.interface import Strategy


class RecordingStrategy(Strategy):
    def __init__(self):
        self.seen_ticks = []

    def on_tick(self, tick, broker, account):
        self.seen_ticks.append(tick.index)


class BuyOnceStrategy(Strategy):
    def on_tick(self, tick, broker, account):
        if tick.index == 0:
            broker.buy(2)
            account.position += 2


def test_strategy_receives_ticks_in_order():
    strategy = RecordingStrategy()
    ticks = [Tick(index=0, price=100), Tick(index=1, price=101), Tick(index=2, price=102)]

    SessionRunner(strategy=strategy).run(ticks)

    assert strategy.seen_ticks == [0, 1, 2]


def test_strategy_orders_executed_by_broker():
    strategy = BuyOnceStrategy()
    ticks = [Tick(index=0, price=100), Tick(index=1, price=101)]

    trades = SessionRunner(strategy=strategy).run(ticks)

    assert trades == [Trade(side="buy", qty=2, price=100, tick_index=0)]


def test_trade_list_deterministic_for_example_strategy():
    strategy = BuyFirstTickCloseAfterN(close_after_ticks=2, qty=1)
    ticks = [
        Tick(index=0, price=100),
        Tick(index=1, price=101),
        Tick(index=2, price=103),
        Tick(index=3, price=104),
    ]

    trades = SessionRunner(strategy=strategy).run(ticks)

    assert trades == [
        Trade(side="buy", qty=1, price=100, tick_index=0),
        Trade(side="sell", qty=1, price=103, tick_index=2),
    ]
