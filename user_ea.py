from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass
class Trade:
    side: str
    entry: float
    sl: float
    tp: float
    opened_at: int
    closed_at: Optional[int] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None


@dataclass
class UserEAState:
    swing_high: Optional[Tuple[int, float]] = None
    swing_low: Optional[Tuple[int, float]] = None
    last_swing_direction: Optional[str] = None
    structure_break: Optional[str] = None
    fib_levels: Dict[float, float] = field(default_factory=dict)
    fib_anchors: Optional[Tuple[Tuple[int, float], Tuple[int, float]]] = None


class UserEA:
    """Deterministic Fibonacci/structure-based EA.

    Uses confirmed 3-point pivots to avoid repainting. Anchors are fixed once
    a bullish swing is confirmed and remain fixed while evaluating entry/exit.
    """

    def __init__(self, config: Dict[str, float]):
        self.config = {
            "fib_low": 0.618,
            "fib_high": 0.786,
            "sl_buffer": 0.0,
            "tp_rr": 1.5,
        }
        self.config.update(config)

        self.state = UserEAState()
        self._prices: List[float] = []
        self.active_trade: Optional[Trade] = None
        self.trades: List[Trade] = []
        self.events: List[Dict[str, Any]] = []

    def _price_of(self, tick: Any) -> float:
        if isinstance(tick, (float, int)):
            return float(tick)
        if isinstance(tick, dict):
            for key in ("price", "close", "mid"):
                if key in tick:
                    return float(tick[key])
        raise ValueError(f"Unsupported tick format: {tick!r}")

    def _confirm_pivot(self, idx: int) -> None:
        # Pivot at idx-1 gets confirmed only when idx exists -> no repainting.
        if idx < 2:
            return

        a, b, c = self._prices[idx - 2], self._prices[idx - 1], self._prices[idx]
        pivot_idx = idx - 1

        if b > a and b > c:
            self.state.swing_high = (pivot_idx, b)
            self.state.last_swing_direction = "down"
        elif b < a and b < c:
            self.state.swing_low = (pivot_idx, b)
            self.state.last_swing_direction = "up"

        # Detect structure break using latest confirmed swing points.
        if self.state.swing_high and c > self.state.swing_high[1]:
            self.state.structure_break = "bullish"
        elif self.state.swing_low and c < self.state.swing_low[1]:
            self.state.structure_break = "bearish"

        self._refresh_bullish_swing()

    def _refresh_bullish_swing(self) -> None:
        # Bullish swing: latest confirmed low comes before latest confirmed high.
        low = self.state.swing_low
        high = self.state.swing_high
        if not low or not high:
            return
        if low[0] >= high[0]:
            return

        if self.active_trade is not None:
            # Fixed anchors while managing an active trade.
            return

        self.state.fib_anchors = (low, high)
        self.state.fib_levels = self._fib_from_anchors(low_price=low[1], high_price=high[1])

    def _fib_from_anchors(self, low_price: float, high_price: float) -> Dict[float, float]:
        move = high_price - low_price
        if move <= 0:
            return {}

        levels = {}
        for ratio in (0.5, 0.618, 0.786):
            levels[ratio] = high_price - move * ratio
        return levels

    def _try_entry(self, idx: int, price: float) -> None:
        if self.active_trade is not None:
            return
        if not self.state.fib_anchors:
            return

        low_anchor, high_anchor = self.state.fib_anchors
        swing_low = low_anchor[1]
        structure_high = high_anchor[1]

        fib_low = float(self.config["fib_low"])
        fib_high = float(self.config["fib_high"])

        # Normalize zone ordering by price.
        zone_a = self.state.fib_levels.get(fib_low)
        zone_b = self.state.fib_levels.get(fib_high)
        if zone_a is None or zone_b is None:
            # allow any values by interpolating.
            move = structure_high - swing_low
            zone_a = structure_high - move * fib_low
            zone_b = structure_high - move * fib_high

        zone_min, zone_max = sorted((zone_a, zone_b))
        if not (zone_min <= price <= zone_max):
            return

        sl = swing_low - float(self.config["sl_buffer"])
        tp = structure_high
        if tp <= price:
            risk = max(price - sl, 0.0)
            tp = price + risk * float(self.config["tp_rr"])

        trade = Trade(side="buy", entry=price, sl=sl, tp=tp, opened_at=idx)
        self.active_trade = trade
        self.trades.append(trade)
        self.events.append({"type": "entry", "index": idx, "price": price})

    def _try_exit(self, idx: int, price: float) -> None:
        if self.active_trade is None:
            return
        trade = self.active_trade
        # Deterministic priority: stop-loss first, then take-profit.
        if price <= trade.sl:
            trade.closed_at = idx
            trade.exit_price = price
            trade.exit_reason = "sl"
            self.events.append({"type": "exit", "reason": "sl", "index": idx, "price": price})
            self.active_trade = None
            return
        if price >= trade.tp:
            trade.closed_at = idx
            trade.exit_price = price
            trade.exit_reason = "tp"
            self.events.append({"type": "exit", "reason": "tp", "index": idx, "price": price})
            self.active_trade = None
            return

    def on_tick(self, tick: Any, idx: int) -> None:
        price = self._price_of(tick)
        self._prices.append(price)

        self._confirm_pivot(idx)
        self._try_exit(idx, price)
        self._try_entry(idx, price)

    def run(self, ticks: Sequence[Any]) -> Dict[str, Any]:
        for idx, tick in enumerate(ticks):
            self.on_tick(tick, idx)

        return {
            "trades": [trade.__dict__.copy() for trade in self.trades],
            "events": list(self.events),
            "state": {
                "swing_high": self.state.swing_high,
                "swing_low": self.state.swing_low,
                "last_swing_direction": self.state.last_swing_direction,
                "structure_break": self.state.structure_break,
                "fib_levels": dict(self.state.fib_levels),
                "fib_anchors": self.state.fib_anchors,
            },
        }


def run_fibo_ea(config: Dict[str, float], ticks: Sequence[Any]) -> Dict[str, Any]:
    return UserEA(config).run(ticks)
