import json
from datetime import datetime
from pathlib import Path

from backtest import run_us30_report


class DummyStrategy:
    def generate(self, bars):
        return []


def test_cli_saves_json(tmp_path, monkeypatch):
    csv_path = Path("tests/fixtures/us30_sample.csv")

    monkeypatch.setattr(run_us30_report, "make_default_fibsdontlie_strategy", lambda: DummyStrategy())
    monkeypatch.setattr(
        run_us30_report,
        "_now",
        lambda tz: datetime(2026, 2, 14, 19, 0),
    )

    rc = run_us30_report.main([
        "--csv",
        str(csv_path),
        "--timeframe",
        "M5",
        "--outdir",
        str(tmp_path),
        "--quiet",
    ])

    assert rc == 0
    expected = tmp_path / "US30_M5_20260214_1900.json"
    assert expected.exists()

    payload = json.loads(expected.read_text(encoding="utf-8"))
    assert "headline" in payload
    assert "diagnostic" in payload
    assert "fragility" in payload
    assert "spread_stress" in payload
    assert "fill_flip" in payload
    assert "worst_trades" in payload
