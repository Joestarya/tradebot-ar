import unittest
import numpy as np
import pandas as pd

from src.indicators import wilder_rma, calculate_rsi, calculate_pivots


class IndicatorTests(unittest.TestCase):
    def test_rma_sma_seed(self):
        result = wilder_rma(pd.Series([1., 2., 3., 4., 5.]), 3)
        self.assertTrue(np.isnan(result.iloc[1]))
        self.assertAlmostEqual(result.iloc[2], 2.)
        self.assertAlmostEqual(result.iloc[3], 8. / 3.)

    def test_rsi_all_gains(self):
        result = calculate_rsi(pd.Series(range(1, 20), dtype=float), 14)
        self.assertAlmostEqual(result.iloc[14], 100.)

    def test_pivot_confirmation_delay(self):
        high = pd.Series([1., 2., 5., 3., 2., 1., 2.])
        low = pd.Series([0., 1., 2., 1., 0., -1., 0.])
        result = calculate_pivots(high, low, left=2, right=2)
        self.assertTrue(np.isnan(result.loc[2, "pivot_high_confirmed"]))
        self.assertEqual(result.loc[4, "pivot_high_confirmed"], 5.)


if __name__ == "__main__":
    unittest.main()
