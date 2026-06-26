#!/usr/bin/env python3
"""Run a deterministic Batavia demo without network access or API secrets."""
import argparse
import json
from pathlib import Path

import jsonschema

from batavia.regime import Evidence, Signals, build_spec


AS_OF = "2026-06-20T10:00:00Z"


def demo_receipts():
    fresh = Evidence(
        cmc_id=1839,
        observed_at="2026-06-20T09:30:00Z",
        sources=(
            {"name": "get_crypto_technical_analysis", "observed_at": "2026-06-20T09:30:00Z"},
            {"name": "get_global_metrics_latest", "observed_at": "2026-06-20T09:30:00Z"},
        ),
    )
    stale = Evidence(
        cmc_id=1839,
        observed_at="2026-06-20T06:00:00Z",
        sources=({"name": "get_global_metrics_latest", "observed_at": "2026-06-20T06:00:00Z"},),
    )
    return [
        build_spec("BNB", Signals(62, 0.72, "normal", 0.18),
                   evidence=fresh, as_of=AS_OF, confirmation_count=3),
        build_spec("BNB", Signals(15, -0.70, "high", 0.10),
                   evidence=fresh, as_of=AS_OF, confirmation_count=1),
        build_spec("BNB", Signals(62, 0.72, "normal", None),
                   evidence=stale, as_of=AS_OF, confirmation_count=3),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print complete receipts")
    args = parser.parse_args()
    schema = json.loads(Path("schema/regime_strategy.schema.json").read_text())
    receipts = demo_receipts()
    for receipt in receipts:
        jsonschema.validate(receipt, schema)

    if args.json:
        print(json.dumps(receipts, indent=2, sort_keys=True))
        return

    print(f"{'status':<20}{'regime':<16}{'evidence':<12}{'strategy':<12}{'hash'}")
    print("-" * 80)
    for receipt in receipts:
        print(
            f"{receipt['decision_status']:<20}{receipt['regime']['label']:<16}"
            f"{receipt['evidence']['quality']:<12}{receipt['active_strategy']['style']:<12}"
            f"{receipt['evidence']['hash_sha256'][:12]}..."
        )
    print("\nAll three receipts validate against strategy contract v0.2.")


if __name__ == "__main__":
    main()
