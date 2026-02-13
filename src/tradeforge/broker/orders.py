from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Order:
    id: str
    type: str
    side: str
    price: Optional[float]
    sl: Optional[float]
    tp: Optional[float]
    volume: float
