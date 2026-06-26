"""Small CoinMarketCap Pro API client for reproducible Batavia research."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://pro-api.coinmarketcap.com"


class CMCError(RuntimeError):
    pass


class CMCClient:
    def __init__(self, api_key=None, *, timeout=30, retries=3, opener=None, sleep=time.sleep):
        self.api_key = api_key or os.environ.get("CMC_API_KEY", "")
        self.timeout = timeout
        self.retries = retries
        self.opener = opener or urllib.request.urlopen
        self.sleep = sleep

    def _get(self, path, params=None):
        if not self.api_key:
            raise CMCError("CMC_API_KEY is not set")
        url = f"{BASE_URL}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={
            "X-CMC_PRO_API_KEY": self.api_key,
            "Accept": "application/json",
            "User-Agent": "batavia-regime-compiler/0.2",
        })
        last_error = None
        for attempt in range(self.retries):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                status = payload.get("status", {})
                if status.get("error_code") not in (None, 0, "0"):
                    raise CMCError(f"CMC {status.get('error_code')}: {status.get('error_message')}")
                return payload.get("data", payload)
            except urllib.error.HTTPError as exc:
                last_error = CMCError(f"HTTP {exc.code} for {path}")
                if exc.code in (401, 403):
                    break
                if attempt + 1 < self.retries:
                    self.sleep(2 ** attempt)
            except (OSError, urllib.error.URLError, json.JSONDecodeError, CMCError) as exc:
                last_error = exc
                if attempt + 1 < self.retries:
                    self.sleep(2 ** attempt)
        raise CMCError(f"CMC request failed: {last_error}")

    def resolve_asset(self, symbol):
        rows = self._get("/v1/cryptocurrency/map", {"symbol": symbol.upper(), "sort": "cmc_rank"})
        matches = [row for row in rows if row.get("symbol", "").upper() == symbol.upper()]
        if not matches:
            raise CMCError(f"CMC asset not found: {symbol}")
        row = sorted(matches, key=lambda item: item.get("rank") or 10**9)[0]
        return {"id": int(row["id"]), "symbol": row["symbol"], "name": row.get("name")}

    def ohlcv_hourly(self, cmc_id, *, time_start, time_end):
        data = self._get("/v2/cryptocurrency/ohlcv/historical", {
            "id": str(cmc_id), "time_period": "hourly", "interval": "1h",
            "time_start": time_start, "time_end": time_end, "convert": "USD",
        })
        asset = _unwrap_asset(data, cmc_id)
        rows = []
        for item in asset.get("quotes", []):
            quote = item.get("quote", {}).get("USD", {})
            timestamp = item.get("time_open") or quote.get("timestamp")
            if not timestamp:
                continue
            rows.append({
                "timestamp": int(parse_utc(timestamp).timestamp() * 1000),
                "open": float(quote["open"]), "high": float(quote["high"]),
                "low": float(quote["low"]), "close": float(quote["close"]),
                "volume": float(quote.get("volume") or 0.0),
            })
        return sorted(rows, key=lambda row: row["timestamp"])

    def fear_greed_historical(self, *, limit=500, start=1):
        rows = self._get("/v3/fear-and-greed/historical", {"limit": limit, "start": start})
        return [{
            "timestamp": int(item["timestamp"]),
            "value": float(item["value"]),
            "classification": item.get("value_classification"),
        } for item in rows]


def parse_utc(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _unwrap_asset(data, cmc_id):
    if isinstance(data, dict) and "quotes" in data:
        return data
    if isinstance(data, dict):
        for key in (str(cmc_id), int(cmc_id)):
            if key in data and isinstance(data[key], dict):
                return data[key]
        for value in data.values():
            if isinstance(value, dict) and "quotes" in value:
                return value
    raise CMCError(f"Unexpected OHLCV response for CMC ID {cmc_id}")
