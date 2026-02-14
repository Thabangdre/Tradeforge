from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Trade:
    trade_id: str
    side: str
    entry: float
    exit: float
    pnl: float
    reason: str
    open_ts: int
    close_ts: int


@dataclass(frozen=True)
class Event:
    ts: int
    trade_id: str
    type: str
    details: dict


@dataclass(frozen=True)
class BacktestResult:
    trades: list[Trade]
    events: list[Event]
    total_pnl: float
    ending_cash: float
