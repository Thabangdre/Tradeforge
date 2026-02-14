from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    STOP = "STOP"
    MARKET = "MARKET"


class IntraBarPath(str, Enum):
    WORST_CASE = "WORST_CASE"
    OHLC = "OHLC"


class EventType(str, Enum):
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_CANCELED = "ORDER_CANCELED"
    ORDER_FILLED = "ORDER_FILLED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    PARTIAL_TP = "PARTIAL_TP"
    BE_MOVED = "BE_MOVED"
    STOP_HIT = "STOP_HIT"
    TP_HIT = "TP_HIT"


@dataclass(slots=True)
class Bar:
    ts: Any
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


@dataclass(slots=True)
class PendingOrder:
    id: str
    side: Side
    type: OrderType
    price: float | None
    sl: float
    tp: float
    qty: float
    setup_id: str | None = None
    created_ts: Any = None


@dataclass(slots=True)
class Position:
    id: str
    side: Side
    entry: float
    sl: float
    tp: float
    qty: float
    setup_id: str | None = None
    open_ts: Any = None
    partial_taken: bool = False
    be_moved: bool = False
    remaining_qty: float | None = None
    initial_sl: float = field(init=False)

    def __post_init__(self) -> None:
        if self.remaining_qty is None:
            self.remaining_qty = self.qty
        self.initial_sl = self.sl


@dataclass(slots=True)
class Trade:
    id: str
    side: Side
    entry: float
    exit: float
    qty: float
    pnl: float
    open_ts: Any
    close_ts: Any
    reason: str


@dataclass(slots=True)
class Event:
    type: EventType
    ts: Any
    data: dict[str, Any]
