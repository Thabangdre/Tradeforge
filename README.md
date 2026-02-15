# Tradeforge

A lightweight walk-forward backtesting module for time-series strategies.

## Quick start

```python
from tradeforge.walk_forward import WalkForwardBacktester, WalkForwardConfig, mse

prices = [101, 102, 100, 104, 103, 105, 106, 108, 107]
config = WalkForwardConfig(train_size=4, test_size=2, expanding_window=True)
backtester = WalkForwardBacktester(config)


def fit_fn(train_window):
    return sum(train_window) / len(train_window)


def evaluate_fn(model, test_window):
    preds = [model] * len(test_window)
    return {"mse": mse(preds, test_window)}

results = backtester.run(prices, fit_fn, evaluate_fn)
summary = backtester.summarize(results)
```

Run tests:

```bash
python -m unittest discover -s tests
```
