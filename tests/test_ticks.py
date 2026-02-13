from pathlib import Path

from tradeforge.data import compute_file_checksum, load_ticks_csv


def test_ticks_load_in_chronological_order(tmp_path: Path) -> None:
    csv_path = tmp_path / "ticks.csv"
    csv_path.write_text(
        "timestamp_ms,bid,ask\n"
        "1700000001000,1.15,1.25\n"
        "1700000000000,1.10,1.20\n",
        encoding="utf-8",
    )

    ticks = load_ticks_csv(csv_path)

    assert [tick.timestamp_ms for tick in ticks] == [1700000000000, 1700000001000]


def test_checksum_of_known_csv_matches_expected(tmp_path: Path) -> None:
    csv_path = tmp_path / "known.csv"
    csv_path.write_text(
        "timestamp_ms,bid,ask\n"
        "1700000000000,1.1,1.2\n"
        "1700000001000,1.15,1.25\n",
        encoding="utf-8",
    )

    checksum = compute_file_checksum(csv_path)

    assert checksum == "0780a64fefce022b7c7493e4a0984bcc3defba7fa6bf9c7aa9158eb889816771"
