#!/usr/bin/env python3
"""Compile normalized CoinMarketCap evidence into a Batavia v0.2 receipt."""
import argparse
import csv
from datetime import datetime, timezone
import json

from batavia.indicators import derive_signals
from batavia.regime import Evidence, Signals, build_spec


def load_ohlcv(path):
    rows = list(csv.DictReader(open(path, newline="")))
    if len(rows) < 50:
        raise SystemExit(f"need at least 50 OHLCV rows, got {len(rows)}")
    return ([float(row["high"]) for row in rows],
            [float(row["low"]) for row in rows],
            [float(row["close"]) for row in rows])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("--cmc-id", type=int)
    parser.add_argument("--csv", help="hourly OHLCV used to derive trend and volatility")
    parser.add_argument("--trend", type=float)
    parser.add_argument("--vol", choices=["low", "normal", "high"])
    parser.add_argument("--fear-greed", type=float)
    parser.add_argument("--funding", type=float)
    parser.add_argument("--confirmation", type=int, default=1)
    parser.add_argument("--observed-at")
    parser.add_argument("--as-of")
    parser.add_argument("--source", action="append", default=[], help="source label; repeatable")
    parser.add_argument("-o", "--out")
    args = parser.parse_args()

    as_of = args.as_of or datetime.now(timezone.utc).isoformat(timespec="seconds")
    observed_at = args.observed_at or as_of
    if args.csv:
        highs, lows, closes = load_ohlcv(args.csv)
        signals = derive_signals(highs, lows, closes, args.fear_greed, args.funding)
        if args.trend is not None or args.vol is not None:
            signals = Signals(
                fear_greed=signals.fear_greed,
                trend_score=args.trend if args.trend is not None else signals.trend_score,
                vol_state=args.vol or signals.vol_state,
                funding_stress=signals.funding_stress,
            )
    else:
        signals = Signals(args.fear_greed, args.trend, args.vol, args.funding)

    sources = tuple({"name": name, "observed_at": observed_at} for name in args.source)
    evidence = Evidence(cmc_id=args.cmc_id, observed_at=observed_at, sources=sources)
    receipt = build_spec(args.symbol, signals, evidence=evidence, as_of=as_of,
                         confirmation_count=args.confirmation)
    rendered = json.dumps(receipt, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(rendered + "\n")
        print(f"wrote {args.out}: {receipt['decision_status']} / {receipt['regime']['label']}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
