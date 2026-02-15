import unittest

from tradeforge.walk_forward import WalkForwardBacktester, WalkForwardConfig, mse, naive_mean_forecast


class WalkForwardBacktesterTests(unittest.TestCase):
    def test_expanding_split(self):
        cfg = WalkForwardConfig(train_size=5, test_size=2, expanding_window=True)
        backtester = WalkForwardBacktester(cfg)
        splits = backtester.split(12)
        self.assertEqual(
            splits,
            [
                (0, 5, 5, 7),
                (0, 7, 7, 9),
                (0, 9, 9, 11),
            ],
        )

    def test_rolling_split(self):
        cfg = WalkForwardConfig(train_size=5, test_size=2, expanding_window=False)
        backtester = WalkForwardBacktester(cfg)
        splits = backtester.split(12)
        self.assertEqual(
            splits,
            [
                (0, 5, 5, 7),
                (2, 7, 7, 9),
                (4, 9, 9, 11),
            ],
        )

    def test_run_and_summary(self):
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        cfg = WalkForwardConfig(train_size=4, test_size=2)
        backtester = WalkForwardBacktester(cfg)

        def fit_fn(train):
            return sum(train) / len(train)

        def evaluate_fn(model, test):
            predictions = [model] * len(test)
            return {"mse": mse(predictions, test)}

        results = backtester.run(data, fit_fn=fit_fn, evaluate_fn=evaluate_fn)
        self.assertEqual(len(results), 2)
        summary = backtester.summarize(results)
        self.assertIn("mse", summary)
        self.assertGreater(summary["mse"], 0)


class UtilityTests(unittest.TestCase):
    def test_naive_mean_forecast(self):
        forecast = naive_mean_forecast([1.0, 3.0, 5.0], horizon=4)
        self.assertEqual(forecast, [3.0, 3.0, 3.0, 3.0])


if __name__ == "__main__":
    unittest.main()
