from __future__ import annotations

from tradeforge.context import StrategyContext
from tradeforge.models import Bar
from tradeforge.session import SessionRunner
from tradeforge.strategies.bbma_oa import BBMAOAStrategy


def _fill_context(
    h1_closes: list[float],
    m15_closes: list[float],
    m15_last_high: float,
    m15_last_low: float,
    m5_closes: list[float],
    m5_last_open: float,
    m5_prev_open: float,
) -> StrategyContext:
    ctx = StrategyContext()

    for i, close in enumerate(h1_closes):
        ctx.update_bar(Bar(i, close, close + 1, close - 1, close, "1h"))

    for i, close in enumerate(m15_closes):
        high = close + 1
        low = close - 1
        if i == len(m15_closes) - 1:
            high = m15_last_high
            low = m15_last_low
        ctx.update_bar(Bar(i, close, high, low, close, "15m"))

    for i, close in enumerate(m5_closes):
        open_ = close
        if i == len(m5_closes) - 2:
            open_ = m5_prev_open
        elif i == len(m5_closes) - 1:
            open_ = m5_last_open
        high = max(open_, close) + 0.5
        low = min(open_, close) - 0.5
        ctx.update_bar(Bar(i, open_, high, low, close, "5m"))

    return ctx


def test_bullish_sequence_triggers_long() -> None:
    ctx = _fill_context(
        h1_closes=[100 + i for i in range(50)],
        m15_closes=[100.0] * 20,
        m15_last_high=101.0,
        m15_last_low=50.0,
        m5_closes=[100.0] * 49 + [95.0, 105.0],
        m5_last_open=96.0,
        m5_prev_open=96.0,
    )

    signal = BBMAOAStrategy().evaluate(ctx)

    assert signal is not None
    assert signal.side == "long"
    assert signal.stop_loss == 50.0
    assert signal.take_profit > signal.entry


def test_bearish_sequence_triggers_short() -> None:
    ctx = _fill_context(
        h1_closes=[150 - i for i in range(50)],
        m15_closes=[100.0] * 20,
        m15_last_high=150.0,
        m15_last_low=99.0,
        m5_closes=[100.0] * 49 + [105.0, 95.0],
        m5_last_open=104.0,
        m5_prev_open=104.0,
    )

    signal = BBMAOAStrategy().evaluate(ctx)

    assert signal is not None
    assert signal.side == "short"
    assert signal.stop_loss == 150.0
    assert signal.take_profit < signal.entry


def test_bias_filter_blocks_opposite_trades() -> None:
    # Bullish H1 bias, but short setup/entry should be blocked.
    ctx = _fill_context(
        h1_closes=[100 + i for i in range(50)],
        m15_closes=[100.0] * 20,
        m15_last_high=150.0,
        m15_last_low=99.0,
        m5_closes=[100.0] * 49 + [105.0, 95.0],
        m5_last_open=104.0,
        m5_prev_open=104.0,
    )

    signal = BBMAOAStrategy().evaluate(ctx)
    assert signal is None


def test_deterministic_results() -> None:
    ctx = _fill_context(
        h1_closes=[100 + i for i in range(50)],
        m15_closes=[100.0] * 20,
        m15_last_high=101.0,
        m15_last_low=50.0,
        m5_closes=[100.0] * 49 + [95.0, 105.0],
        m5_last_open=96.0,
        m5_prev_open=96.0,
    )
    strategy = BBMAOAStrategy()

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first == second


def test_session_runner_aggregates_timeframes() -> None:
    runner = SessionRunner()
    for i in range(60):
        price = 100 + i
        runner.on_one_minute_ohlc(i, price, price + 1, price - 1, price)

    assert runner.context.get_bar("1m").timeframe == "1m"
    assert runner.context.get_bar("5m").timeframe == "5m"
    assert runner.context.get_bar("15m").timeframe == "15m"
    assert runner.context.get_bar("1h").timeframe == "1h"
