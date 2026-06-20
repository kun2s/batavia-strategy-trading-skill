"""Pure-Python indicators + signal derivation. No numpy/pandas dependency so the
skill stays light and portable (a CMC agent can run it inline).

These turn a window of OHLCV bars into the small `Signals` bundle the regime
classifier needs. Sentiment (Fear & Greed) and funding_stress come from CMC
endpoints, not from price — pass them in; price gives trend_score and vol_state.
"""
from __future__ import annotations
from .regime import Signals


def ema(values, period):
    """Exponential moving average -> list aligned to `values` (None until warm)."""
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [None] * len(values)
    avg = values[0]
    for i, v in enumerate(values):
        avg = v if i == 0 else (v * k + avg * (1 - k))
        out[i] = avg if i >= period - 1 else None
    return out


def rsi(closes, period=14):
    """Wilder's RSI -> list aligned to `closes` (None until warm)."""
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    avg_g, avg_l = gains / period, losses / period
    out[period] = 100.0 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l)
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_g = (avg_g * (period - 1) + max(d, 0.0)) / period
        avg_l = (avg_l * (period - 1) + max(-d, 0.0)) / period
        out[i] = 100.0 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l)
    return out


def atr_pct(highs, lows, closes, period=14):
    """ATR as a fraction of price (e.g. 0.02 = 2%). Last value, or None if cold."""
    n = len(closes)
    if n <= period:
        return None
    trs = []
    for i in range(1, n):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr / closes[-1] if closes[-1] else None


def trend_score(close, ema_fast, ema_slow, full_band=0.03):
    """Map EMA alignment to [-1, 1]. Driven by the EMA20/EMA50 spread, dampened
    when price sits on the wrong side of the fast EMA (early/failing trend)."""
    if ema_fast is None or ema_slow is None or not ema_slow:
        return 0.0
    spread = (ema_fast - ema_slow) / ema_slow
    score = max(-1.0, min(1.0, spread / full_band))
    if close < ema_fast and score > 0:
        score *= 0.5   # price below fast EMA weakens a nominal uptrend
    if close > ema_fast and score < 0:
        score *= 0.5
    return round(score, 3)


def vol_state(atr_fraction, low=0.015, high=0.04):
    """1h ATR% bucket. <1.5% calm, >4% hot (defaults; see METHODOLOGY.md)."""
    if atr_fraction is None:
        return "normal"
    if atr_fraction < low:
        return "low"
    if atr_fraction > high:
        return "high"
    return "normal"


def derive_signals(highs, lows, closes, fear_greed=50.0, funding_stress=0.0):
    """OHLC window (+ external sentiment/funding) -> Signals for the classifier."""
    ef = ema(closes, 20)
    es = ema(closes, 50)
    ts = trend_score(closes[-1], ef[-1], es[-1])
    vs = vol_state(atr_pct(highs, lows, closes))
    return Signals(fear_greed=fear_greed, trend_score=ts,
                   vol_state=vs, funding_stress=funding_stress)
