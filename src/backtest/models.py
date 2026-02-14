from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class IntraBarPath(str, Enum):
    OHLC = "ohlc"
    WORST_CASE = "worst_case"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Bar:
    ts: Any
    open: float
    high: float
    low: float
    close: float


@dataclass
class Order:
    side: Side
    qty: float
    order_type: OrderType = OrderType.MARKET
    trigger_price: Optional[float] = None
    tp: Optional[float] = None
    sl: Optional[float] = None
    partial_tp: Optional[float] = None
    partial_qty: Optional[float] = None
    move_be_on_partial: bool = False


@dataclass
class Position:
    trade_id: int
    side: Side
    entry_ts: Any
    entry_price: float
    qty: float
    remaining_qty: float
    tp: Optional[float] = None
    sl: Optional[float] = None
    partial_tp: Optional[float] = None
    partial_qty: Optional[float] = None
    partial_done: bool = False
    be_moved: bool = False
    move_be_on_partial: bool = False


@dataclass
class Trade:
    trade_id: int
    side: Side
    entry_ts: Any
    entry_price: float
    qty: float
    exit_ts: Any | None = None
    exit_price: float | None = None
    reason: str | None = None
    pnl: float = 0.0


@dataclass
class Event:
    ts: Any
    type: str
    trade_id: int
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionConfig:
    path: IntraBarPath = IntraBarPath.OHLC
    slippage: float = 0.0


@dataclass
class Metrics:
    net_pnl: float
    profit_factor: float
    max_drawdown: float
    total_trades: int
    win_rate: float


@dataclass
class BacktestResult:
    equity_curve: list[tuple[Any, float]]
    trades: list[Trade]
    events: list[Event]
    metrics: Metrics
