from __future__ import annotations

import argparse

from tradeforge.validate.mt5_parity import (
    MatchTolerances,
    load_mt5_trades_csv,
    load_tradeforge_trades_csv,
    parity_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tradeforge")
    sub = parser.add_subparsers(dest="command", required=True)

    parity = sub.add_parser("parity", help="Generate MT5 parity report")
    parity.add_argument("--tradeforge", required=True, help="Path to Tradeforge trade CSV")
    parity.add_argument("--mt5", required=True, help="Path to MT5 trade history CSV")
    parity.add_argument("--out", required=True, help="Output mismatch report CSV")
    parity.add_argument("--entry-time-ms", type=int, default=2000)
    parity.add_argument("--entry-price", type=float, default=0.0002)
    parity.add_argument("--exit-price", type=float, default=0.0002)
    parity.add_argument("--pnl", type=float, default=0.01)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "parity":
        tf_trades = load_tradeforge_trades_csv(args.tradeforge)
        mt5_trades = load_mt5_trades_csv(args.mt5)
        summary = parity_report(
            tf_trades,
            mt5_trades,
            MatchTolerances(
                entry_time_ms=args.entry_time_ms,
                entry_price=args.entry_price,
                exit_price=args.exit_price,
                pnl=args.pnl,
            ),
            args.out,
        )
        print(summary)
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
