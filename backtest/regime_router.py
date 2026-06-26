#!/usr/bin/env python3
"""Run one Batavia market CSV through every candidate policy."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.engine import POLICIES, load_market_csv, run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="timestamp,open,high,low,close,fear_greed,funding_stress")
    parser.add_argument("--policy", choices=POLICIES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = load_market_csv(args.csv)
    policies = [args.policy] if args.policy else list(POLICIES)
    results = {policy: run(data, policy) for policy in policies}
    if args.json:
        print(json.dumps(results, indent=2))
        return
    print(f"{'policy':<22}{'return':>10}{'maxDD':>10}{'R/DD':>9}{'trades':>9}{'exposure':>11}")
    print("-" * 71)
    for policy, result in results.items():
        print(f"{policy:<22}{result['total_return_pct']:>9.2f}%{result['max_drawdown_pct']:>9.2f}%"
              f"{result['return_over_drawdown']:>9.2f}{result['trades']:>9}"
              f"{result['exposure_pct']:>10.1f}%")


if __name__ == "__main__":
    main()
