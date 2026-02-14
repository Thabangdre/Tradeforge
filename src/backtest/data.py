from __future__ import annotations

import csv
from dataclasses import replace
from datetime import datetime, time, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from backtest.models import Bar

_TIMEFRAME_DELTAS = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "M30": timedelta(minutes=30),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
}

_DATETIME_FORMATS = (
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


def _normalize_header(name: str) -> str:
    return "".join(name.lower().split())


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    txt = value.strip()
    if not txt:
        return None
    return float(txt)


def _parse_dt(value: str, tz_name: str) -> datetime:
    txt = value.strip()
    for fmt in _DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(txt, fmt)
            return parsed.replace(tzinfo=ZoneInfo(tz_name))
        except ValueError:
            continue
    parsed = datetime.fromisoformat(txt)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo(tz_name))
    return parsed


def _timeframe_delta(timeframe: str) -> timedelta:
    try:
        return _TIMEFRAME_DELTAS[timeframe.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported timeframe: {timeframe}") from exc


def _session_keep(bar: Bar, session: str | None) -> bool:
    if session is None:
        return True

    ny = bar.ts.astimezone(ZoneInfo("America/New_York"))
    if ny.weekday() >= 5:
        return False

    current_t = ny.time()
    if session == "NY_RTH":
        return time(9, 30) <= current_t <= time(16, 0)
    if session == "NY":
        return time(0, 0) <= current_t <= time(23, 59, 59)
    raise ValueError(f"Unsupported session: {session}")


def normalize_bars(
    bars: Iterable[Bar],
    timeframe: str,
    *,
    strict: bool = False,
) -> tuple[list[Bar], dict[str, Any]]:
    bars_list = list(bars)
    bars_in = len(bars_list)

    last_by_ts: dict[datetime, Bar] = {}
    for bar in bars_list:
        last_by_ts[bar.ts] = bar

    deduped = [last_by_ts[ts] for ts in sorted(last_by_ts)]
    duplicates_removed = bars_in - len(deduped)

    invalid_fixed = 0
    cleaned: list[Bar] = []
    for bar in deduped:
        expected_high = max(bar.open, bar.close)
        expected_low = min(bar.open, bar.close)
        valid = bar.high >= expected_high and bar.low <= expected_low
        if valid:
            cleaned.append(bar)
            continue

        if strict:
            raise ValueError(f"Invalid OHLC at {bar.ts.isoformat()}")

        fixed_high = max(bar.high, bar.open, bar.close)
        fixed_low = min(bar.low, bar.open, bar.close)
        cleaned.append(replace(bar, high=fixed_high, low=fixed_low))
        invalid_fixed += 1

    expected_delta = _timeframe_delta(timeframe)
    gap_count = 0
    missing_bars_estimate = 0
    max_gap = timedelta(0)

    for current, nxt in zip(cleaned, cleaned[1:]):
        gap = nxt.ts - current.ts
        if gap > expected_delta:
            gap_count += 1
            if gap > max_gap:
                max_gap = gap
            missing = int(round(gap / expected_delta)) - 1
            if missing > 0:
                missing_bars_estimate += missing

    report: dict[str, Any] = {
        "bars_in": bars_in,
        "bars_out": len(cleaned),
        "duplicates_removed": duplicates_removed,
        "invalid_fixed": invalid_fixed,
        "gap_count": gap_count,
        "max_gap": max_gap,
        "missing_bars_estimate": missing_bars_estimate,
        "start_ts": cleaned[0].ts if cleaned else None,
        "end_ts": cleaned[-1].ts if cleaned else None,
    }
    return cleaned, report


def load_bars_csv(
    path: str,
    timeframe: str,
    tz: str = "Africa/Johannesburg",
    *,
    session: str | None = None,
    strict: bool = False,
) -> tuple[list[Bar], dict[str, Any]]:
    bars: list[Bar] = []

    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")

        field_map = {_normalize_header(field): field for field in reader.fieldnames}

        date_col = field_map.get("date")
        time_col = field_map.get("time")
        dt_col = (
            field_map.get("datetime")
            or field_map.get("timestamp")
            or field_map.get("ts")
        )

        open_col = field_map.get("open") or field_map.get("o")
        high_col = field_map.get("high") or field_map.get("h")
        low_col = field_map.get("low") or field_map.get("l")
        close_col = field_map.get("close") or field_map.get("c")
        volume_col = (
            field_map.get("tickvolume")
            or field_map.get("volume")
            or field_map.get("v")
        )

        required = [open_col, high_col, low_col, close_col]
        if not all(required):
            raise ValueError("Missing OHLC columns")
        if not dt_col and not (date_col and time_col):
            raise ValueError("Missing datetime information")

        for row in reader:
            dt_text = row[dt_col] if dt_col else f"{row[date_col]} {row[time_col]}"
            ts = _parse_dt(dt_text, tz)

            bar = Bar(
                ts=ts,
                open=float(row[open_col]),
                high=float(row[high_col]),
                low=float(row[low_col]),
                close=float(row[close_col]),
                volume=_parse_float(row.get(volume_col)) if volume_col else None,
            )
            bars.append(bar)

    normalized, report = normalize_bars(bars, timeframe, strict=strict)

    before_session = len(normalized)
    filtered = [bar for bar in normalized if _session_keep(bar, session)]
    report["session"] = session
    report["bars_filtered_out"] = before_session - len(filtered)
    report["bars_out"] = len(filtered)
    report["start_ts"] = filtered[0].ts if filtered else None
    report["end_ts"] = filtered[-1].ts if filtered else None

    return filtered, report
