#!/usr/bin/env python3
"""Batavia — generate a regime-aware, backtestable strategy spec for a token.

This is the Track 2 deliverable's entry point: market-regime signals in, a
schema-valid `strategy_spec` out. No live trading happens here — the output is a
research artifact a backtester runs.

Signal sources (CoinMarketCap Agent Hub):
  - trend_score / vol_state : derive from a 1h OHLCV series  (--csv)  OR pass --trend/--vol
  - fear_greed              : get_fear_and_greed_latest                (--fear-greed)
  - funding_stress          : get_global_crypto_derivatives_metrics    (--funding)

Examples:
  python generate_spec.py ETH --fear-greed 72 --trend 0.7 --funding 0.2
  python generate_spec.py ETH --csv data/eth_1h.csv --fear-greed 35
  python generate_spec.py ETH -o examples/eth.json
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone

from batavia.regime import Signals, build_spec
from batavia.indicators import derive_signals


def _load_ohlcv(path):
    """CSV with header columns: high,low,close (timestamp/open/volume optional)."""
    highs, lows, closes = [], [], []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            highs.append(float(row["high"]))
            lows.append(float(row["low"]))
            closes.append(float(row["close"]))
    if len(closes) < 50:
        sys.exit(f"need >=50 bars to derive trend/vol, got {len(closes)}")
    return highs, lows, closes


def main():
    p = argparse.ArgumentParser(description="Generate a Batavia regime strategy spec.")
    p.add_argument("symbol", help="token symbol, e.g. ETH")
    p.add_argument("--csv", help="1h OHLCV csv -> derive trend_score & vol_state")
    p.add_argument("--trend", type=float, help="manual trend_score [-1..1]")
    p.add_argument("--vol", choices=["low", "normal", "high"], help="manual vol_state")
    p.add_argument("--fear-greed", type=float, default=50.0, help="CMC F&G index 0..100")
    p.add_argument("--funding", type=float, default=0.0, help="normalized funding [-1..1]")
    p.add_argument("--as-of", help="ISO timestamp (default: now, UTC)")
    p.add_argument("-o", "--out", help="write spec here (default: stdout)")
    args = p.parse_args()

    if args.csv:
        highs, lows, closes = _load_ohlcv(args.csv)
        sig = derive_signals(highs, lows, closes,
                             fear_greed=args.fear_greed, funding_stress=args.funding)
        if args.trend is not None:
            sig.trend_score = args.trend
        if args.vol is not None:
            sig.vol_state = args.vol
    else:
        sig = Signals(fear_greed=args.fear_greed,
                      trend_score=args.trend or 0.0,
                      vol_state=args.vol or "normal",
                      funding_stress=args.funding)

    as_of = args.as_of or datetime.now(timezone.utc).isoformat(timespec="seconds")
    spec = build_spec(args.symbol, sig, as_of=as_of)

    text = json.dumps(spec, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text + "\n")
        r = spec["regime"]
        print(f"wrote {args.out}  ->  regime={r['label']}  ({r['rationale']})")
    else:
        print(text)


if __name__ == "__main__":
    main()
