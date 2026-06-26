#!/usr/bin/env python3
"""Render the committed validation JSON into the human-readable results page."""
import argparse
import json
from pathlib import Path


def render(report):
    lines = [
        "# Validation Results", "",
        "All figures below are generated from `results/validation.json`. The engine uses next-bar-open",
        "entries, stop-first intrabar fills, entry/exit fees, mark-to-market equity, and final-bar liquidation.",
        "", "## Candidate summary", "",
        "| Policy | Median window return | Median maxDD | Selection score | Profitable assets |",
        "|---|---:|---:|---:|---:|",
    ]
    for policy, row in report["summary"].items():
        lines.append(
            f"| `{policy}` | {row['median_window_return_pct']:+.2f}% | "
            f"{row['median_max_drawdown_pct']:.2f}% | {row['selection_score']:+.2f} | "
            f"{row['profitable_assets']}/{row['assets']} |"
        )
    selection = report["selection"]
    lines += [
        "", "## Selection", "",
        f"Selected policy: **`{selection['selected']}`**.", "",
        f"Eligible regime-aware candidates: {', '.join(selection['eligible']) if selection['eligible'] else 'none'}.",
        "Fallback was used." if selection["fallback_used"] else "The selected policy passed the published gate.",
        "", "The gate requires a positive median chronological-window return and profitability on at least four of seven assets.",
        "", "## Per-asset, per-window results", "",
    ]
    for symbol in report["symbols"]:
        lines += [f"### {symbol}", "", "| Policy | W1 | W2 | W3 |", "|---|---:|---:|---:|"]
        for policy, windows in report["detail"][symbol].items():
            values = " | ".join(f"{window['total_return_pct']:+.2f}%" for window in windows)
            lines.append(f"| `{policy}` | {values} |")
        lines.append("")
    lines += [
        "## Limits", "",
        "- Historical CoinMarketCap funding is not assumed; `funding_stress` is neutral in this study.",
        "- The EUPHORIA branch is covered by deterministic synthetic tests, not claimed as historical evidence.",
        "- Past performance does not guarantee future results.", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="results/validation.json")
    parser.add_argument("--output", default="docs/RESULTS.md")
    args = parser.parse_args()
    report = json.loads(Path(args.input).read_text())
    Path(args.output).write_text(render(report))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
