"""Regime classification + the regime -> strategy playbook.

Batavia treats a market as moving through seasons:
TRENDING_UP, RANGING, EUPHORIA, and RISK_OFF. Each season calls for a different
strategy — and two of them call for *standing aside*. This module turns a small
set of CoinMarketCap-derived signals into (a) a regime label and (b) the fully
specified, backtestable sub-strategy that season calls for.

Design stance: the metric that decides a live-PnL competition is drawdown, not
headline return ("most profit without blowing up"). The single largest drawdown
saver is refusing to trade in the wrong season. So the most important output of
this skill is often `entry.on == "none"`.
"""
from __future__ import annotations
from dataclasses import dataclass

# ── regime labels ──
TRENDING_UP = "TRENDING_UP"
RANGING = "RANGING"
EUPHORIA = "EUPHORIA"
RISK_OFF = "RISK_OFF"

# ── classifier thresholds (documented; tune in METHODOLOGY.md) ──
EXTREME_GREED = 80.0   # Fear & Greed >= this = crowd euphoria
EXTREME_FEAR = 20.0    # Fear & Greed <= this = capitulation
TREND_ON = 0.5         # |trend_score| >= this = a regime-defining trend
FUNDING_HOT = 0.5      # normalized perp funding >= this = crowded longs


@dataclass
class Signals:
    """The minimal regime inputs. All optional; sensible neutral defaults so the
    classifier degrades gracefully when a CMC surface is unavailable."""
    fear_greed: float = 50.0      # CMC Fear & Greed Index, 0..100
    trend_score: float = 0.0      # -1..1, EMA alignment (price vs EMA20/EMA50)
    vol_state: str = "normal"     # "low" | "normal" | "high"  (from ATR%)
    funding_stress: float = 0.0   # -1..1, normalized perp funding (+ = crowded longs)


def classify(sig: Signals):
    """-> (label, scores, rationale). Deterministic decision tree, ordered by
    priority: capital-preservation overrides (euphoria, fear) come before the
    trend/range split. Long-only universe (spot BEP-20) — a downtrend maps to
    RISK_OFF (stand aside), never to a short."""
    fg, ts, fs = sig.fear_greed, sig.trend_score, sig.funding_stress
    if fg >= EXTREME_GREED and fs >= FUNDING_HOT:
        label = EUPHORIA
        why = (f"Extreme greed (F&G {fg:.0f}) with crowded long funding "
               f"({fs:+.2f}) — blow-off risk. Stand down, no new longs.")
    elif fg <= EXTREME_FEAR:
        # Fear is checked before trend: capital preservation outranks chasing a
        # rally into a fearful tape. A "be greedy when fearful" variant (trend
        # before fear) was tried and REJECTED on real data — see METHODOLOGY §8.
        label = RISK_OFF
        why = (f"Extreme fear (F&G {fg:.0f}) — preserve capital, "
               f"do not catch a falling knife.")
    elif ts >= TREND_ON:
        label = TRENDING_UP
        why = (f"Clear uptrend (trend {ts:+.2f}) without euphoric froth — "
               f"ride momentum with a trailing exit.")
    elif ts <= -TREND_ON:
        label = RISK_OFF
        why = (f"Downtrend (trend {ts:+.2f}) on a spot/long-only universe — "
               f"stand aside; we cannot profit short here.")
    else:
        label = RANGING
        why = (f"No dominant trend (trend {ts:+.2f}), calm sentiment — "
               f"fade oversold extremes for a quick reversion.")
    scores = {
        "fear_greed": round(fg, 1),
        "trend_score": round(ts, 3),
        "vol_state": sig.vol_state,
        "funding_stress": round(fs, 3),
    }
    return label, scores, why


# ── the playbook: one fully-specified, backtestable sub-strategy per season ──
PLAYBOOK = {
    TRENDING_UP: {
        "style": "momentum",
        "direction": "long_only",
        "entry": {
            "on": "trend_continuation",
            "rule": "close > EMA20 while trend_score >= 0.5",
            "side": "long",
        },
        "exit": {
            "stop_loss_pct": 0.025,
            "take_profit_pct": 0.08,
            "max_hold_hours": 72,
            "trail": {"activate_at_pct": 0.04, "trail_pct": 0.03},
            "on": ["trend_flip_down"],
        },
        "sizing": {
            "method": "volatility_target",
            "base_risk": 0.02, "reference_atr_pct": 0.02,
            "min_risk": 0.005, "max_risk": 0.04,
            "max_position_fraction": 0.34,
        },
    },
    RANGING: {
        "style": "mean_reversion",
        "direction": "long_only",
        "entry": {
            "on": "oversold_reversion",
            "rule": "RSI(14) < 30 and close <= lower_bollinger(20, 2)",
            "side": "long",
        },
        "exit": {
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.03,
            "max_hold_hours": 24,
            "on": ["RSI(14) > 55"],
        },
        "sizing": {
            "method": "fixed_fraction",
            "base_risk": 0.015,
            "max_position_fraction": 0.25,
        },
    },
    EUPHORIA: {
        "style": "defensive_no_new_risk",
        "direction": "long_only",
        "entry": {
            "on": "none",
            "rule": "no new longs into extreme greed + hot funding",
            "side": "flat",
        },
        "exit": {
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.04,
            "max_hold_hours": 12,
            "note": "manage/trim existing positions only; tighten stops",
        },
        "sizing": {"method": "fixed_fraction", "base_risk": 0.0, "max_position_fraction": 0.0},
    },
    RISK_OFF: {
        "style": "cash",
        "direction": "long_only",
        "entry": {
            "on": "none",
            "rule": "hold the quote/stable asset; re-enter only when the regime changes",
            "side": "flat",
        },
        "exit": {
            "stop_loss_pct": 0.015,
            "take_profit_pct": 0.0,
            "max_hold_hours": 0,
            "note": "close risk and sit in cash",
        },
        "sizing": {"method": "fixed_fraction", "base_risk": 0.0, "max_position_fraction": 0.0},
    },
}

# ── portfolio-level guardrails (motivated by the competition gate, not by any
#    single strategy). Halt new risk at 20% drawdown: a 10-point buffer under a
#    ~30% disqualification gate. ──
PORTFOLIO_RISK = {
    "drawdown_derisk_start": 0.12,
    "drawdown_halt": 0.20,
    "drawdown_resume": 0.14,
    "max_concurrent": 3,
    "min_trades_per_day": 1,
    "note": "Halt at 20% DD = a 10-point buffer below a ~30% gate. The router's "
            "RISK_OFF/EUPHORIA seasons are the first line of drawdown defense.",
}

DEFAULT_DATA_INPUTS = [
    "get_crypto_quotes_latest",               # price/volume -> 1h candles, trend & vol
    "get_crypto_technical_analysis",          # RSI/MACD/EMA -> trend_score, vol_state
    "get_global_crypto_derivatives_metrics",  # funding/OI -> funding_stress
    "get_fear_and_greed_latest",              # sentiment regime
]

def build_spec(symbol, sig: Signals, as_of=None, data_inputs=None):
    """Assemble the full, schema-valid strategy spec for `symbol` given the
    detected regime. `as_of` is an ISO timestamp string (passed in by the
    caller — this module never reads the clock, to stay deterministic)."""
    label, scores, why = classify(sig)
    active = PLAYBOOK[label]
    return {
        "name": "batavia-regime-router",
        "version": "0.1",
        "as_of": as_of,
        "symbol": symbol.upper(),
        "timeframe": "1h",
        "direction": "long_only",
        "regime": {"label": label, "scores": scores, "rationale": why},
        "active_strategy": {"regime": label, **active},
        "regime_playbook": PLAYBOOK,
        "risk": PORTFOLIO_RISK,
        "costs": {"fee_per_side_pct": 0.05},
        "data_inputs": list(data_inputs) if data_inputs else DEFAULT_DATA_INPUTS,
        "validation": VALIDATION_FRAMEWORK,
    }


VALIDATION_FRAMEWORK = {
    "method": ("Walk-forward, regime-segmented. Compare the router against three "
               "static baselines (always-momentum, always-mean-reversion, "
               "buy-and-hold) on the same out-of-sample window. Primary metric: "
               "portfolio max drawdown (the gate). Secondary: total return and "
               "per-regime expectancy."),
    "hypothesis": ("Switching beats any single static signal: momentum gets chopped "
                   "up in ranging seasons and caught in blow-off tops, while "
                   "mean-reversion is run over by strong trends. Standing flat in "
                   "RISK_OFF/EUPHORIA is the single largest drawdown saver."),
    "baselines": ["always_momentum", "always_mean_reversion", "buy_and_hold"],
    "status": ("Validated on real data (docs/RESULTS.md): ETH 1h, 3000 bars "
               "Feb-Jun 2026. In a -12.5% buy-hold window the router lost only "
               "-4.6% (maxDD 4.6%) — but a regime-blind momentum baseline beat it "
               "on return that window. Edge is drawdown-adjusted robustness, not "
               "single-window return; multi-asset validation is the next step. "
               "No fabricated numbers — reproduce via backtest/fetch_data.py."),
}
