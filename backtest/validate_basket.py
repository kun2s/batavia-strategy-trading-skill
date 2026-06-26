#!/usr/bin/env python3
"""Compare all policies across assets and three chronological windows."""
import argparse
import json
from pathlib import Path
import statistics
import sys
from math import prod

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backtest.engine import (  # noqa: E402
    POLICIES, align_market_data, chronological_windows, load_market_csv, run,
)

DEFAULT = ["BTC", "ETH", "BNB", "SOL", "AVAX", "LINK", "DOGE"]
CANDIDATES = ["router", "trend_cash", "sentiment_momentum"]


def validate(data_dir, symbols):
    loaded = {
        symbol: load_market_csv(Path(data_dir) / f"{symbol.lower()}_1h.csv")
        for symbol in symbols
    }
    datasets = align_market_data(loaded)
    detail = {}
    for symbol in symbols:
        data = datasets[symbol]
        windows = chronological_windows(len(data))
        detail[symbol] = {
            policy: [_compact(run(data, policy, start=start, end=end)) for start, end in windows]
            for policy in POLICIES
        }
    summary = {}
    for policy in POLICIES:
        asset_returns = []
        window_returns = []
        drawdowns = []
        ratios = []
        for symbol in symbols:
            results = detail[symbol][policy]
            values = [result["total_return_pct"] for result in results]
            asset_returns.append((prod(1 + value / 100 for value in values) - 1) * 100)
            window_returns.extend(values)
            drawdowns.extend(result["max_drawdown_pct"] for result in results)
            ratios.extend(result["return_over_drawdown"] for result in results)
        summary[policy] = {
            "median_window_return_pct": round(statistics.median(window_returns), 4),
            "median_max_drawdown_pct": round(statistics.median(drawdowns), 4),
            "median_return_over_drawdown": round(statistics.median(ratios), 4),
            "profitable_assets": sum(value > 0 for value in asset_returns),
            "assets": len(symbols),
        }
        median_return = summary[policy]["median_window_return_pct"]
        median_drawdown = summary[policy]["median_max_drawdown_pct"]
        if median_drawdown:
            selection_score = median_return / median_drawdown
        elif median_return > 0:
            selection_score = 1_000_000_000.0
        else:
            selection_score = 0.0
        summary[policy]["selection_score"] = round(selection_score, 4)
    eligible = [policy for policy in CANDIDATES
                if summary[policy]["median_window_return_pct"] > 0
                and summary[policy]["profitable_assets"] >= 4]
    selected = max(eligible, key=lambda policy: summary[policy]["selection_score"]) if eligible else "sentiment_momentum"
    mean_reversion_eligible = (
        summary["mean_reversion"]["median_window_return_pct"] > 0
        and summary["mean_reversion"]["profitable_assets"] >= 4
    )
    return {"symbols": symbols, "windows": 3,
            "common_bars": len(next(iter(datasets.values()))),
            "time_start": next(iter(datasets.values())).timestamps[0],
            "time_end": next(iter(datasets.values())).timestamps[-1],
            "summary": summary,
            "selection": {"eligible": eligible, "selected": selected,
                          "fallback_used": not bool(eligible),
                          "mean_reversion_eligible": mean_reversion_eligible},
            "detail": detail}


def _compact(result):
    return {key: value for key, value in result.items() if key != "trades_detail"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbols", nargs="*", default=DEFAULT)
    parser.add_argument("--data-dir", default="data/cmc")
    parser.add_argument("--out")
    args = parser.parse_args()
    report = validate(args.data_dir, [symbol.upper() for symbol in args.symbols])
    print(f"{'policy':<22}{'median ret':>12}{'median DD':>12}{'select score':>14}{'profitable':>13}")
    print("-" * 73)
    for policy, row in report["summary"].items():
        profitable = f"{row['profitable_assets']}/{row['assets']}"
        print(f"{policy:<22}{row['median_window_return_pct']:>11.2f}%"
              f"{row['median_max_drawdown_pct']:>11.2f}%{row['selection_score']:>14.2f}"
              f"{profitable:>13}")
    print(f"selected: {report['selection']['selected']} (fallback={report['selection']['fallback_used']})")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
