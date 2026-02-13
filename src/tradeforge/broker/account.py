"""Account and PnL engine for Tradeforge broker simulations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

Side = Literal["BUY", "SELL"]


@dataclass(slots=True)
class Position:
    """Represents an open position."""

    position_id: int
    side: Side
    volume: float
    entry_price: float
    sl: Optional[float] = None
    tp: Optional[float] = None


@dataclass(slots=True)
class ClosedTrade:
    """Represents a closed trade with realized PnL."""

    position_id: int
    side: Side
    volume: float
    entry_price: float
    exit_price: float
    realized_pnl: float


class Account:
    """Tracks account state and calculates floating/realized PnL."""

    def __init__(self, initial_balance: float) -> None:
        self.balance = float(initial_balance)
        self.equity = float(initial_balance)
        self.open_positions: List[Position] = []
        self.closed_trades: List[ClosedTrade] = []
        self.floating_pnl = 0.0
        self.realized_pnl = 0.0
        self._next_position_id = 1
        self._last_bid: Optional[float] = None
        self._last_ask: Optional[float] = None

    def on_order_filled(
        self,
        *,
        side: Side,
        volume: float,
        entry_price: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Position:
        """Create a new position after a broker fill."""
        position = Position(
            position_id=self._next_position_id,
            side=side,
            volume=float(volume),
            entry_price=float(entry_price),
            sl=sl,
            tp=tp,
        )
        self._next_position_id += 1
        self.open_positions.append(position)
        self._refresh_floating_and_equity()
        return position

    def on_price_update(self, *, bid: float, ask: float) -> None:
        """Update market price, close SL/TP hits, and recompute account metrics."""
        self._last_bid = float(bid)
        self._last_ask = float(ask)
        self._close_triggered_positions()
        self._refresh_floating_and_equity()

    def _close_triggered_positions(self) -> None:
        if self._last_bid is None or self._last_ask is None:
            return

        survivors: List[Position] = []
        for position in self.open_positions:
            exit_price: Optional[float] = None

            if position.side == "BUY":
                if position.sl is not None and self._last_bid <= position.sl:
                    exit_price = position.sl
                elif position.tp is not None and self._last_bid >= position.tp:
                    exit_price = position.tp
            else:  # SELL
                if position.sl is not None and self._last_ask >= position.sl:
                    exit_price = position.sl
                elif position.tp is not None and self._last_ask <= position.tp:
                    exit_price = position.tp

            if exit_price is None:
                survivors.append(position)
                continue

            realized = self._position_realized_pnl(position, exit_price)
            self.realized_pnl += realized
            self.balance += realized
            self.closed_trades.append(
                ClosedTrade(
                    position_id=position.position_id,
                    side=position.side,
                    volume=position.volume,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    realized_pnl=realized,
                )
            )

        self.open_positions = survivors

    def _position_floating_pnl(self, position: Position) -> float:
        if self._last_bid is None or self._last_ask is None:
            return 0.0

        if position.side == "BUY":
            return (self._last_bid - position.entry_price) * position.volume
        return (position.entry_price - self._last_ask) * position.volume

    @staticmethod
    def _position_realized_pnl(position: Position, exit_price: float) -> float:
        if position.side == "BUY":
            return (exit_price - position.entry_price) * position.volume
        return (position.entry_price - exit_price) * position.volume

    def _refresh_floating_and_equity(self) -> None:
        self.floating_pnl = sum(self._position_floating_pnl(p) for p in self.open_positions)
        self.equity = self.balance + self.floating_pnl
