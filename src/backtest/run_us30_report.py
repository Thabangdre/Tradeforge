from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backtest.data import load_bars_csv
from backtest.report import build_research_report, format_research_report
from importlib import import_module

from backtest.strategy_stub import MissingStrategyError, make_default_fibsdontlie_strategy as make_stub_strategy


def _now(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))


def make_default_fibsdontlie_strategy():
    candidates = [
        ("strategies.fibsdontlie", ["FibsDontLie", "FibsDontLieStrategy"]),
        ("src.strategies.fibsdontlie", ["FibsDontLie", "FibsDontLieStrategy"]),
    ]
    for module_name, class_names in candidates:
        try:
            module = import_module(module_name)
        except Exception:
            continue
        for class_name in class_names:
            cls = getattr(module, class_name, None)
            if cls is not None:
                return cls()
    return make_stub_strategy()


def _parse_spreads(raw: str) -> dict[str, float]:
    spreads: dict[str, float] = {}
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"Invalid spread item '{chunk}', expected name=value")
        name, value = chunk.split("=", 1)
        name = name.strip()
        value = value.strip()
        spread = float(value)
        if spread <= 0:
            raise ValueError(f"Spread '{name}' must be > 0")
        spreads[name] = spread
    if "normal" not in spreads:
        raise ValueError("Spreads must include at least 'normal'")
    return spreads


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run US30 backtest research report")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--symbol", default="US30")
    parser.add_argument("--tz", default="Africa/Johannesburg")
    parser.add_argument("--session", choices=["NY_RTH", "NY"], default=None)
    parser.add_argument("--spreads", default="tight=0.5,normal=1.0,wide=2.0")
    parser.add_argument("--path", choices=["worst", "ohlc"], default="worst")
    parser.add_argument("--initial-cash", type=float, default=0.0)
    parser.add_argument("--top-losses", type=int, default=10)
    parser.add_argument("--outdir", default="reports")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        spreads = _parse_spreads(args.spreads)
    except Exception as exc:
        print(f"Error: invalid --spreads: {exc}")
        return 2

    try:
        strategy = make_default_fibsdontlie_strategy()
    except MissingStrategyError as exc:
        print(f"Error: {exc}")
        return 2

    try:
        bars, load_report = load_bars_csv(args.csv, args.timeframe, tz=args.tz, session=args.session)
    except Exception as exc:
        print(f"Error: failed to load CSV: {exc}")
        return 2

    if not bars:
        print("Error: no bars loaded from CSV")
        return 2

    if not args.quiet:
        print("Data quality summary")
        print(f"bars={len(bars)}")
        print(f"start={load_report.get('start_ts')}")
        print(f"end={load_report.get('end_ts')}")
        print(f"duplicates_removed={load_report.get('duplicates_removed', 0)}")
        print(f"invalid_fixed={load_report.get('invalid_fixed', 0)}")
        print(f"gap_count={load_report.get('gap_count', 0)}")
        print(f"missing_bars_estimate={load_report.get('missing_bars_estimate', 0)}")
        print(f"bars_filtered_out={load_report.get('bars_filtered_out', 0)}")

    report = build_research_report(
        bars=bars,
        strategy=strategy,
        symbol=args.symbol,
        exec_config={"path_preference": args.path, "headline": "WORST_CASE"},
        spreads=spreads,
        initial_cash=args.initial_cash,
        top_n_losses=args.top_losses,
    )

    report_text = format_research_report(report)
    if not args.quiet:
        print(report_text)

    if not args.no_save:
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        timestamp = _now(args.tz).strftime("%Y%m%d_%H%M")
        file_name = f"{args.symbol}_{args.timeframe}_{timestamp}.json"
        out_path = outdir / file_name
        out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        if not args.quiet:
            print(f"Saved report: {out_path}")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
