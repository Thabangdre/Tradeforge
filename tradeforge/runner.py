from __future__ import annotations

from pathlib import Path
from typing import Any

from .csv_ticks import load_ticks_csv



def run_fibo_on_csv(path: str | Path, config: dict[str, Any]) -> Any:
    """Load CSV ticks and run the Fibonacci EA engine on them."""

    try:
        from .fibo import run_fibo_ea
    except ImportError as exc:  # pragma: no cover - only triggered in incomplete setups
        raise ImportError(
            "run_fibo_ea is not available. Expected tradeforge.fibo.run_fibo_ea"
        ) from exc

    tick_data = load_ticks_csv(path)
    return run_fibo_ea(tick_data.ticks, config)
