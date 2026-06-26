#!/usr/bin/env python3
"""Fail when committed validation figures cannot be reproduced exactly."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backtest.render_results import render  # noqa: E402
from backtest.validate_basket import validate  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/cmc")
    parser.add_argument("--results", default="results/validation.json")
    parser.add_argument("--document", default="docs/RESULTS.md")
    args = parser.parse_args()

    committed = json.loads(Path(args.results).read_text())
    reproduced = validate(args.data_dir, committed["symbols"])
    if reproduced != committed:
        raise SystemExit("validation JSON differs from a fresh engine run")
    expected_document = render(committed)
    if Path(args.document).read_text() != expected_document:
        raise SystemExit("docs/RESULTS.md differs from rendered validation JSON")
    print("OK validation JSON and documentation reproduce exactly")


if __name__ == "__main__":
    main()
