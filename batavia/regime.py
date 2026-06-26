"""Deterministic market-regime classification and strategy-receipt compiler."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math

TRENDING_UP = "TRENDING_UP"
RANGING = "RANGING"
EUPHORIA = "EUPHORIA"
RISK_OFF = "RISK_OFF"

ACTIVE = "ACTIVE"
STAND_ASIDE = "STAND_ASIDE"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

EXTREME_GREED = 80.0
EXTREME_FEAR = 20.0
TREND_ON = 0.5
FUNDING_HOT = 0.5
MAX_EVIDENCE_AGE_SECONDS = 7200


@dataclass(frozen=True)
class Signals:
    fear_greed: float | None = None
    trend_score: float | None = None
    vol_state: str | None = None
    funding_stress: float | None = None


@dataclass(frozen=True)
class Evidence:
    cmc_id: int | None = None
    observed_at: str | None = None
    sources: tuple[dict, ...] = field(default_factory=tuple)
    missing_inputs: tuple[str, ...] = field(default_factory=tuple)


MOMENTUM = {
    "style": "momentum",
    "direction": "long_only",
    "entry": {
        "on": "fresh_close_cross_above_ema20",
        "rule": "previous close <= EMA20 and latest close > EMA20 after 3 confirmed TRENDING_UP bars",
        "side": "long",
        "execute": "next_bar_open",
    },
    "exit": {
        "stop_loss_pct": 0.025,
        "take_profit_pct": 0.08,
        "max_hold_hours": 72,
        "on": ["confirmed_regime_not_trending_up"],
        "execute_signal_exit": "next_bar_open",
    },
    "sizing": {
        "method": "volatility_target",
        "base_position_fraction": 0.15,
        "reference_atr_pct": 0.02,
        "min_position_fraction": 0.05,
        "max_position_fraction": 0.25,
    },
}


def _cash_strategy(reason: str) -> dict:
    return {
        "style": "cash",
        "direction": "long_only",
        "entry": {"on": "none", "rule": reason, "side": "flat", "execute": "none"},
        "exit": {
            "stop_loss_pct": 0.0,
            "take_profit_pct": 0.0,
            "max_hold_hours": 0,
            "on": ["exit_existing_position_at_next_bar_open"],
            "execute_signal_exit": "next_bar_open",
        },
        "sizing": {"method": "fixed_fraction", "max_position_fraction": 0.0},
    }


PLAYBOOK = {
    TRENDING_UP: MOMENTUM,
    RANGING: _cash_strategy("No confirmed directional edge; preserve optionality in cash."),
    EUPHORIA: _cash_strategy("Extreme greed and crowded funding invalidate new long risk."),
    RISK_OFF: _cash_strategy("Fear or a confirmed downtrend invalidates long-only participation."),
}

COSTS = {"fee_per_side_pct": 0.05, "intrabar_conflict_policy": "stop_first"}
VALIDATION = {
    "method": "Three chronological windows; active strategies share fills, sizing, fees, stops, targets, and max hold.",
    "candidates": [
        "router", "trend_cash", "sentiment_momentum", "momentum",
        "mean_reversion", "buy_hold", "cash",
    ],
    "selection_gate": "Positive median window return and profitable on at least 4 of 7 assets.",
}
AGENT_HUB = {
    "skill": "batavia-regime-compiler",
    "surfaces": ["skill", "mcp", "cli_replay"],
    "required_mcp_tools": [
        "search_cryptos",
        "get_crypto_quotes_latest",
        "get_crypto_technical_analysis",
        "get_global_metrics_latest",
        "get_global_crypto_derivatives_metrics",
    ],
    "optional_research_tools": ["get_crypto_ohlcv_historical", "get_fear_and_greed_historical"],
    "provenance_contract": "Every receipt records the CMC tool names, observation timestamps, freshness gate, and evidence hash used for the decision.",
    "x402_policy": "No paid call is required for the offline demo; live Agent Hub runs may use x402-enabled CMC tool access without changing the receipt schema.",
}


def classify(sig: Signals) -> tuple[str, dict, str]:
    """Classify one evidence snapshot. Multi-bar confirmation is applied by the engine."""
    fg = 50.0 if sig.fear_greed is None else float(sig.fear_greed)
    ts = 0.0 if sig.trend_score is None else float(sig.trend_score)
    fs = 0.0 if sig.funding_stress is None else float(sig.funding_stress)
    if fg >= EXTREME_GREED and sig.funding_stress is not None and fs >= FUNDING_HOT:
        label = EUPHORIA
        rationale = f"F&G {fg:.0f} and funding stress {fs:+.2f} indicate crowded long risk."
    elif fg <= EXTREME_FEAR:
        label = RISK_OFF
        rationale = f"F&G {fg:.0f} is an immediate long-risk invalidation."
    elif ts >= TREND_ON:
        label = TRENDING_UP
        rationale = f"Trend score {ts:+.2f} supports long momentum, subject to confirmation."
    elif ts <= -TREND_ON:
        label = RISK_OFF
        rationale = f"Trend score {ts:+.2f} is incompatible with long-only participation."
    else:
        label = RANGING
        rationale = f"Trend score {ts:+.2f} has no confirmed directional edge."
    scores = {
        "fear_greed": None if sig.fear_greed is None else round(fg, 1),
        "trend_score": None if sig.trend_score is None else round(ts, 3),
        "vol_state": sig.vol_state,
        "funding_stress": None if sig.funding_stress is None else round(fs, 3),
    }
    return label, scores, rationale


def evidence_quality(sig: Signals, evidence: Evidence, as_of: str | None) -> tuple[str, list[str], bool]:
    missing = set(evidence.missing_inputs)
    if not as_of:
        missing.add("as_of")
    if evidence.cmc_id is None:
        missing.add("cmc_id")
    if not evidence.sources:
        missing.add("sources")
    for source in evidence.sources:
        if not source.get("name"):
            missing.add("source_name")
        observed_at = source.get("observed_at")
        if not observed_at:
            missing.add("source_observed_at")
        else:
            try:
                _parse_time(str(observed_at))
            except ValueError:
                missing.add("valid_source_observed_at")
    required = {
        "fear_greed": sig.fear_greed,
        "trend_score": sig.trend_score,
        "vol_state": sig.vol_state,
    }
    missing.update(k for k, value in required.items() if value is None)
    stale = False
    if evidence.observed_at and as_of:
        try:
            observed = _parse_time(evidence.observed_at)
            assessed = _parse_time(as_of)
            age = (assessed - observed).total_seconds()
            stale = age > MAX_EVIDENCE_AGE_SECONDS
            if age < -300:
                missing.add("observed_at_not_in_future")
        except ValueError:
            missing.add("valid_observed_at")
    elif not evidence.observed_at:
        missing.add("observed_at")
    quality = "complete" if not missing and not stale else ("stale" if stale else "incomplete")
    return quality, sorted(missing), stale


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _receipt_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _normalized_sources(sources: tuple[dict, ...]) -> list[dict]:
    return [{"name": source.get("name", ""), "observed_at": source.get("observed_at")}
            for source in sources]


def build_spec(
    symbol: str,
    sig: Signals,
    *,
    evidence: Evidence | None = None,
    as_of: str | None = None,
    confirmation_count: int = 1,
) -> dict:
    """Compile normalized CMC evidence into a deterministic v0.2 strategy receipt."""
    evidence = evidence or Evidence()
    _validate_inputs(sig, evidence, confirmation_count)
    label, scores, rationale = classify(sig)
    quality, missing, stale = evidence_quality(sig, evidence, as_of)
    sources = _normalized_sources(evidence.sources)
    if missing or stale:
        status = INSUFFICIENT_DATA
        active = _cash_strategy("Required market evidence is missing or stale.")
    elif label == TRENDING_UP and confirmation_count >= 3:
        status = ACTIVE
        active = MOMENTUM
    else:
        status = STAND_ASIDE
        active = PLAYBOOK[label]

    hash_input = {
        "version": "0.2.0",
        "symbol": symbol.upper(),
        "as_of": as_of,
        "signals": asdict(sig),
        "evidence": {
            "cmc_id": evidence.cmc_id,
            "observed_at": evidence.observed_at,
            "sources": sources,
            "missing_inputs": list(evidence.missing_inputs),
        },
        "agent_hub": AGENT_HUB,
        "confirmation_count": confirmation_count,
    }
    return {
        "name": "batavia-regime-compiler",
        "version": "0.2.0",
        "as_of": as_of,
        "asset": {"symbol": symbol.upper(), "cmc_id": evidence.cmc_id},
        "timeframe": "1h",
        "decision_status": status,
        "evidence": {
            "quality": quality,
            "observed_at": evidence.observed_at,
            "stale": stale,
            "missing_inputs": missing,
            "sources": sources,
            "hash_sha256": _receipt_hash(hash_input),
        },
        "agent_hub": deepcopy(AGENT_HUB),
        "regime": {
            "label": label,
            "confirmation_count": confirmation_count,
            "required_confirmation_bars": 3,
            "scores": scores,
            "rationale": rationale,
        },
        "active_strategy": {"regime": label, **deepcopy(active)},
        "regime_playbook": deepcopy(PLAYBOOK),
        "invalidation_conditions": [
            "confirmed regime is no longer TRENDING_UP",
            "Fear & Greed is at or below 20",
            "Fear & Greed is at or above 80 while funding_stress is at or above 0.5",
            "required evidence is older than 2 hours",
        ],
        "costs": COSTS,
        "validation": VALIDATION,
        "alternatives_rejected": _alternatives(label, status),
    }


def _validate_inputs(sig: Signals, evidence: Evidence, confirmation_count: int) -> None:
    ranges = {
        "fear_greed": (sig.fear_greed, 0.0, 100.0),
        "trend_score": (sig.trend_score, -1.0, 1.0),
        "funding_stress": (sig.funding_stress, -1.0, 1.0),
    }
    for name, (value, lower, upper) in ranges.items():
        if value is not None and (not math.isfinite(float(value)) or not lower <= float(value) <= upper):
            raise ValueError(f"{name} must be finite and between {lower} and {upper}")
    if sig.vol_state not in (None, "low", "normal", "high"):
        raise ValueError("vol_state must be low, normal, high, or None")
    if not isinstance(confirmation_count, int) or confirmation_count < 0:
        raise ValueError("confirmation_count must be a non-negative integer")
    if evidence.cmc_id is not None and evidence.cmc_id <= 0:
        raise ValueError("cmc_id must be positive")


def _alternatives(label: str, status: str) -> list[dict]:
    alternatives = []
    if label != RANGING:
        alternatives.append({"strategy": "mean_reversion", "reason": "Market is not classified as ranging."})
    elif status != ACTIVE:
        alternatives.append({"strategy": "mean_reversion", "reason": "Retained as a research baseline, not an active playbook rule."})
    if status != ACTIVE:
        alternatives.append({"strategy": "momentum", "reason": "Evidence gate does not authorize a new position."})
    return alternatives
