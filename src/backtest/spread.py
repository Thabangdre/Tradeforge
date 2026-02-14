from __future__ import annotations


class FixedSpreadModel:
    def __init__(self, spread: float):
        self.spread = spread

    def get_spread(self, symbol: str, ts) -> float:
        return self.spread


def bid_ask_from_mid(mid: float, spread: float) -> tuple[float, float]:
    half = spread / 2.0
    return mid - half, mid + half
