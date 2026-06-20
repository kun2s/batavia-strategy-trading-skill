# Methodology — Batavia regime router

## 1. The premise

A single trading signal embeds a bet about market structure. Trend-following bets
the market trends; mean-reversion bets it ranges. Each is *right* in some regimes
and actively *harmful* in others:

- momentum gets **chopped up** in ranging markets (whipsaw losses), and gets
  caught at **blow-off tops** when it buys strength into euphoria;
- mean-reversion gets **run over** by strong trends (it keeps fading a move that
  doesn't come back).

Batavia's premise: don't pick one and hope. **Detect the regime, then deploy the
signal that fits it — and in hostile regimes, deploy nothing.**

## 2. The signals (all from the CoinMarketCap Agent Hub)

| Signal | Range | Source tool | Meaning |
|---|---|---|---|
| `fear_greed` | 0–100 | `get_fear_and_greed_latest` | crowd sentiment |
| `trend_score` | −1…+1 | `get_crypto_quotes_latest` → EMA20/50 | trend strength & sign |
| `vol_state` | low/normal/high | quotes → ATR% | volatility bucket |
| `funding_stress` | −1…+1 | `get_global_crypto_derivatives_metrics` | + = crowded longs |

`trend_score` is the EMA20–EMA50 spread normalised by a 3% full-scale band, then
dampened when price sits on the wrong side of the fast EMA (an early or failing
trend shouldn't read as a strong one). `vol_state` buckets 1h ATR%: `<1.5%` low,
`>4%` high. Both are computed in `batavia/indicators.py` with pure Python.

## 3. The decision tree (priority order)

Capital-preservation overrides are checked **first** — a euphoric or fearful tape
overrides any trend reading.

```
1. fear_greed >= 80  AND  funding_stress >= 0.5   → EUPHORIA    (no new longs)
2. fear_greed <= 20                                → RISK_OFF    (cash)
3. trend_score >= +0.5                             → TRENDING_UP (momentum)
4. trend_score <= -0.5                             → RISK_OFF    (cash; can't short spot)
5. otherwise                                       → RANGING     (mean-reversion)
```

Thresholds (`EXTREME_GREED`, `EXTREME_FEAR`, `TREND_ON`, `FUNDING_HOT`) are module
constants in `regime.py` — transparent and tunable, deliberately **not** fitted to
a single historical window (that would be overfitting the very thing the harness
is meant to test).

## 4. The playbook (regime → sub-strategy)

| Regime | Style | Entry | Exit | Sizing |
|---|---|---|---|---|
| TRENDING_UP | momentum | `close > EMA20` while trend on | SL 2.5% / TP 8% / 72h, trail 3% after +4% | vol-target, ≤34% |
| RANGING | mean-reversion | `RSI(14) < 30` near lower band | SL 2% / TP 3% / 24h | fixed 1.5%, ≤25% |
| EUPHORIA | defensive | **none** | trim/tighten existing only | 0 |
| RISK_OFF | cash | **none** | close risk, sit in quote asset | 0 |

The asymmetry is intentional: trends are let run (wide TP + trail), reversions are
taken quickly (tight TP), and hostile seasons size to zero.

## 5. Portfolio guardrails (regime-independent)

Motivated directly by the competition's ~30% drawdown gate, **not** by any one
strategy:

- de-risk from **12%** drawdown, **halt** new risk at **20%** (a 10-point buffer
  below a ~30% gate), resume below **14%** (hysteresis);
- `max_concurrent = 3`; `min_trades_per_day = 1`; `fee_per_side = 0.05%`.

The router's RISK_OFF/EUPHORIA seasons are the *first* line of drawdown defense;
the governor is the backstop.

## 6. Validation design

`backtest/regime_router.py` is the engine. The intended study:

- **Baselines:** `always_momentum`, `always_mean_reversion`, `buy_and_hold`.
- **Primary metric:** portfolio **max drawdown** (the gate). **Secondary:** total
  return and per-regime expectancy.
- **Method:** walk-forward, regime-segmented, on the eligible BEP-20 universe with
  1h candles and 0.05%/side costs.
- **Hypothesis to confirm or kill:** the router's drawdown is materially lower
  than always-momentum while it still captures ranging-market gains a trend-only
  system misses; and stepping flat in RISK_OFF/EUPHORIA is the largest single
  contributor to that drawdown reduction.

Real-data findings (ETH, 3000 1h bars) and a rejected refinement live in
[RESULTS.md](RESULTS.md).

### What the self-test shows (and doesn't)

`--selftest` runs on **synthetic** seasons. It proves the *mechanics*: the
classifier labels each season correctly, and the router sidesteps a constructed
crash that buy-and-hold eats. It is **not** evidence of real-world edge — that
requires real OHLCV + a per-bar sentiment/funding context series. Batavia
deliberately ships **no fabricated performance numbers**; the framework and a
runnable engine are the honest deliverable.

## 7. Limitations & honest failure modes

- **Regime lag.** Classification reacts to realised price/sentiment; sharp regime
  flips will be caught a few bars late. The drawdown governor exists for exactly
  this residual.
- **Threshold sensitivity.** Hard cutoffs (e.g. F&G 80) can flicker at the
  boundary; a production version would add hysteresis on the regime label.
- **Sentiment dependence.** EUPHORIA/RISK_OFF need live F&G and funding; without
  them the router degrades to a trend/range-only classifier (the harness warns).
- **Long-only.** No downside capture — by design, matching the spot universe.
