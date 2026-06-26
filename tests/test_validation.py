import csv
from pathlib import Path
import tempfile
import unittest

from backtest.engine import POLICIES
from backtest.render_results import render
from backtest.validate_basket import DEFAULT, validate


class ValidationTests(unittest.TestCase):
    def test_full_candidate_report_on_aligned_basket(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fields = [
                "timestamp", "open", "high", "low", "close", "volume",
                "fear_greed", "funding_stress",
            ]
            for asset_index, symbol in enumerate(DEFAULT):
                with (root / f"{symbol.lower()}_1h.csv").open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    previous = 100.0 + asset_index
                    for index in range(180):
                        close = 100.0 + asset_index + index * 0.03
                        writer.writerow({
                            "timestamp": index * 3_600_000,
                            "open": previous,
                            "high": max(previous, close) * 1.001,
                            "low": min(previous, close) * 0.999,
                            "close": close,
                            "volume": 1_000,
                            "fear_greed": 50,
                            "funding_stress": "",
                        })
                        previous = close
            report = validate(root, DEFAULT)
        self.assertEqual(set(report["summary"]), set(POLICIES))
        self.assertEqual(report["common_bars"], 180)
        self.assertIn(report["selection"]["selected"], POLICIES)
        self.assertIn("mean_reversion_eligible", report["selection"])
        self.assertIn("Candidate summary", render(report))


if __name__ == "__main__":
    unittest.main()
