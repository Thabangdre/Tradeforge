from dataclasses import dataclass


@dataclass(frozen=True)
class Tick:
    index: int
    price: float


@dataclass(frozen=True)
class Trade:
    side: str
    qty: float
    price: float
    tick_index: int
