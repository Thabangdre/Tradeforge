from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


def normalize_bars(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize bars into a predictable structure.

    This implementation keeps data lightweight for CLI and test usage.
    """
    normalized: list[dict[str, Any]] = []
    for bar in bars:
        normalized.append(
            {
                "timestamp": bar["timestamp"],
                "open": float(bar["open"]),
                "high": float(bar["high"]),
                "low": float(bar["low"]),
                "close": float(bar["close"]),
            }
        )
    return normalized


def load_bars_csv(path: str, timeframe: str, tz: str = "Africa/Johannesburg", session: str | None = None):
    """Load OHLC bars from CSV and return (bars, load_report)."""
    csv_path = Path(path)
    bars: list[dict[str, Any]] = []
    duplicates_removed = 0
    invalid_fixed = 0

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        seen: set[str] = set()
        for row in reader:
            ts = (row.get("timestamp") or row.get("time") or "").strip()
            if not ts:
                continue
            if ts in seen:
                duplicates_removed += 1
                continue
            seen.add(ts)
            try:
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            bar = {
                "timestamp": ts,
                "open": row.get("open", "0"),
                "high": row.get("high", "0"),
                "low": row.get("low", "0"),
                "close": row.get("close", "0"),
            }
            bars.append(bar)

    bars = normalize_bars(bars)
    start_ts = bars[0]["timestamp"] if bars else None
    end_ts = bars[-1]["timestamp"] if bars else None
    load_report = {
        "timeframe": timeframe,
        "tz": tz,
        "session": session,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "duplicates_removed": duplicates_removed,
        "invalid_fixed": invalid_fixed,
        "gap_count": 0,
        "missing_bars_estimate": 0,
        "bars_filtered_out": 0,
    }
    return bars, load_report
