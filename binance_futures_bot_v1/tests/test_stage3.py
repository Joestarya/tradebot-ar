import unittest

import pandas as pd

from src.risk import calculate_position_size
from src.strategy import generate_signal


class RiskTests(unittest.TestCase):
    def test_size_respects_risk_budget(self):
        result = calculate_position_size(
            balance_usdt=100, entry=100, stop_loss=99,
            risk_fraction=0.01, leverage=10,
            fee_rate=0, slippage_rate=0,
            quantity_step=0.001, min_quantity=0.001, min_notional=1,
        )
        self.assertTrue(result.accepted)
        self.assertLessEqual(result.estimated_loss, result.risk_budget)

    def test_rejects_below_minimum(self):
        result = calculate_position_size(
            balance_usdt=10, entry=100, stop_loss=99,
            risk_fraction=0.01, leverage=10,
            fee_rate=0, slippage_rate=0,
            quantity_step=0.001, min_quantity=0.001, min_notional=100,
        )
        self.assertFalse(result.accepted)


class StrategyTests(unittest.TestCase):
    def test_no_signal_when_trend_neutral(self):
        rows = 60
        close = [100 + (i % 2) * 0.01 for i in range(rows)]
        df1h = pd.DataFrame({"close": close})
        df15 = pd.DataFrame({
            "close": [100.0] * 4, "high": [101.0] * 4,
            "low": [99.0] * 4, "rsi_14": [55.0] * 4,
            "macd_hist": [0.1, 0.2, 0.3, 0.4], "atr_14": [1.0] * 4,
            "volume_ratio": [1.2] * 4, "support": [99.0] * 4,
            "resistance": [101.0] * 4,
        })
        self.assertIsNone(generate_signal(df15, df1h, "BTCUSDT"))


if __name__ == "__main__":
    unittest.main()
