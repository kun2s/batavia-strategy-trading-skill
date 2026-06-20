#!/usr/bin/env python3
"""Fetch real, free public data to validate Batavia on actual history.

Sources (all free, no API key):
  - 1h OHLCV         : Binance public klines      (api.binance.com)
  - Fear & Greed     : alternative.me FNG index   (daily, mapped to each hour)
  - perp funding     : Binance futures fundingRate (every 8h, normalized)

Writes two aligned CSVs the backtester reads:
  data/<sym>_1h_price.csv   -> timestamp,high,low,close
  data/<sym>_1h_ctx.csv     -> fear_greed,funding   (one row per price bar)

Usage:  python backtest/fetch_data.py ETH --bars 3000
Note: uses only the Python standard library (urllib) — no extra deps.
"""
import argparse
import csv
import json
import os
import urllib.request
from datetime import datetime, timezone

FUNDING_SCALE = 0.0005   # per-8h rate that maps to funding_stress = 1.0 (crowded)


def _get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def fetch_klines(symbol, bars):
    """Paginate Binance 1h klines backward -> list of (open_ms, high, low, close)."""
    out, end = [], None
    while len(out) < bars:
        url = (f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT"
               f"&interval=1h&limit=1000")
        if end:
            url += f"&endTime={end}"
        batch = _get(url)
        if not batch:
            break
        rows = [(int(k[0]), float(k[2]), float(k[3]), float(k[4])) for k in batch]
        out = rows + out
        end = batch[0][0] - 1
        if len(batch) < 1000:
            break
    # dedupe + sort ascending, keep the most recent `bars`
    seen, dedup = set(), []
    for r in sorted(out):
        if r[0] not in seen:
            seen.add(r[0]); dedup.append(r)
    return dedup[-bars:]


def fetch_fng(days=300):
    """alternative.me -> {utc_date_str: value}."""
    data = _get(f"https://api.alternative.me/fng/?limit={days}&format=json")["data"]
    out = {}
    for d in data:
        day = datetime.fromtimestamp(int(d["timestamp"]), timezone.utc).strftime("%Y-%m-%d")
        out[day] = float(d["value"])
    return out


def fetch_funding(symbol):
    """Binance funding history -> sorted [(time_ms, rate)] (every ~8h)."""
    data = _get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}USDT&limit=1000")
    return sorted((int(d["fundingTime"]), float(d["fundingRate"])) for d in data)


def _funding_at(funding, t_ms):
    """Most recent funding rate at-or-before t_ms, normalized to [-1, 1]."""
    rate = 0.0
    for ft, fr in funding:
        if ft <= t_ms:
            rate = fr
        else:
            break
    return max(-1.0, min(1.0, rate / FUNDING_SCALE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol", nargs="?", default="ETH")
    ap.add_argument("--bars", type=int, default=3000, help="how many 1h bars")
    args = ap.parse_args()
    sym = args.symbol.upper()

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(here, "data")
    os.makedirs(data_dir, exist_ok=True)

    print(f"fetching {args.bars} 1h bars for {sym} ...")
    klines = fetch_klines(sym, args.bars)
    print(f"  got {len(klines)} bars "
          f"({datetime.fromtimestamp(klines[0][0]/1000, timezone.utc).date()} -> "
          f"{datetime.fromtimestamp(klines[-1][0]/1000, timezone.utc).date()})")
    fng = fetch_fng()
    funding = fetch_funding(sym)
    print(f"  F&G days: {len(fng)}   funding points: {len(funding)}")

    price_path = os.path.join(data_dir, f"{sym.lower()}_1h_price.csv")
    ctx_path = os.path.join(data_dir, f"{sym.lower()}_1h_ctx.csv")
    last_fg = 50.0
    with open(price_path, "w", newline="") as pf, open(ctx_path, "w", newline="") as cf:
        pw, cw = csv.writer(pf), csv.writer(cf)
        pw.writerow(["timestamp", "high", "low", "close"])
        cw.writerow(["fear_greed", "funding"])
        for t_ms, hi, lo, cl in klines:
            day = datetime.fromtimestamp(t_ms/1000, timezone.utc).strftime("%Y-%m-%d")
            last_fg = fng.get(day, last_fg)
            pw.writerow([t_ms, hi, lo, cl])
            cw.writerow([last_fg, round(_funding_at(funding, t_ms), 4)])
    print(f"wrote {price_path}\n      {ctx_path}")


if __name__ == "__main__":
    main()
