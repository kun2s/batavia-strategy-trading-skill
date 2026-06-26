from datetime import datetime, timezone
import io
import json
import unittest
import urllib.error

from batavia.cmc import CMCClient, CMCError, parse_utc
from backtest.fetch_cmc import closed_interval, sentiment_as_of


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): return False


class CMCTests(unittest.TestCase):
    def test_parse_utc_never_uses_local_timezone(self):
        parsed = parse_utc("2026-06-20T01:00:00Z")
        self.assertEqual(parsed.tzinfo, timezone.utc)
        self.assertEqual(parsed.hour, 1)

    def test_resolve_asset_is_id_first(self):
        payload = {"status": {"error_code": 0}, "data": [
            {"id": 999, "symbol": "BNB", "name": "Other", "rank": 99},
            {"id": 1839, "symbol": "BNB", "name": "BNB", "rank": 4},
        ]}
        client = CMCClient("key", opener=lambda *a, **k: Response(json.dumps(payload).encode()))
        self.assertEqual(client.resolve_asset("bnb")["id"], 1839)

    def test_ohlcv_response_is_normalized(self):
        payload = {"status": {"error_code": 0}, "data": {"1839": {"quotes": [{
            "time_open": "2026-06-20T09:00:00Z",
            "quote": {"USD": {
                "open": 600, "high": 610, "low": 590, "close": 605,
                "volume": 1234, "timestamp": "2026-06-20T09:59:59Z",
            }},
        }]}}}
        client = CMCClient("key", opener=lambda *a, **k: Response(json.dumps(payload).encode()))
        rows = client.ohlcv_hourly(
            1839, time_start="2026-06-20T09:00:00Z", time_end="2026-06-20T10:00:00Z"
        )
        self.assertEqual(rows[0]["timestamp"], 1_781_946_000_000)
        self.assertEqual(rows[0]["close"], 605.0)
        self.assertEqual(rows[0]["volume"], 1234.0)

    def test_retry_is_bounded(self):
        calls = []
        def failing(*args, **kwargs):
            calls.append(1)
            raise urllib.error.URLError("offline")
        client = CMCClient("key", retries=3, opener=failing, sleep=lambda _: None)
        with self.assertRaises(CMCError):
            client.resolve_asset("BNB")
        self.assertEqual(len(calls), 3)

    def test_auth_denial_is_not_retried(self):
        calls = []
        def forbidden(request, **kwargs):
            calls.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)
        client = CMCClient("key", retries=3, opener=forbidden, sleep=lambda _: None)
        with self.assertRaisesRegex(CMCError, "HTTP 403.*cryptocurrency/map"):
            client.resolve_asset("BNB")
        self.assertEqual(len(calls), 1)

    def test_sentiment_join_never_looks_forward(self):
        rows = [{"timestamp": 1_000}, {"timestamp": 2_000}, {"timestamp": 3_000}]
        observations = [
            {"timestamp": 2, "value": 25.0},
            {"timestamp": 3, "value": 75.0},
        ]
        self.assertEqual(sentiment_as_of(rows, observations), [None, 25.0, 75.0])

    def test_current_open_candle_is_excluded(self):
        start = datetime(2026, 6, 20, 8, tzinfo=timezone.utc)
        end = datetime(2026, 6, 20, 10, tzinfo=timezone.utc)
        rows = [{"timestamp": int(hour.timestamp() * 1000)} for hour in (
            start, datetime(2026, 6, 20, 9, tzinfo=timezone.utc), end,
        )]
        self.assertEqual(len(closed_interval(rows, start, end)), 2)


if __name__ == "__main__":
    unittest.main()
