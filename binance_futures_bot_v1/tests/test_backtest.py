import unittest

import pandas as pd

from src.backtest import run_backtest


class BacktestTests(unittest.TestCase):
    def test_empty_signals_preserve_balance(self):
        times = pd.date_range("2026-01-01", periods=80, freq="15min", tz="UTC")
        hourly_times = pd.date_range("2025-12-28", periods=100, freq="1h", tz="UTC")
        m15 = pd.DataFrame({
            "open_time": times,
            "close_time": times + pd.Timedelta(minutes=15) - pd.Timedelta(milliseconds=1),
            "open": [100.0] * 80, "high": [101.0] * 80,
            "low": [99.0] * 80, "close": [100.0] * 80,
            "volume": [100.0] * 80,
        })
        h1 = pd.DataFrame({
            "open_time": hourly_times,
            "close_time": hourly_times + pd.Timedelta(hours=1) - pd.Timedelta(milliseconds=1),
            "open": [100.0] * 100, "high": [101.0] * 100,
            "low": [99.0] * 100, "close": [100.0] * 100,
            "volume": [100.0] * 100,
        })
        trades, summary = run_backtest(
            {"BTCUSDT": m15}, {"BTCUSDT": h1}, initial_balance=100,
            fee_rate=0, slippage_rate=0,
        )
        self.assertTrue(trades.empty)
        self.assertEqual(summary["final_balance"], 100)
        self.assertEqual(summary["trades"], 0)


if __name__ == "__main__":
    unittest.main()
