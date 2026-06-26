import unittest

from batavia.indicators import atr_series, bollinger, ema, rsi, trend_score


class IndicatorTests(unittest.TestCase):
    def test_ema_warmup_and_direction(self):
        values = list(range(1, 31))
        result = ema(values, 20)
        self.assertIsNone(result[18])
        self.assertIsNotNone(result[19])
        self.assertGreater(result[-1], result[19])

    def test_rsi_extremes(self):
        self.assertEqual(rsi(list(range(20)), 14)[-1], 100.0)
        self.assertLess(rsi(list(range(20, 0, -1)), 14)[-1], 1.0)

    def test_rsi_flat_market_is_neutral(self):
        self.assertEqual(rsi([100.0] * 20, 14)[-1], 50.0)

    def test_bollinger_contains_flat_series(self):
        upper, middle, lower = bollinger([100.0] * 25)
        self.assertEqual((upper[-1], middle[-1], lower[-1]), (100.0, 100.0, 100.0))

    def test_atr_and_trend_score(self):
        closes = [100 + i for i in range(60)]
        atr = atr_series([c + 1 for c in closes], [c - 1 for c in closes], closes)
        self.assertGreater(atr[-1], 0)
        self.assertGreater(trend_score(closes[-1], 120, 110), 0.5)


if __name__ == "__main__":
    unittest.main()
