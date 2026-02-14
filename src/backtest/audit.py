from __future__ import annotations


def build_trade_audit(events, trades):
    rows = {}
    for trade in trades:
        rows[trade.trade_id] = {
            "trade_id": trade.trade_id,
            "entry_ts": trade.entry_ts,
            "entry_price": trade.entry_price,
            "partial_ts": None,
            "partial_price": None,
            "partial_qty": None,
            "be_ts": None,
            "be_sl": None,
            "exit_ts": trade.exit_ts,
            "exit_price": trade.exit_price,
            "reason": trade.reason,
        }

    for ev in events:
        row = rows.get(ev.trade_id)
        if not row:
            continue
        if ev.type == "PARTIAL_TP" and row["partial_ts"] is None:
            row["partial_ts"] = ev.ts
            row["partial_price"] = ev.payload.get("price")
            row["partial_qty"] = ev.payload.get("qty")
        elif ev.type == "BE_MOVED" and row["be_ts"] is None:
            row["be_ts"] = ev.ts
            row["be_sl"] = ev.payload.get("new_sl")
        elif ev.type == "POSITION_CLOSED":
            row["exit_ts"] = ev.ts
            row["exit_price"] = ev.payload.get("price")
            row["reason"] = ev.payload.get("reason")

    return [rows[k] for k in sorted(rows)]
