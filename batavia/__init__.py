"""Batavia: CoinMarketCap evidence in, auditable strategy receipt out."""
from .regime import (
    Evidence, Signals, classify, build_spec, PLAYBOOK,
    ACTIVE, STAND_ASIDE, INSUFFICIENT_DATA,
    TRENDING_UP, RANGING, EUPHORIA, RISK_OFF,
)
from .indicators import derive_signals

__all__ = [
    "Evidence", "Signals", "classify", "build_spec", "derive_signals",
    "PLAYBOOK", "ACTIVE", "STAND_ASIDE", "INSUFFICIENT_DATA",
    "TRENDING_UP", "RANGING", "EUPHORIA", "RISK_OFF",
]
__version__ = "0.2.0"
