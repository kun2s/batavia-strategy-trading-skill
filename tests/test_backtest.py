import unittest

from backtest.engine import (
    MarketData, align_market_data, chronological_windows, confirm_regimes, run,
)
from batavia.regime import EUPHORIA, RANGING, RISK_OFF, Signals, TRENDING_UP


def market(closes, fear=None):
    n = len(closes)
    opens = [closes[0]] + closes[:-1]
    return MarketData(
        list(range(0, n * 3_600_000, 3_600_000)), opens,
        [max(o, c) * 1.001 for o, c in zip(opens, closes)],
        [min(o, c) * 0.999 for o, c in zip(opens, closes)], closes,
        fear or [50.0] * n, [None] * n,
    )


class BacktestTests(unittest.TestCase):
    def test_confirmation_and_immediate_risk_override(self):
        raw = [RANGING, TRENDING_UP, TRENDING_UP, TRENDING_UP, RANGING, EUPHORIA]
        signals = [Signals(50, 0, "normal", None) for _ in raw]
        signals[-1] = Signals(90, 1, "normal", 0.8)
        labels, _ = confirm_regimes(raw, signals)
        self.assertEqual(labels[2], RANGING)
        self.assertEqual(labels[3], TRENDING_UP)
        self.assertEqual(labels[-1], EUPHORIA)

    def test_all_policies_run_and_windows_do_not_overlap(self):
        data = market([100 + i * 0.2 for i in range(180)])
        for policy in ("router", "trend_cash", "sentiment_momentum", "momentum",
                       "mean_reversion", "buy_hold", "cash"):
            self.assertEqual(run(data, policy)["policy"], policy)
        windows = chronological_windows(len(data))
        self.assertEqual(windows[0][1], windows[1][0])
        self.assertEqual(windows[1][1], windows[2][0])

    def test_sentiment_candidate_matches_momentum_without_veto(self):
        data = market([100 + i * 0.2 for i in range(180)])
        sentiment = run(data, "sentiment_momentum")
        momentum = run(data, "momentum")
        self.assertEqual(sentiment["total_return_pct"], momentum["total_return_pct"])
        self.assertEqual(sentiment["trades"], momentum["trades"])

    def test_mark_to_market_drawdown_for_buy_hold(self):
        closes = [100.0] * 55 + [80.0] * 10 + [100.0] * 10
        result = run(market(closes), "buy_hold")
        self.assertGreater(result["max_drawdown_pct"], 19.0)

    def test_stop_first_when_entry_bar_touches_both(self):
        closes = [100.0] * 50 + [110.0] + [110.0] * 10
        data = market(closes)
        data.opens[51] = 110.0
        data.highs[51] = 125.0
        data.lows[51] = 100.0
        result = run(data, "momentum")
        self.assertEqual(result["exits"].get("stop_loss"), 1)

    def test_final_bar_liquidates_open_position(self):
        closes = [100.0] * 50 + [101.0] * 10
        result = run(market(closes), "momentum")
        self.assertEqual(result["trades"], 1)
        self.assertEqual(result["exits"], {"final_bar": 1})
        self.assertEqual(result["trades_detail"][0]["exit_bar"], len(closes) - 1)

    def test_flat_round_trip_charges_both_fees(self):
        closes = [100.0] * 50 + [101.0] * 10
        result = run(market(closes), "momentum")
        trade_return = result["trades_detail"][0]["return_pct"]
        self.assertLess(trade_return, -0.09)
        self.assertGreater(trade_return, -0.11)
        self.assertLess(result["total_return_pct"], 0.0)

    def test_asset_comparison_uses_common_timestamps(self):
        first = market([100.0] * 80)
        second = market([100.0] * 80)
        second.timestamps = [timestamp + 3_600_000 for timestamp in second.timestamps]
        aligned = align_market_data({"A": first, "B": second})
        self.assertEqual(aligned["A"].timestamps, aligned["B"].timestamps)
        self.assertEqual(len(aligned["A"]), 79)

    def test_intrabar_exit_cannot_reenter_at_past_open(self):
        closes = [100.0] * 50 + [101.0, 99.0, 101.0] + [101.0] * 10
        data = market(closes)
        data.lows[53] = 90.0
        result = run(data, "momentum")
        self.assertEqual(result["trades"], 1)
        self.assertEqual(result["exits"], {"stop_loss": 1})
        self.assertGreater(result["exposure_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
