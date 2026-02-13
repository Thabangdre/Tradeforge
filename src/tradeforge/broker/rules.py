from .orders import Order


def market_fill_price(side: str, bid: float, ask: float) -> float:
    normalized = side.upper()
    if normalized == "BUY":
        return ask
    if normalized == "SELL":
        return bid
    raise ValueError(f"Unsupported side: {side}")


def trigger_price(side: str, bid: float, ask: float) -> float:
    normalized = side.upper()
    if normalized == "BUY":
        return bid
    if normalized == "SELL":
        return ask
    raise ValueError(f"Unsupported side: {side}")


def is_sl_triggered(order: Order, bid: float, ask: float) -> bool:
    if order.sl is None:
        return False
    normalized = order.side.upper()
    if normalized == "BUY":
        return bid <= order.sl
    if normalized == "SELL":
        return ask >= order.sl
    raise ValueError(f"Unsupported side: {order.side}")


def is_tp_triggered(order: Order, bid: float, ask: float) -> bool:
    if order.tp is None:
        return False
    normalized = order.side.upper()
    if normalized == "BUY":
        return bid >= order.tp
    if normalized == "SELL":
        return ask <= order.tp
    raise ValueError(f"Unsupported side: {order.side}")
