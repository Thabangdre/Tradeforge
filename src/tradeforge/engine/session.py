from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Tick:
    timestamp: str
    price: float


class ReplayEngine:
    def __init__(self, ticks: Iterable[Tick]) -> None:
        self._ticks = list(ticks)

    def __iter__(self):
        return iter(self._ticks)


@dataclass
class TradeEvent:
    timestamp: str
    side: str
    qty: int
    price: float
    cash_after: float
    position_after: int


@dataclass
class Account:
    starting_balance: float
    cash: float = field(init=False)
    position: int = 0
    equity_curve: list[dict[str, float | str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cash = float(self.starting_balance)

    def apply_trade(self, side: str, qty: int, price: float) -> None:
        if side == "BUY":
            self.cash -= qty * price
            self.position += qty
        elif side == "SELL":
            self.cash += qty * price
            self.position -= qty
        else:
            raise ValueError(f"Unsupported side: {side}")

    def mark_to_market(self, timestamp: str, price: float) -> None:
        equity = self.cash + self.position * price
        self.equity_curve.append(
            {
                "timestamp": timestamp,
                "cash": round(self.cash, 8),
                "position": self.position,
                "price": price,
                "equity": round(equity, 8),
            }
        )


class BrokerSimulator:
    def __init__(self, rng: random.Random, buy_threshold: float = 0.35, sell_threshold: float = 0.45) -> None:
        self.rng = rng
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def maybe_create_order(self, position: int) -> str | None:
        draw = self.rng.random()
        if position == 0 and draw < self.buy_threshold:
            return "BUY"
        if position > 0 and draw < self.sell_threshold:
            return "SELL"
        return None


@dataclass
class SessionConfig:
    tick_file: str
    seed: int
    starting_balance: float = 10_000.0
    trade_qty: int = 1


@dataclass
class SessionResult:
    trades: list[TradeEvent]
    equity_curve: list[dict[str, float | str]]
    final_balance: float


class Session:
    """Simulation session runner for deterministic tick-by-tick backtests."""

    def __init__(self, config: SessionConfig) -> None:
        self.config = config
        self.result: SessionResult | None = None

    def load_tick_data(self) -> list[Tick]:
        path = Path(self.config.tick_file)
        ticks: list[Tick] = []
        with path.open("r", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                ticks.append(Tick(timestamp=row["timestamp"], price=float(row["price"])))
        return ticks

    def run(self) -> SessionResult:
        ticks = self.load_tick_data()
        replay_engine = ReplayEngine(ticks)
        rng = random.Random(self.config.seed)
        broker = BrokerSimulator(rng=rng)
        account = Account(starting_balance=self.config.starting_balance)
        trades: list[TradeEvent] = []

        for tick in replay_engine:
            side = broker.maybe_create_order(account.position)
            if side is not None:
                account.apply_trade(side=side, qty=self.config.trade_qty, price=tick.price)
                trades.append(
                    TradeEvent(
                        timestamp=tick.timestamp,
                        side=side,
                        qty=self.config.trade_qty,
                        price=tick.price,
                        cash_after=round(account.cash, 8),
                        position_after=account.position,
                    )
                )

            account.mark_to_market(timestamp=tick.timestamp, price=tick.price)

        final_balance = account.equity_curve[-1]["equity"] if account.equity_curve else account.cash
        self.result = SessionResult(
            trades=trades,
            equity_curve=account.equity_curve,
            final_balance=float(final_balance),
        )
        return self.result
