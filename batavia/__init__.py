"""Batavia — a regime-detection CMC Strategy Skill (BNB Hack, Track 2).

Reads the market's "season" from CoinMarketCap data and emits the backtestable
strategy spec that season calls for — including the seasons where the right move
is to hold cash.
"""
from .regime import (
    Signals, classify, build_spec, PLAYBOOK, PORTFOLIO_RISK,
    TRENDING_UP, RANGING, EUPHORIA, RISK_OFF,
)
from .indicators import derive_signals

__all__ = [
    "Signals", "classify", "build_spec", "derive_signals",
    "PLAYBOOK", "PORTFOLIO_RISK",
    "TRENDING_UP", "RANGING", "EUPHORIA", "RISK_OFF",
]
__version__ = "0.1.0"
