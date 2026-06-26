"""Portable pure-Python indicators used by both compiler and backtester."""
from __future__ import annotations

from math import sqrt
from .regime import Signals


def ema(values, period):
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [None] * len(values)
    value = float(values[0])
    for i, current in enumerate(values):
        value = float(current) if i == 0 else float(current) * k + value * (1 - k)
        if i >= period - 1:
            out[i] = value
    return out


def rsi(closes, period=14):
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def _rsi_value(avg_gain, avg_loss):
    if avg_gain == 0 and avg_loss == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def true_ranges(highs, lows, closes):
    out = []
    for i in range(len(closes)):
        previous = closes[i - 1] if i else closes[i]
        out.append(max(highs[i] - lows[i], abs(highs[i] - previous), abs(lows[i] - previous)))
    return out


def atr_series(highs, lows, closes, period=14):
    out = [None] * len(closes)
    if len(closes) < period:
        return out
    trs = true_ranges(highs, lows, closes)
    value = sum(trs[:period]) / period
    out[period - 1] = value
    for i in range(period, len(closes)):
        value = (value * (period - 1) + trs[i]) / period
        out[i] = value
    return out


def atr_pct(highs, lows, closes, period=14):
    values = atr_series(highs, lows, closes, period)
    if not values or values[-1] is None or not closes[-1]:
        return None
    return values[-1] / closes[-1]


def bollinger(closes, period=20, deviations=2.0):
    middle = [None] * len(closes)
    upper = [None] * len(closes)
    lower = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        mean = sum(window) / period
        variance = sum((value - mean) ** 2 for value in window) / period
        sd = sqrt(variance)
        middle[i] = mean
        upper[i] = mean + deviations * sd
        lower[i] = mean - deviations * sd
    return upper, middle, lower


def trend_score(close, ema_fast, ema_slow, full_band=0.03):
    if ema_fast is None or ema_slow is None or not ema_slow:
        return 0.0
    score = max(-1.0, min(1.0, ((ema_fast - ema_slow) / ema_slow) / full_band))
    if close < ema_fast and score > 0:
        score *= 0.5
    elif close > ema_fast and score < 0:
        score *= 0.5
    return round(score, 3)


def vol_state(atr_fraction, low=0.015, high=0.04):
    if atr_fraction is None:
        return None
    if atr_fraction < low:
        return "low"
    if atr_fraction > high:
        return "high"
    return "normal"


def derive_signals(highs, lows, closes, fear_greed=None, funding_stress=None):
    if not closes:
        return Signals(fear_greed=fear_greed, funding_stress=funding_stress)
    fast, slow = ema(closes, 20), ema(closes, 50)
    score = trend_score(closes[-1], fast[-1], slow[-1])
    volatility = vol_state(atr_pct(highs, lows, closes))
    return Signals(fear_greed=fear_greed, trend_score=score,
                   vol_state=volatility, funding_stress=funding_stress)
