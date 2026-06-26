#!/usr/bin/env python3
"""Visible smoke test for the four market states and evidence abstention."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from batavia.regime import Evidence, Signals, build_spec


def main():
    evidence = Evidence(
        1839,
        "2026-06-20T09:30:00Z",
        ({"name": "synthetic_test", "observed_at": "2026-06-20T09:30:00Z"},),
    )
    cases = [
        ("TRENDING_UP", Signals(60, 0.8, "normal", 0.1), 3, "ACTIVE"),
        ("RANGING", Signals(50, 0.0, "low", 0.0), 3, "STAND_ASIDE"),
        ("EUPHORIA", Signals(85, 0.9, "high", 0.8), 1, "STAND_ASIDE"),
        ("RISK_OFF", Signals(15, -0.8, "high", -0.2), 1, "STAND_ASIDE"),
    ]
    for expected, signals, count, status in cases:
        receipt = build_spec("BNB", signals, evidence=evidence,
                             as_of="2026-06-20T10:00:00Z", confirmation_count=count)
        got = receipt["regime"]["label"]
        assert got == expected and receipt["decision_status"] == status
        print(f"OK {expected:<12} -> {status}")
    abstain = build_spec("BNB", Signals(), as_of="2026-06-20T10:00:00Z")
    assert abstain["decision_status"] == "INSUFFICIENT_DATA"
    print("OK missing data -> INSUFFICIENT_DATA")


if __name__ == "__main__":
    main()
