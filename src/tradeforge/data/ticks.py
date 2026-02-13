"""Tick schema and CSV loading utilities."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

EXPECTED_TICK_COLUMNS = ["timestamp_ms", "bid", "ask"]


@dataclass(frozen=True, slots=True)
class Tick:
    """Single market tick."""

    timestamp_ms: int
    bid: float
    ask: float


def load_ticks_csv(path: str | Path) -> list[Tick]:
    """Load ticks from CSV and return them in chronological order.

    CSV must include exactly these columns and order:
    timestamp_ms,bid,ask
    """

    csv_path = Path(path)

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            raise ValueError("CSV file is empty")
        if header != EXPECTED_TICK_COLUMNS:
            raise ValueError(
                f"CSV columns must be exactly {','.join(EXPECTED_TICK_COLUMNS)}"
            )

        ticks: list[Tick] = []
        for line_number, row in enumerate(reader, start=2):
            if len(row) != 3:
                raise ValueError(f"Invalid row length at line {line_number}: {row}")
            try:
                tick = Tick(
                    timestamp_ms=int(row[0]),
                    bid=float(row[1]),
                    ask=float(row[2]),
                )
            except ValueError as exc:
                raise ValueError(f"Invalid data at line {line_number}: {row}") from exc
            ticks.append(tick)

    return sorted(ticks, key=lambda tick: tick.timestamp_ms)


def compute_file_checksum(path: str | Path, algorithm: str = "sha256") -> str:
    """Compute a deterministic checksum for a data file."""

    file_path = Path(path)
    hasher = hashlib.new(algorithm)

    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)

    return hasher.hexdigest()
