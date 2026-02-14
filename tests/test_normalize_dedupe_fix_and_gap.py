from datetime import datetime
from zoneinfo import ZoneInfo

from backtest.data import normalize_bars
from backtest.models import Bar


def test_normalize_dedupe_fix_gap() -> None:
    tz = ZoneInfo("Africa/Johannesburg")
    bars = [
        Bar(datetime(2024, 1, 2, 9, 0, tzinfo=tz), 1.0, 1.2, 0.9, 1.1, 10),
        Bar(datetime(2024, 1, 2, 9, 5, tzinfo=tz), 1.1, 1.3, 1.0, 1.2, 11),
        Bar(datetime(2024, 1, 2, 9, 5, tzinfo=tz), 1.1, 1.31, 1.0, 1.21, 12),
        Bar(datetime(2024, 1, 2, 9, 15, tzinfo=tz), 1.21, 1.15, 1.25, 1.2, 13),
    ]

    normalized, report = normalize_bars(bars, timeframe="M5", strict=False)

    assert len(normalized) == 3
    assert report["duplicates_removed"] == 1
    assert report["invalid_fixed"] > 0
    assert report["gap_count"] == 1
    assert report["missing_bars_estimate"] == 1
