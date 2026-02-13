from __future__ import annotations

from tradeforge.strategy.interface import Strategy


class BuyFirstTickCloseAfterN(Strategy):
    def __init__(self, close_after_ticks: int, qty: float = 1.0) -> None:
        self.close_after_ticks = close_after_ticks
        self.qty = qty
        self._entry_tick: int | None = None

    def on_tick(self, tick, broker, account):
        if self._entry_tick is None:
            broker.buy(self.qty)
            account.position += self.qty
            self._entry_tick = tick.index
            return

        if account.position > 0 and tick.index - self._entry_tick >= self.close_after_ticks:
            broker.close_position(account.position)
            account.position = 0.0
