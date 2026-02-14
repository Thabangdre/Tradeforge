from backtest import run_us30_report


class DummyStrategy:
    def generate(self, bars):
        return []


def test_empty_bars_returns_2(tmp_path, monkeypatch):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("timestamp,open,high,low,close\n", encoding="utf-8")

    monkeypatch.setattr(run_us30_report, "make_default_fibsdontlie_strategy", lambda: DummyStrategy())

    rc = run_us30_report.main([
        "--csv",
        str(empty_csv),
        "--timeframe",
        "M5",
    ])

    assert rc == 2
