from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tradeforge.runner import run_fibo_on_csv


def main(path: str | Path, config: dict[str, Any]) -> Any:
    return run_fibo_on_csv(path, config)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Fibonacci EA with CSV ticks")
    parser.add_argument("path", help="Path to CSV ticks file")
    parser.add_argument(
        "--config",
        default="{}",
        help="JSON object with EA configuration",
    )
    args = parser.parse_args()

    config = json.loads(args.config)
    results = main(args.path, config)
    print(results)
