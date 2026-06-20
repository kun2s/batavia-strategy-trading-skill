#!/usr/bin/env python3
"""Batavia backtest harness — run the regime router on OHLCV and report metrics.

This is the validation engine referenced by the spec's `validation` block. It is
deliberately simple and transparent (long-only, one position at a time) so the
result is auditable, not a black box. It ships NO baked numbers: you run it on
your own data, or run `--selftest` to verify the router's mechanics on synthetic
seasons.

Usage:
  python backtest/regime_router.py --selftest
  python backtest/regime_router.py --csv data/eth_1h.csv [--context data/ctx.csv]

CSV (price):   header with high,low,close   (timestamp/open/volume optional)
CSV (context): header with fear_greed,funding (one row per price bar; optional)
"""
import argparse
import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from batavia.regime import (classify, PLAYBOOK, TRENDING_UP, RANGING,  # noqa: E402
                            EUPHORIA, RISK_OFF, Signals)
from batavia.indicators import ema, rsi, atr_pct, trend_score, vol_state  # noqa: E402

WARMUP = 50
FEE = 0.0005  # 0.05% per side, matches the spec's cost assumption


def _signals_at(highs, lows, closes, fg, funding):
    ef, es = ema(closes, 20), ema(closes, 50)
    ts = trend_score(closes[-1], ef[-1], es[-1])
    vs = vol_state(atr_pct(highs, lows, closes))
    return Signals(fear_greed=fg, trend_score=ts, vol_state=vs, funding_stress=funding)


def run(highs, lows, closes, fgs, fundings, mode="router"):
    """Walk bar by bar; long-only, one position. `mode` selects the policy:
      'router'         -> switch sub-strategy by detected regime (Batavia)
      'momentum'       -> baseline: always momentum, regime-blind
      'mean_reversion' -> baseline: always mean-reversion, regime-blind
    Returns a metrics dict."""
    forced = {"momentum": TRENDING_UP, "mean_reversion": RANGING}.get(mode)
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    pos = None            # {entry, qty_frac, sl, tp, t_open, exit_cfg, regime}
    trades = []
    regime_hist = {TRENDING_UP: 0, RANGING: 0, EUPHORIA: 0, RISK_OFF: 0}

    for i in range(WARMUP, len(closes)):
        h, l, c = highs[:i + 1], lows[:i + 1], closes[:i + 1]
        sig = _signals_at(h, l, c, fgs[i], fundings[i])
        label, _, _ = classify(sig)
        regime_hist[label] += 1
        active = label if forced is None else forced   # policy-selected sub-strategy
        price = closes[i]

        # ── manage an open position ──
        if pos:
            cfg = pos["exit_cfg"]
            hit = None
            if price <= pos["sl"]:
                hit, fill = "SL", pos["sl"]
            elif price >= pos["tp"]:
                hit, fill = "TP", pos["tp"]
            elif (i - pos["t_open"]) >= cfg["max_hold_hours"]:
                hit, fill = "timeout", price
            elif forced is None and label in (RISK_OFF, EUPHORIA) and pos["regime"] != label:
                hit, fill = "regime_exit", price   # season turned hostile -> step out
            if hit:
                ret = (fill - pos["entry"]) / pos["entry"]
                pnl = pos["qty_frac"] * (ret - 2 * FEE)
                equity *= (1 + pnl)
                trades.append({"regime": pos["regime"], "exit": hit, "ret": ret, "pnl": pnl})
                pos = None

        # ── consider an entry (only when flat) ──
        if not pos:
            sub = PLAYBOOK[active]
            entry_on = sub["entry"]["on"]
            enter = False
            if active == TRENDING_UP:
                ef = ema(c, 20)
                enter = ef[-1] is not None and price > ef[-1]
            elif active == RANGING:
                r = rsi(c, 14)
                enter = r[-1] is not None and r[-1] < 30
            # EUPHORIA / RISK_OFF: entry_on == "none" -> never enter (the point)
            if enter and entry_on != "none":
                frac = sub["sizing"].get("max_position_fraction", 0.25)
                pos = {
                    "entry": price, "qty_frac": frac,
                    "sl": price * (1 - sub["exit"]["stop_loss_pct"]),
                    "tp": price * (1 + sub["exit"]["take_profit_pct"]) if sub["exit"]["take_profit_pct"] else math.inf,
                    "t_open": i, "exit_cfg": sub["exit"], "regime": label,
                }

        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)

    bh = (closes[-1] - closes[WARMUP]) / closes[WARMUP]
    wins = [t for t in trades if t["pnl"] > 0]
    return {
        "bars": len(closes) - WARMUP,
        "total_return_pct": round((equity - 1) * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "buy_hold_return_pct": round(bh * 100, 2),
        "trades": len(trades),
        "win_rate_pct": round(100 * len(wins) / len(trades), 1) if trades else 0.0,
        "regime_bars": regime_hist,
        "exits": _tally(t["exit"] for t in trades),
    }


def _tally(it):
    out = {}
    for x in it:
        out[x] = out.get(x, 0) + 1
    return out


# ─────────────────────────── self-test (synthetic seasons) ───────────────────
def _synth():
    """Build a price series with four labelled seasons + matching sentiment, so we
    can assert the classifier names each season correctly."""
    highs, lows, closes, fgs, fundings, truth = [], [], [], [], [], []

    def push(c, fg, fund, label):
        highs.append(c * 1.004); lows.append(c * 0.996)
        closes.append(c); fgs.append(fg); fundings.append(fund); truth.append(label)

    p = 100.0
    for _ in range(80):                      # calm uptrend
        p *= 1.004; push(p, 62, 0.1, TRENDING_UP)
    for k in range(80):                      # range: oscillate, flat sentiment
        p = 140 + 4 * math.sin(k / 3.0); push(p, 50, 0.0, RANGING)
    for _ in range(40):                      # blow-off: fast up + euphoria + hot funding
        p *= 1.012; push(p, 88, 0.8, EUPHORIA)
    for _ in range(60):                      # crash + extreme fear
        p *= 0.985; push(p, 13, -0.3, RISK_OFF)
    return highs, lows, closes, fgs, fundings, truth


def selftest():
    highs, lows, closes, fgs, fundings, truth = _synth()
    # representative bar deep inside each season (segments: 0-79 up, 80-159 range,
    # 160-199 euphoria, 200-259 crash)
    checks = [(60, TRENDING_UP), (140, RANGING), (185, EUPHORIA), (235, RISK_OFF)]
    ok = True
    print("regime classification self-test:")
    for i, expected in checks:
        sig = _signals_at(highs[:i + 1], lows[:i + 1], closes[:i + 1], fgs[i], fundings[i])
        got, _, _ = classify(sig)
        flag = "OK " if got == expected else "FAIL"
        ok = ok and got == expected
        print(f"  [{flag}] bar {i}: expected {expected:<12} got {got}  "
              f"(trend {sig.trend_score:+.2f}, F&G {sig.fear_greed:.0f})")

    print("\nrouter vs buy-and-hold on the synthetic series:")
    m = run(highs, lows, closes, fgs, fundings)
    print(f"  router return : {m['total_return_pct']:+.2f}%   maxDD {m['max_drawdown_pct']:.2f}%")
    print(f"  buy & hold    : {m['buy_hold_return_pct']:+.2f}%")
    print(f"  trades        : {m['trades']}  win {m['win_rate_pct']}%  exits {m['exits']}")
    print(f"  regime bars   : {m['regime_bars']}")
    print("\nNOTE: synthetic data — proves the router's *mechanics*, not real edge. "
          "Run --csv on real OHLCV for performance evidence.")
    return 0 if ok else 1


def compare(highs, lows, closes, fgs, fundings):
    """Router vs the three static baselines on the same data. Primary lens = maxDD
    (the gate); secondary = return."""
    policies = [("Batavia router", "router"),
                ("always-momentum", "momentum"),
                ("always-mean-rev", "mean_reversion")]
    rows = [(name, run(highs, lows, closes, fgs, fundings, mode=m)) for name, m in policies]
    bh = rows[0][1]["buy_hold_return_pct"]

    print(f"{'policy':<18}{'return':>10}{'maxDD':>9}{'trades':>8}{'win%':>7}")
    print("-" * 52)
    for name, m in rows:
        print(f"{name:<18}{m['total_return_pct']:>9.2f}%{m['max_drawdown_pct']:>8.2f}%"
              f"{m['trades']:>8}{m['win_rate_pct']:>7}")
    print(f"{'buy & hold':<18}{bh:>9.2f}%{'—':>8}{'—':>8}{'—':>7}")
    rh = rows[0][1]["regime_bars"]
    tot = sum(rh.values()) or 1
    print("\nregime mix (router): " +
          "  ".join(f"{k}={v} ({100*v//tot}%)" for k, v in rh.items()))
    print(f"router exits: {rows[0][1]['exits']}")
    return rows


def _load(path, cols):
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append([float(row[c]) for c in cols])
    return rows


def main():
    ap = argparse.ArgumentParser(description="Batavia regime-router backtest.")
    ap.add_argument("--selftest", action="store_true", help="run synthetic-season checks")
    ap.add_argument("--csv", help="OHLCV csv (high,low,close)")
    ap.add_argument("--context", help="optional per-bar csv (fear_greed,funding)")
    ap.add_argument("--compare", action="store_true",
                    help="router vs static baselines table (use with --csv)")
    args = ap.parse_args()

    if args.selftest or not args.csv:
        sys.exit(selftest())

    px = _load(args.csv, ["high", "low", "close"])
    highs = [r[0] for r in px]; lows = [r[1] for r in px]; closes = [r[2] for r in px]
    if args.context:
        ctx = _load(args.context, ["fear_greed", "funding"])
        fgs = [r[0] for r in ctx]; fundings = [r[1] for r in ctx]
    else:
        fgs = [50.0] * len(closes); fundings = [0.0] * len(closes)
        print("WARN: no --context; fear_greed=50/funding=0 -> EUPHORIA/RISK_OFF(by fear) "
              "cannot trigger. Supply a context csv for full regime coverage.\n")

    if args.compare:
        compare(highs, lows, closes, fgs, fundings)
    else:
        import json
        print(json.dumps(run(highs, lows, closes, fgs, fundings), indent=2))


if __name__ == "__main__":
    main()
