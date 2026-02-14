from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev

from tradeforge.context import StrategyContext
from tradeforge.models import Signal


@dataclass(frozen=True)
class BBMAOAConfig:
    entry_tf: str = "5m"
    setup_tf: str = "15m"
    bias_tf: str = "1h"
    ema_period: int = 50
    bb_period: int = 20
    bb_dev: float = 2.0
    tp_rr: float = 2.0


def _ema(values: list[float], period: int) -> float:
    if len(values) < period:
        raise ValueError("Not enough values to compute EMA")
    alpha = 2 / (period + 1)
    ema = values[0]
    for value in values[1:]:
        ema = alpha * value + (1 - alpha) * ema
    return ema


def _bollinger(values: list[float], period: int, dev: float) -> tuple[float, float, float]:
    if len(values) < period:
        raise ValueError("Not enough values to compute Bollinger Bands")
    window = values[-period:]
    mid = mean(window)
    sigma = pstdev(window)
    return mid, mid + dev * sigma, mid - dev * sigma


class BBMAOAStrategy:
    def __init__(self, config: BBMAOAConfig | None = None) -> None:
        self.config = config or BBMAOAConfig()

    def evaluate(self, context: StrategyContext) -> Signal | None:
        cfg = self.config
        # Bias from H1 EMA50
        h1_closes = [b.close for b in context.get_series(cfg.bias_tf, cfg.ema_period)]
        h1_ema = _ema(h1_closes, cfg.ema_period)
        h1_close = context.get_bar(cfg.bias_tf).close

        bias: str | None = None
        if h1_close > h1_ema:
            bias = "bullish"
        elif h1_close < h1_ema:
            bias = "bearish"
        else:
            return None

        # Setup extreme from M15 BB touch
        setup_bars = context.get_series(cfg.setup_tf, cfg.bb_period)
        setup_closes = [b.close for b in setup_bars]
        _mid, bb_upper, bb_lower = _bollinger(setup_closes, cfg.bb_period, cfg.bb_dev)
        setup_last = setup_bars[-1]

        touch_upper = setup_last.high >= bb_upper
        touch_lower = setup_last.low <= bb_lower

        # Entry from M5 reentry to EMA50 + momentum candle
        entry_bars = context.get_series(cfg.entry_tf, cfg.ema_period + 1)
        entry_closes = [b.close for b in entry_bars]
        prev_bar = entry_bars[-2]
        last_bar = entry_bars[-1]

        prev_ema = _ema(entry_closes[:-1], cfg.ema_period)
        curr_ema = _ema(entry_closes, cfg.ema_period)

        long_reentry = prev_bar.close <= prev_ema and last_bar.close > curr_ema
        short_reentry = prev_bar.close >= prev_ema and last_bar.close < curr_ema
        bullish_momentum = last_bar.close > last_bar.open
        bearish_momentum = last_bar.close < last_bar.open

        if bias == "bullish" and touch_lower and long_reentry and bullish_momentum:
            entry = last_bar.close
            stop_loss = setup_last.low
            risk = entry - stop_loss
            if risk <= 0:
                return None
            take_profit = entry + cfg.tp_rr * risk
            return Signal("long", entry, stop_loss, take_profit, "H1 bullish + M15 lower BB + M5 EMA50 reentry")

        if bias == "bearish" and touch_upper and short_reentry and bearish_momentum:
            entry = last_bar.close
            stop_loss = setup_last.high
            risk = stop_loss - entry
            if risk <= 0:
                return None
            take_profit = entry - cfg.tp_rr * risk
            return Signal("short", entry, stop_loss, take_profit, "H1 bearish + M15 upper BB + M5 EMA50 reentry")

        return None
