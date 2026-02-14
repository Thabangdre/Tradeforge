from pathlib import Path

from backtest import run_us30_report


class DummyStrategy:
    def generate(self, bars):
        return []


def test_bad_spreads_missing_normal(monkeypatch):
    csv_path = Path("tests/fixtures/us30_sample.csv")
    monkeypatch.setattr(run_us30_report, "make_default_fibsdontlie_strategy", lambda: DummyStrategy())

    rc = run_us30_report.main([
        "--csv",
        str(csv_path),
        "--timeframe",
        "M5",
        "--spreads",
        "tight=0.5,wide=2.0",
    ])

    assert rc != 0


def test_bad_spreads_non_positive(monkeypatch):
    csv_path = Path("tests/fixtures/us30_sample.csv")
    monkeypatch.setattr(run_us30_report, "make_default_fibsdontlie_strategy", lambda: DummyStrategy())

    rc = run_us30_report.main([
        "--csv",
        str(csv_path),
        "--timeframe",
        "M5",
        "--spreads",
        "normal=0",
    ])

    assert rc != 0
