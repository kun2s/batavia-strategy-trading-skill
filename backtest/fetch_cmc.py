#!/usr/bin/env python3
"""Fetch independent CoinMarketCap OHLCV and Fear & Greed research inputs."""
import argparse
from bisect import bisect_right
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from batavia.cmc import CMCClient, CMCError  # noqa: E402

DEFAULT = ["BTC", "ETH", "BNB", "SOL", "AVAX", "LINK", "DOGE"]


def fetch_hourly_chunks(client, cmc_id, start, end, chunk_days=30):
    """Fetch bounded windows and de-duplicate boundary candles."""
    by_timestamp = {}
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=chunk_days), end)
        rows = client.ohlcv_hourly(
            cmc_id, time_start=cursor.isoformat(), time_end=chunk_end.isoformat()
        )
        by_timestamp.update((row["timestamp"], row) for row in rows)
        cursor = chunk_end
    return [by_timestamp[key] for key in sorted(by_timestamp)]


def validate_coverage(rows, days):
    minimum = int(days * 24 * 0.95)
    if len(rows) < minimum:
        raise RuntimeError(f"CMC returned {len(rows)} rows; expected at least {minimum}")
    timestamps = [row["timestamp"] for row in rows]
    if timestamps != sorted(set(timestamps)):
        raise RuntimeError("CMC candles are duplicated or out of order")


def closed_interval(rows, start, end):
    """Keep candle opens in [start, end); the candle opening at end is not closed."""
    lower = int(start.timestamp() * 1000)
    upper = int(end.timestamp() * 1000)
    return [row for row in rows if lower <= row["timestamp"] < upper]


def sentiment_as_of(rows, observations):
    """Return the latest published sentiment at each candle timestamp."""
    published = sorted((int(item["timestamp"]) * 1000, item["value"]) for item in observations)
    timestamps = [item[0] for item in published]
    values = [item[1] for item in published]
    result = []
    for row in rows:
        index = bisect_right(timestamps, row["timestamp"]) - 1
        result.append(values[index] if index >= 0 else None)
    return result


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbols", nargs="*", default=DEFAULT)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--out-dir", default="data/cmc")
    args = parser.parse_args()
    if args.days <= 0:
        parser.error("--days must be positive")
    client = CMCClient()
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=args.days)
    os.makedirs(args.out_dir, exist_ok=True)
    fear = client.fear_greed_historical(limit=min(500, args.days + 5))
    manifest = {
        "source": "CoinMarketCap Pro API",
        "endpoints": [
            "/v1/cryptocurrency/map",
            "/v2/cryptocurrency/ohlcv/historical",
            "/v3/fear-and-greed/historical",
        ],
        "fetched_at": end.isoformat(),
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "requested_days": args.days,
        "assets": {},
    }
    for symbol in [value.upper() for value in args.symbols]:
        asset = client.resolve_asset(symbol)
        rows = closed_interval(fetch_hourly_chunks(client, asset["id"], start, end), start, end)
        validate_coverage(rows, args.days)
        fear_values = sentiment_as_of(rows, fear)
        path = os.path.join(args.out_dir, f"{symbol.lower()}_1h.csv")
        with open(path, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "timestamp", "open", "high", "low", "close", "volume", "fear_greed", "funding_stress",
            ])
            writer.writeheader()
            for row, fear_value in zip(rows, fear_values):
                writer.writerow({
                    **row,
                    "fear_greed": "" if fear_value is None else fear_value,
                    "funding_stress": "",
                })
        fear_rows = sum(value is not None for value in fear_values)
        manifest["assets"][symbol] = {
            "cmc_id": asset["id"],
            "rows": len(rows),
            "fear_greed_rows": fear_rows,
            "first_timestamp": rows[0]["timestamp"],
            "last_timestamp": rows[-1]["timestamp"],
            "sha256": sha256_file(path),
            "file": path,
        }
        print(f"{symbol}: CMC ID {asset['id']} / {len(rows)} hourly bars")
    with open(os.path.join(args.out_dir, "manifest.json"), "w") as handle:
        json.dump(manifest, handle, indent=2)


if __name__ == "__main__":
    try:
        main()
    except CMCError as exc:
        message = str(exc)
        if "HTTP 403" in message and "ohlcv/historical" in message:
            raise SystemExit(
                "CMC denied historical OHLCV (HTTP 403). The key is valid, but its "
                "subscription does not grant /v2/cryptocurrency/ohlcv/historical."
            )
        raise SystemExit(message)
