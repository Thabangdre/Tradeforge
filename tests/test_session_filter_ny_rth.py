from pathlib import Path
from zoneinfo import ZoneInfo

from backtest.data import load_bars_csv


def test_session_filter_ny_rth(tmp_path: Path) -> None:
    csv_path = tmp_path / "session_sample.csv"
    csv_path.write_text(
        "Datetime,Open,High,Low,Close\n"
        "2024-01-03 14:00,1,2,0.5,1.5\n"  # 09:00 NY, out
        "2024-01-03 14:30,1,2,0.5,1.5\n"  # 09:30 NY, in
        "2024-01-03 20:30,1,2,0.5,1.5\n"  # 15:30 NY, in
        "2024-01-03 21:30,1,2,0.5,1.5\n",  # 16:30 NY, out
        encoding="utf-8",
    )

    bars, report = load_bars_csv(str(csv_path), timeframe="M30", tz="UTC", session="NY_RTH")

    assert report["session"] == "NY_RTH"
    assert report["bars_filtered_out"] == 2
    assert len(bars) == 2

    for bar in bars:
        ny = bar.ts.astimezone(ZoneInfo("America/New_York"))
        assert ny.weekday() < 5
        assert (ny.time().hour, ny.time().minute) >= (9, 30)
        assert (ny.time().hour, ny.time().minute) <= (16, 0)
