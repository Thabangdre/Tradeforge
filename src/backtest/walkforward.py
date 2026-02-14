from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any, Callable, Dict, List, Optional

from backtest.engine import BacktestEngine
from backtest.execution import ExecutionConfig
from backtest.models import Bar
from backtest.report import build_research_report
from backtest.spread import SpreadModel


@dataclass(frozen=True)
class WalkForwardSpec:
    train_bars: int
    test_bars: int
    step_bars: int
    start_index: int = 0
    end_index: Optional[int] = None


@dataclass(frozen=True)
class WalkForwardSegment:
    seg_id: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int


def make_segments(n_bars: int, spec: WalkForwardSpec) -> List[WalkForwardSegment]:
    if n_bars <= 0:
        return []
    if spec.train_bars <= 0 or spec.test_bars <= 0 or spec.step_bars <= 0:
        raise ValueError("train_bars, test_bars, and step_bars must be positive")
    start = max(0, spec.start_index)
    end = n_bars if spec.end_index is None else min(spec.end_index, n_bars)
    if start >= end:
        return []

    segments: list[WalkForwardSegment] = []
    i = start
    seg_id = 0
    while True:
        train_start = i
        train_end = i + spec.train_bars
        test_start = train_end
        test_end = test_start + spec.test_bars
        if test_end > end:
            break
        segments.append(
            WalkForwardSegment(
                seg_id=seg_id,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
        seg_id += 1
        i += spec.step_bars
    return segments


def _median_ignore_none(values: list[float | None]) -> float | None:
    kept = [v for v in values if v is not None]
    return None if not kept else float(median(kept))


def _run_window(
    bars: list[Bar],
    strategy_factory: Callable[[Dict[str, Any]], Any],
    *,
    seg_id: int,
    mode: str,
    symbol: str,
    spread_model: SpreadModel,
    exec_config: ExecutionConfig,
    spreads: Dict[str, float],
    initial_cash: float,
    top_n_losses: int,
) -> Dict[str, Any]:
    strategy = strategy_factory({"seg_id": seg_id, "mode": mode})
    engine = BacktestEngine(
        bars,
        symbol=symbol,
        strategy=strategy,
        spread_model=spread_model,
        exec_config=exec_config,
        spreads=dict(sorted(spreads.items())),
        initial_cash=initial_cash,
    )
    result = engine.run()
    return build_research_report(result, top_n_losses=top_n_losses)


def walk_forward(
    bars: List[Bar],
    strategy_factory: Callable[[Dict[str, Any]], Any],
    *,
    symbol: str,
    spread_model: SpreadModel,
    exec_config: ExecutionConfig,
    spreads: Dict[str, float],
    spec: WalkForwardSpec,
    initial_cash: float = 0.0,
    top_n_losses: int = 10,
    run_train: bool = False,
    dd_pass_threshold: float | None = None,
) -> Dict[str, Any]:
    segments = make_segments(len(bars), spec)
    if not segments:
        raise ValueError("No walk-forward segments were generated")

    segment_rows: list[dict[str, Any]] = []
    net_pnl_worst_by_segment: list[float] = []
    pf_worst_by_segment: list[float | None] = []
    dd_worst_by_segment: list[float | None] = []
    fragility_by_segment: list[float | None] = []

    for seg in segments:
        train_slice = bars[seg.train_start : seg.train_end]
        test_slice = bars[seg.test_start : seg.test_end]
        test_report = _run_window(
            test_slice,
            strategy_factory,
            seg_id=seg.seg_id,
            mode="test",
            symbol=symbol,
            spread_model=spread_model,
            exec_config=exec_config,
            spreads=spreads,
            initial_cash=initial_cash,
            top_n_losses=top_n_losses,
        )
        row: dict[str, Any] = {
            "seg_id": seg.seg_id,
            "train_range": {"start": seg.train_start, "end": seg.train_end, "bars": len(train_slice)},
            "test_range": {"start": seg.test_start, "end": seg.test_end, "bars": len(test_slice)},
            "test_report": test_report,
        }
        if run_train:
            row["train_report"] = _run_window(
                train_slice,
                strategy_factory,
                seg_id=seg.seg_id,
                mode="train",
                symbol=symbol,
                spread_model=spread_model,
                exec_config=exec_config,
                spreads=spreads,
                initial_cash=initial_cash,
                top_n_losses=top_n_losses,
            )
        segment_rows.append(row)

        headline = test_report.get("headline", {})
        net_pnl_worst_by_segment.append(float(headline.get("net_pnl", 0.0)))
        pf_worst_by_segment.append(headline.get("profit_factor"))
        dd_worst_by_segment.append(headline.get("max_drawdown"))
        fragility_by_segment.append(test_report.get("fragility"))

    pf_pass_threshold = 1.0
    pf_pass_rate = sum(1 for pf in pf_worst_by_segment if pf is not None and pf >= pf_pass_threshold) / len(segments)
    dd_pass_rate = None
    if dd_pass_threshold is not None:
        dd_pass_rate = sum(1 for dd in dd_worst_by_segment if dd is not None and dd <= dd_pass_threshold) / len(segments)

    summary = {
        "segments": len(segments),
        "median_pf_worst": _median_ignore_none(pf_worst_by_segment),
        "median_dd_worst": _median_ignore_none(dd_worst_by_segment),
        "pass_rate_pf": pf_pass_rate,
        "pass_rate_dd": dd_pass_rate,
        "fragility_median": _median_ignore_none(fragility_by_segment),
        "net_pnl_worst_total": float(sum(net_pnl_worst_by_segment)),
        "net_pnl_worst_by_segment": net_pnl_worst_by_segment,
        "pf_worst_by_segment": pf_worst_by_segment,
        "dd_worst_by_segment": dd_worst_by_segment,
    }

    return {
        "spec": {
            "train_bars": spec.train_bars,
            "test_bars": spec.test_bars,
            "step_bars": spec.step_bars,
            "start_index": spec.start_index,
            "end_index": spec.end_index,
        },
        "segments": segment_rows,
        "summary": summary,
    }
