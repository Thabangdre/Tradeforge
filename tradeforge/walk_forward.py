"""Walk-forward backtesting primitives for time-series model validation."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Callable, Generic, Sequence, TypeVar

T = TypeVar("T")
M = TypeVar("M")


@dataclass(frozen=True)
class WalkForwardConfig:
    """Configuration for walk-forward splits.

    Attributes:
        train_size: Initial (or fixed) training window length.
        test_size: Validation window length.
        step_size: Number of observations to move between folds.
        expanding_window: When True, training starts at index 0 and grows.
            When False, training uses a fixed-size rolling window.
    """

    train_size: int
    test_size: int
    step_size: int | None = None
    expanding_window: bool = True

    def __post_init__(self) -> None:
        if self.train_size <= 0:
            raise ValueError("train_size must be > 0")
        if self.test_size <= 0:
            raise ValueError("test_size must be > 0")
        if self.step_size is not None and self.step_size <= 0:
            raise ValueError("step_size must be > 0 when provided")


@dataclass(frozen=True)
class FoldResult:
    """Single fold output."""

    fold: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    metrics: dict[str, float]


class WalkForwardBacktester(Generic[T, M]):
    """Backtester that evaluates a model over sequential train/test windows."""

    def __init__(self, config: WalkForwardConfig):
        self.config = config

    def split(self, n_samples: int) -> list[tuple[int, int, int, int]]:
        """Create train/test index boundaries for each fold.

        Returns tuples of: (train_start, train_end, test_start, test_end).
        End indexes are exclusive.
        """

        if n_samples <= 0:
            return []

        step = self.config.step_size or self.config.test_size
        train_size = self.config.train_size
        test_size = self.config.test_size

        folds: list[tuple[int, int, int, int]] = []
        test_start = train_size

        while test_start + test_size <= n_samples:
            if self.config.expanding_window:
                train_start = 0
            else:
                train_start = test_start - train_size

            train_end = test_start
            test_end = test_start + test_size

            if train_start < 0:
                break

            folds.append((train_start, train_end, test_start, test_end))
            test_start += step

        return folds

    def run(
        self,
        data: Sequence[T],
        fit_fn: Callable[[Sequence[T]], M],
        evaluate_fn: Callable[[M, Sequence[T]], dict[str, float]],
    ) -> list[FoldResult]:
        """Run walk-forward backtesting across all folds."""

        results: list[FoldResult] = []

        for fold_index, (train_start, train_end, test_start, test_end) in enumerate(
            self.split(len(data)),
            start=1,
        ):
            train_data = data[train_start:train_end]
            test_data = data[test_start:test_end]
            model = fit_fn(train_data)
            metrics = evaluate_fn(model, test_data)

            results.append(
                FoldResult(
                    fold=fold_index,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    metrics=metrics,
                )
            )

        return results

    @staticmethod
    def summarize(results: Sequence[FoldResult]) -> dict[str, float]:
        """Aggregate numeric metrics across folds by mean."""

        if not results:
            return {}

        metric_names = set().union(*(result.metrics.keys() for result in results))
        summary: dict[str, float] = {}

        for metric in metric_names:
            values = [result.metrics[metric] for result in results if metric in result.metrics]
            if values:
                summary[metric] = mean(values)

        return summary


def mse(predictions: Sequence[float], targets: Sequence[float]) -> float:
    """Compute mean squared error."""

    if len(predictions) != len(targets):
        raise ValueError("predictions and targets must have the same length")
    if not predictions:
        raise ValueError("predictions and targets must be non-empty")

    return sum((pred - target) ** 2 for pred, target in zip(predictions, targets)) / len(predictions)


def naive_mean_forecast(train_data: Sequence[float], horizon: int) -> list[float]:
    """Generate a constant forecast using the training-set mean."""

    if horizon <= 0:
        raise ValueError("horizon must be > 0")
    if not train_data:
        raise ValueError("train_data must be non-empty")

    avg = mean(train_data)
    return [avg] * horizon
