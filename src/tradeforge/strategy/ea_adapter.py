from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Deque, Iterable, List, Sequence


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Tick:
    """Single market tick."""

    timestamp: int
    price: float


@dataclass
class AccountState:
    """Minimal account state exposed to user EA signals."""

    position: int = 0
    balance: float = 0.0


@dataclass(frozen=True)
class Order:
    """Deterministic order record produced by the adapter."""

    timestamp: int
    side: str
    quantity: int
    price: float


class Strategy:
    """Base strategy contract for the TradeForge engine."""

    def on_tick(self, tick: Tick, account: AccountState) -> Sequence[Order]:
        raise NotImplementedError


SignalFn = Callable[[Sequence[Tick], AccountState], Action]


class EAAdapter(Strategy):
    """Adapter for user-defined EA signal logic.

    The adapter stores a rolling tick buffer, executes the provided signal function
    on each incoming tick, and translates returned actions into deterministic
    order records.
    """

    def __init__(self, signal_fn: SignalFn, max_history: int = 512, order_size: int = 1):
        if max_history <= 0:
            raise ValueError("max_history must be positive")
        if order_size <= 0:
            raise ValueError("order_size must be positive")

        self.signal_fn = signal_fn
        self.order_size = order_size
        self._ticks: Deque[Tick] = deque(maxlen=max_history)
        self.trade_log: List[Order] = []

    @property
    def tick_history(self) -> Sequence[Tick]:
        return tuple(self._ticks)

    def on_tick(self, tick: Tick, account: AccountState) -> Sequence[Order]:
        self._ticks.append(tick)
        action = self.signal_fn(self.tick_history, account)

        orders = self._orders_for_action(action=action, tick=tick, account=account)
        self.trade_log.extend(orders)
        return tuple(orders)

    def _orders_for_action(self, action: Action, tick: Tick, account: AccountState) -> List[Order]:
        if action == Action.HOLD:
            return []

        if action == Action.BUY:
            account.position += self.order_size
            return [Order(timestamp=tick.timestamp, side="BUY", quantity=self.order_size, price=tick.price)]

        if action == Action.SELL:
            account.position -= self.order_size
            return [Order(timestamp=tick.timestamp, side="SELL", quantity=self.order_size, price=tick.price)]

        if action == Action.CLOSE:
            if account.position == 0:
                return []

            if account.position > 0:
                qty = account.position
                account.position = 0
                return [Order(timestamp=tick.timestamp, side="SELL", quantity=qty, price=tick.price)]

            qty = abs(account.position)
            account.position = 0
            return [Order(timestamp=tick.timestamp, side="BUY", quantity=qty, price=tick.price)]

        raise ValueError(f"Unsupported action: {action}")


def sma_cross_signal(short_window: int = 3, long_window: int = 5) -> SignalFn:
    """Example EA: simple moving-average crossover signal function."""

    if short_window <= 0 or long_window <= 0:
        raise ValueError("Moving-average windows must be positive")
    if short_window >= long_window:
        raise ValueError("short_window must be smaller than long_window")

    def _signal(ticks: Sequence[Tick], account: AccountState) -> Action:
        if len(ticks) < long_window:
            return Action.HOLD

        short_avg = sum(t.price for t in ticks[-short_window:]) / short_window
        long_avg = sum(t.price for t in ticks[-long_window:]) / long_window

        if short_avg > long_avg and account.position <= 0:
            return Action.BUY
        if short_avg < long_avg and account.position >= 0:
            return Action.SELL
        return Action.HOLD

    return _signal


def run_strategy(strategy: Strategy, ticks: Iterable[Tick], account: AccountState | None = None) -> List[Order]:
    """Utility runner used by tests/examples for deterministic playback."""

    state = account or AccountState()
    output: List[Order] = []
    for tick in ticks:
        output.extend(strategy.on_tick(tick, state))
    return output
