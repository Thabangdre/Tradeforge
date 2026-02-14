from pathlib import Path

from backtest import run_us30_report


class DummyStrategy:
    def generate(self, bars):
        return []


def test_cli_no_save(tmp_path, monkeypatch):
    csv_path = Path("tests/fixtures/us30_sample.csv")
    monkeypatch.setattr(run_us30_report, "make_default_fibsdontlie_strategy", lambda: DummyStrategy())

    rc = run_us30_report.main([
        "--csv",
        str(csv_path),
        "--timeframe",
        "M5",
        "--outdir",
        str(tmp_path),
        "--no-save",
        "--quiet",
    ])

    assert rc == 0
    assert list(tmp_path.iterdir()) == []
