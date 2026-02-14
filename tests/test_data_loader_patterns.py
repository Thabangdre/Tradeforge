from pathlib import Path

from backtest.data import load_bars_csv


def test_load_fixture_and_report_shape() -> None:
    fixture = Path("tests/fixtures/us30_m5_sample.csv")
    bars, report = load_bars_csv(str(fixture), timeframe="M5")

    assert isinstance(bars, list)
    assert len(bars) > 0

    required = {
        "bars_in",
        "bars_out",
        "duplicates_removed",
        "invalid_fixed",
        "gap_count",
        "missing_bars_estimate",
        "start_ts",
        "end_ts",
        "session",
        "bars_filtered_out",
    }
    assert required.issubset(report)

    assert all(bar.ts.tzinfo is not None for bar in bars)
    assert bars == sorted(bars, key=lambda b: b.ts)
