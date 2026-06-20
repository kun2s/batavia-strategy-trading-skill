#!/usr/bin/env python3
"""Multi-asset validation: run the router + baselines across a basket and report
per-asset and aggregate results. This is what turns a single-window anecdote into
a robustness claim — the router's thesis is "lower drawdown across regimes/assets,"
which only a basket can test.

Usage:  python backtest/validate_basket.py [SYM1 SYM2 ...] [--bars N]
Default basket: BTC ETH BNB SOL AVAX LINK DOGE   (all liquid on Binance).
Uses only free public data (Binance klines/funding + alternative.me F&G).
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch_data import fetch_klines, fetch_fng, fetch_funding, _funding_at  # noqa: E402
from regime_router import run  # noqa: E402

DEFAULT = ["BTC", "ETH", "BNB", "SOL", "AVAX", "LINK", "DOGE"]


def build_series(symbol, bars, fng):
    klines = fetch_klines(symbol, bars)
    funding = fetch_funding(symbol)
    highs = [k[1] for k in klines]
    lows = [k[2] for k in klines]
    closes = [k[3] for k in klines]
    fgs, fundings, last = [], [], 50.0
    for t_ms, *_ in klines:
        day = datetime.fromtimestamp(t_ms / 1000, timezone.utc).strftime("%Y-%m-%d")
        last = fng.get(day, last)
        fgs.append(last)
        fundings.append(round(_funding_at(funding, t_ms), 4))
    return highs, lows, closes, fgs, fundings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*", default=DEFAULT)
    ap.add_argument("--bars", type=int, default=3000)
    args = ap.parse_args()
    symbols = args.symbols or DEFAULT

    fng = fetch_fng()
    rows = []
    print(f"{'asset':<7}{'router':>9}{'rtr_DD':>8}{'mom':>9}{'mom_DD':>8}"
          f"{'meanrev':>9}{'b&h':>9}")
    print("-" * 59)
    for sym in symbols:
        try:
            h, l, c, fgs, fd = build_series(sym, args.bars, fng)
        except Exception as e:
            print(f"{sym:<7}  skip ({e})")
            continue
        r = run(h, l, c, fgs, fd, mode="router")
        m = run(h, l, c, fgs, fd, mode="momentum")
        mr = run(h, l, c, fgs, fd, mode="mean_reversion")
        bh = r["buy_hold_return_pct"]
        rows.append((sym, r, m, mr, bh))
        print(f"{sym:<7}{r['total_return_pct']:>8.1f}%{r['max_drawdown_pct']:>7.1f}%"
              f"{m['total_return_pct']:>8.1f}%{m['max_drawdown_pct']:>7.1f}%"
              f"{mr['total_return_pct']:>8.1f}%{bh:>8.1f}%")

    if not rows:
        return
    n = len(rows)
    def avg(f): return sum(f(x) for x in rows) / n
    print("-" * 59)
    print(f"{'MEAN':<7}{avg(lambda x: x[1]['total_return_pct']):>8.1f}%"
          f"{avg(lambda x: x[1]['max_drawdown_pct']):>7.1f}%"
          f"{avg(lambda x: x[2]['total_return_pct']):>8.1f}%"
          f"{avg(lambda x: x[2]['max_drawdown_pct']):>7.1f}%"
          f"{avg(lambda x: x[3]['total_return_pct']):>8.1f}%"
          f"{avg(lambda x: x[4]):>8.1f}%")

    # the robustness lens: drawdown, not return
    dd_better_bh = sum(1 for x in rows if x[1]['max_drawdown_pct'] < abs(x[4]))
    dd_better_mom = sum(1 for x in rows if x[1]['max_drawdown_pct'] <= x[2]['max_drawdown_pct'])
    ret_beats_bh = sum(1 for x in rows if x[1]['total_return_pct'] > x[4])
    print(f"\nrobustness across {n} assets:")
    print(f"  router maxDD < |buy&hold return|   : {dd_better_bh}/{n}")
    print(f"  router maxDD <= momentum maxDD      : {dd_better_mom}/{n}")
    print(f"  router return > buy&hold return     : {ret_beats_bh}/{n}")
    print("\nReading: the router's claim is drawdown control across assets, not "
          "out-returning momentum on any single one. Judge it on the maxDD columns.")


if __name__ == "__main__":
    main()
