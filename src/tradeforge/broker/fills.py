from dataclasses import dataclass


@dataclass(frozen=True)
class Fill:
    order_id: str
    price: float
    timestamp_ms: int
    reason: str
