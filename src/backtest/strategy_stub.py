class MissingStrategyError(RuntimeError):
    """Raised when the default FibsDontLie strategy is unavailable."""


def make_default_fibsdontlie_strategy():
    raise MissingStrategyError(
        "FibsDontLie strategy not found. Plug in your strategy class and update run_us30_report.py."
    )
