from dataclasses import dataclass
from typing import Dict, List

from .fills import Fill
from .orders import Order
from .rules import is_sl_triggered, is_tp_triggered, market_fill_price, trigger_price


@dataclass
class _OrderState:
    order: Order
    opened: bool = False


class BrokerSimulator:
    def __init__(self) -> None:
        self._states: Dict[str, _OrderState] = {}
        self.fills: List[Fill] = []

    def submit_order(self, order: Order) -> None:
        if order.id in self._states:
            raise ValueError(f"Duplicate order id: {order.id}")
        self._states[order.id] = _OrderState(order=order)

    def process_tick(self, timestamp_ms: int, bid: float, ask: float) -> List[Fill]:
        generated: List[Fill] = []

        for order_id in sorted(self._states.keys()):
            state = self._states.get(order_id)
            if state is None:
                continue
            order = state.order

            if not state.opened:
                if order.type.upper() != "MARKET":
                    continue
                fill = Fill(
                    order_id=order.id,
                    price=market_fill_price(order.side, bid, ask),
                    timestamp_ms=timestamp_ms,
                    reason="market",
                )
                generated.append(fill)
                state.opened = True
                continue

            if is_sl_triggered(order, bid, ask):
                fill = Fill(
                    order_id=order.id,
                    price=trigger_price(order.side, bid, ask),
                    timestamp_ms=timestamp_ms,
                    reason="sl",
                )
                generated.append(fill)
                del self._states[order.id]
                continue

            if is_tp_triggered(order, bid, ask):
                fill = Fill(
                    order_id=order.id,
                    price=trigger_price(order.side, bid, ask),
                    timestamp_ms=timestamp_ms,
                    reason="tp",
                )
                generated.append(fill)
                del self._states[order.id]

        self.fills.extend(generated)
        return generated
