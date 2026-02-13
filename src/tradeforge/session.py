from __future__ import annotations

from collections.abc import Iterable

from tradeforge.account import Account
from tradeforge.broker import Broker
from tradeforge.models import Tick, Trade
from tradeforge.strategy.interface import Strategy


class SessionRunner:
    def __init__(self, strategy: Strategy, broker: Broker | None = None, account: Account | None = None) -> None:
        self.strategy = strategy
        self.broker = broker or Broker()
        self.account = account or Account()

    def run(self, ticks: Iterable[Tick]) -> list[Trade]:
        for tick in ticks:
            self.broker.set_current_tick(tick)
            self.strategy.on_tick(tick, self.broker, self.account)
        return self.broker.trades
