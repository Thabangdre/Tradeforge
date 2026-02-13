from __future__ import annotations

import pytest

from tradeforge.csv_ticks import load_ticks_csv


def test_load_ticks_csv_parses_rows_and_checksum(tmp_path):
    csv_file = tmp_path / "ticks.csv"
    csv_file.write_text(
        "timestamp_ms,bid,ask\n"
        "1000,1.1000,1.1002\n"
        "1001,1.1001,1.1003\n",
        encoding="utf-8",
    )

    result = load_ticks_csv(csv_file)

    assert [t.timestamp_ms for t in result.ticks] == [1000, 1001]
    assert [t.bid for t in result.ticks] == [1.1, 1.1001]
    assert [t.ask for t in result.ticks] == [1.1002, 1.1003]
    assert len(result.checksum) == 64

    # Deterministic checksum across loads.
    result_again = load_ticks_csv(csv_file)
    assert result_again.checksum == result.checksum


def test_load_ticks_csv_validates_column_order(tmp_path):
    csv_file = tmp_path / "ticks_bad_header.csv"
    csv_file.write_text(
        "timestamp_ms,ask,bid\n"
        "1000,1.1002,1.1000\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid CSV header order"):
        load_ticks_csv(csv_file)


def test_load_ticks_csv_validates_monotonic_timestamps(tmp_path):
    csv_file = tmp_path / "ticks_bad_order.csv"
    csv_file.write_text(
        "timestamp_ms,bid,ask\n"
        "1000,1.1000,1.1002\n"
        "1000,1.1001,1.1003\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="strictly increasing"):
        load_ticks_csv(csv_file)
