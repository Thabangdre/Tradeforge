from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backtest.data import normalize_bars
from backtest.models import Bar


def test_strict_mode_raises_on_invalid_ohlc() -> None:
    bars = [
        Bar(
            ts=datetime(2024, 1, 1, 10, 0, tzinfo=ZoneInfo("UTC")),
            open=10.0,
            high=9.0,
            low=11.0,
            close=10.5,
            volume=100,
        )
    ]

    with pytest.raises(ValueError):
        normalize_bars(bars, timeframe="M5", strict=True)
