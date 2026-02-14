from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class TradeRecord:
    side: str
    entry_time: int
    entry_price: float
    exit_time: int
    exit_price: float
    volume: float
    pnl: float
    source_id: str | None = None


@dataclass(frozen=True)
class MatchTolerances:
    entry_time_ms: int = 2000
    entry_price: float = 0.0002
    exit_price: float = 0.0002
    pnl: float = 0.01


@dataclass(frozen=True)
class Mismatch:
    tradeforge: TradeRecord
    mt5: TradeRecord
    entry_time_diff_ms: int
    entry_price_diff: float
    exit_price_diff: float
    pnl_diff: float


def _normalize_header(name: str) -> str:
    return "".join(ch for ch in name.lower().strip() if ch.isalnum())


def _to_ms(value: str) -> int:
    text = value.strip()
    if not text:
        raise ValueError("empty timestamp")
    if text.isdigit():
        raw = int(text)
        return raw if raw > 10_000_000_000 else raw * 1000

    text = text.replace(".", "-")
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S.%f",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
    ):
        try:
            return int(datetime.strptime(text, fmt).timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError(f"unsupported timestamp format: {value}")


def _to_float(value: str, *, default: float | None = None) -> float:
    text = value.strip().replace(",", "")
    if text == "":
        if default is None:
            raise ValueError("empty numeric value")
        return default
    return float(text)


def export_trades_csv(trades: Iterable[object], path: str | Path) -> None:
    headers = [
        "id",
        "side",
        "entry_time_ms",
        "entry_price",
        "exit_time_ms",
        "exit_price",
        "sl",
        "tp",
        "volume",
        "pnl",
        "reason",
        "tag",
    ]
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for idx, trade in enumerate(trades):
            writer.writerow(
                {
                    "id": getattr(trade, "id", idx),
                    "side": getattr(trade, "side", ""),
                    "entry_time_ms": getattr(trade, "entry_time_ms", getattr(trade, "entry_time", "")),
                    "entry_price": getattr(trade, "entry_price", ""),
                    "exit_time_ms": getattr(trade, "exit_time_ms", getattr(trade, "exit_time", "")),
                    "exit_price": getattr(trade, "exit_price", ""),
                    "sl": getattr(trade, "sl", ""),
                    "tp": getattr(trade, "tp", ""),
                    "volume": getattr(trade, "volume", ""),
                    "pnl": getattr(trade, "pnl", ""),
                    "reason": getattr(trade, "reason", ""),
                    "tag": getattr(trade, "tag", ""),
                }
            )


def _extract(row: dict[str, str], *candidates: str) -> str:
    for key in candidates:
        if key in row and row[key].strip() != "":
            return row[key]
    return ""


def load_mt5_trades_csv(path: str | Path) -> list[TradeRecord]:
    records: list[TradeRecord] = []
    with Path(path).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        mapped = {_normalize_header(k): k for k in reader.fieldnames}

        for i, raw in enumerate(reader):
            row = {k: (v or "") for k, v in raw.items()}

            side_value = _extract(
                {n: row[o] for n, o in mapped.items() if o in row},
                "side",
                "type",
                "direction",
            ).lower()
            if side_value.startswith("buy"):
                side = "buy"
            elif side_value.startswith("sell"):
                side = "sell"
            else:
                continue

            normalized = {n: row[o] for n, o in mapped.items() if o in row}

            entry_time_raw = _extract(normalized, "entrytimems", "entrytime", "opentime", "time")
            exit_time_raw = _extract(normalized, "exittimems", "exittime", "closetime", "time1")
            entry_price_raw = _extract(normalized, "entryprice", "openprice", "price")
            exit_price_raw = _extract(normalized, "exitprice", "closeprice", "price1")
            volume_raw = _extract(normalized, "volume", "lots")
            pnl_raw = _extract(normalized, "pnl", "profit")
            source_id = _extract(normalized, "id", "ticket", "positionid", "order") or str(i)

            if not all((entry_time_raw, exit_time_raw, entry_price_raw, exit_price_raw, volume_raw, pnl_raw)):
                continue

            try:
                records.append(
                    TradeRecord(
                        side=side,
                        entry_time=_to_ms(entry_time_raw),
                        entry_price=_to_float(entry_price_raw),
                        exit_time=_to_ms(exit_time_raw),
                        exit_price=_to_float(exit_price_raw),
                        volume=_to_float(volume_raw),
                        pnl=_to_float(pnl_raw),
                        source_id=source_id,
                    )
                )
            except ValueError:
                continue
    return records


def _trade_diffs(tf: TradeRecord, mt5: TradeRecord) -> tuple[int, float, float, float]:
    return (
        abs(tf.entry_time - mt5.entry_time),
        abs(tf.entry_price - mt5.entry_price),
        abs(tf.exit_price - mt5.exit_price),
        abs(tf.pnl - mt5.pnl),
    )


def match_trades(
    tradeforge_trades: Iterable[TradeRecord],
    mt5_trades: Iterable[TradeRecord],
    tolerances: MatchTolerances,
) -> dict[str, list]:
    tf_sorted = sorted(list(tradeforge_trades), key=lambda t: (t.entry_time, t.source_id or ""))
    mt5_sorted = sorted(list(mt5_trades), key=lambda t: (t.entry_time, t.source_id or ""))

    used_mt5: set[int] = set()
    matched: list[tuple[TradeRecord, TradeRecord]] = []
    mismatches: list[Mismatch] = []
    unmatched_tf: list[TradeRecord] = []

    for tf in tf_sorted:
        candidates: list[tuple[int, int, float, int]] = []
        for idx, mt5 in enumerate(mt5_sorted):
            if idx in used_mt5 or tf.side != mt5.side:
                continue
            time_diff = abs(tf.entry_time - mt5.entry_time)
            if time_diff > tolerances.entry_time_ms:
                continue
            entry_diff = abs(tf.entry_price - mt5.entry_price)
            candidates.append((time_diff, idx, entry_diff, idx))

        if not candidates:
            unmatched_tf.append(tf)
            continue

        candidates.sort(key=lambda c: (c[0], c[2], c[1]))
        best_idx = candidates[0][1]
        used_mt5.add(best_idx)
        mt5 = mt5_sorted[best_idx]
        matched.append((tf, mt5))

        time_diff, entry_diff, exit_diff, pnl_diff = _trade_diffs(tf, mt5)
        if (
            entry_diff > tolerances.entry_price
            or exit_diff > tolerances.exit_price
            or pnl_diff > tolerances.pnl
        ):
            mismatches.append(
                Mismatch(
                    tradeforge=tf,
                    mt5=mt5,
                    entry_time_diff_ms=time_diff,
                    entry_price_diff=entry_diff,
                    exit_price_diff=exit_diff,
                    pnl_diff=pnl_diff,
                )
            )

    unmatched_mt5 = [t for idx, t in enumerate(mt5_sorted) if idx not in used_mt5]

    return {
        "matched": matched,
        "unmatched_tradeforge": unmatched_tf,
        "unmatched_mt5": unmatched_mt5,
        "mismatches": mismatches,
    }


def parity_report(
    tradeforge_trades: Iterable[TradeRecord],
    mt5_trades: Iterable[TradeRecord],
    tolerances: MatchTolerances,
    mismatch_csv_path: str | Path,
) -> dict[str, float]:
    tf_list = list(tradeforge_trades)
    mt5_list = list(mt5_trades)
    result = match_trades(tf_list, mt5_list, tolerances)
    matched = result["matched"]

    if matched:
        entry_diffs = [abs(tf.entry_price - mt5.entry_price) for tf, mt5 in matched]
        exit_diffs = [abs(tf.exit_price - mt5.exit_price) for tf, mt5 in matched]
        pnl_diff_total = sum(tf.pnl - mt5.pnl for tf, mt5 in matched)
    else:
        entry_diffs = []
        exit_diffs = []
        pnl_diff_total = 0.0

    summary = {
        "match_rate": len(matched) / max(1, len(tf_list)),
        "mean_abs_entry_diff": sum(entry_diffs) / max(1, len(entry_diffs)),
        "mean_abs_exit_diff": sum(exit_diffs) / max(1, len(exit_diffs)),
        "pnl_diff_total": pnl_diff_total,
    }

    mismatch_path = Path(mismatch_csv_path)
    mismatch_path.parent.mkdir(parents=True, exist_ok=True)
    with mismatch_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "tradeforge_id",
                "mt5_id",
                "entry_time_diff_ms",
                "entry_price_diff",
                "exit_price_diff",
                "pnl_diff",
            ],
        )
        writer.writeheader()
        for m in result["mismatches"]:
            writer.writerow(
                {
                    "tradeforge_id": m.tradeforge.source_id or "",
                    "mt5_id": m.mt5.source_id or "",
                    "entry_time_diff_ms": m.entry_time_diff_ms,
                    "entry_price_diff": m.entry_price_diff,
                    "exit_price_diff": m.exit_price_diff,
                    "pnl_diff": m.pnl_diff,
                }
            )

    return summary


def load_tradeforge_trades_csv(path: str | Path) -> list[TradeRecord]:
    rows: list[TradeRecord] = []
    with Path(path).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                rows.append(
                    TradeRecord(
                        side=row["side"].strip().lower(),
                        entry_time=_to_ms(row["entry_time_ms"]),
                        entry_price=_to_float(row["entry_price"]),
                        exit_time=_to_ms(row["exit_time_ms"]),
                        exit_price=_to_float(row["exit_price"]),
                        volume=_to_float(row["volume"]),
                        pnl=_to_float(row["pnl"]),
                        source_id=row.get("id", str(i)),
                    )
                )
            except (KeyError, ValueError):
                continue
    return rows
