from __future__ import annotations

import csv
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Union


@dataclass(frozen=True)
class Tick:
    timestamp_ms: int
    bid: float
    ask: float


@dataclass(frozen=True)
class TickCsvData:
    ticks: list[Tick]
    checksum: str


def _checksum_for_ticks(ticks: Iterable[Tick]) -> str:
    hasher = hashlib.sha256()
    for tick in ticks:
        hasher.update(struct.pack("<qdd", tick.timestamp_ms, tick.bid, tick.ask))
    return hasher.hexdigest()


def load_ticks_csv(path: Union[str, Path]) -> TickCsvData:
    """Load ticks from CSV with strict schema and ordering checks.

    Expected columns (in this exact order): timestamp_ms,bid,ask
    """

    csv_path = Path(path)
    ticks: list[Tick] = []

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("CSV is empty") from exc

        expected_header = ["timestamp_ms", "bid", "ask"]
        if header != expected_header:
            raise ValueError(
                f"Invalid CSV header order. Expected {expected_header}, got {header}"
            )

        previous_ts: int | None = None
        for line_no, row in enumerate(reader, start=2):
            if len(row) != 3:
                raise ValueError(f"Line {line_no}: expected 3 columns, got {len(row)}")

            raw_ts, raw_bid, raw_ask = row
            try:
                timestamp_ms = int(raw_ts)
            except ValueError as exc:
                raise ValueError(
                    f"Line {line_no}: timestamp_ms must be an integer, got {raw_ts!r}"
                ) from exc

            try:
                bid = float(raw_bid)
                ask = float(raw_ask)
            except ValueError as exc:
                raise ValueError(
                    f"Line {line_no}: bid/ask must be float-compatible values"
                ) from exc

            if previous_ts is not None and timestamp_ms <= previous_ts:
                raise ValueError(
                    f"Line {line_no}: timestamp_ms must be strictly increasing "
                    f"({timestamp_ms} <= {previous_ts})"
                )
            previous_ts = timestamp_ms

            ticks.append(Tick(timestamp_ms=timestamp_ms, bid=bid, ask=ask))

    return TickCsvData(ticks=ticks, checksum=_checksum_for_ticks(ticks))
