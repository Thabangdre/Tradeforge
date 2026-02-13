from __future__ import annotations

from tradeforge.models import Tick, Trade


class Broker:
    def __init__(self) -> None:
        self._current_tick: Tick | None = None
        self._trades: list[Trade] = []

    @property
    def trades(self) -> list[Trade]:
        return list(self._trades)

    def set_current_tick(self, tick: Tick) -> None:
        self._current_tick = tick

    def buy(self, qty: float = 1.0) -> None:
        self._execute_trade(side="buy", qty=qty)

    def sell(self, qty: float = 1.0) -> None:
        self._execute_trade(side="sell", qty=qty)

    def close_position(self, position: float) -> None:
        if position > 0:
            self.sell(position)
        elif position < 0:
            self.buy(-position)

    def _execute_trade(self, side: str, qty: float) -> None:
        if self._current_tick is None:
            raise RuntimeError("Cannot execute order without an active tick")
        self._trades.append(
            Trade(
                side=side,
                qty=qty,
                price=self._current_tick.price,
                tick_index=self._current_tick.index,
            )
        )
