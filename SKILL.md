---
name: batavia-regime-skill
description: >
  Detect the current market "season" (regime) from CoinMarketCap data and emit a
  backtestable trading-strategy spec tuned to that season — including the seasons
  where the right move is to hold cash. Use when the user wants a regime-aware
  quant strategy spec (which signal, when to switch, when to stand aside),
  grounded in a drawdown-first design — not a live trade. Produces a JSON spec a
  backtester can run, plus a runnable validation harness.
---

# Batavia — CMC market data → regime-aware, backtestable strategy spec

**Track 2** deliverable for the BNB Hack (CoinMarketCap track). Batavia is a CMC
Skill that turns market data into a *backtestable strategy spec*, not a live
agent. Its distinguishing idea: **markets move through seasons, and no single
signal is right in all of them.** So instead of shipping one strategy, Batavia
detects the regime and emits the strategy that season calls for — and in two of
the four seasons, that strategy is *do nothing*.

## The four seasons

| Regime | Detected when | Strategy it emits |
|---|---|---|
| **TRENDING_UP** | clear uptrend, no euphoric froth | momentum: ride with a trailing exit |
| **RANGING** | no dominant trend, calm sentiment | mean-reversion: fade oversold extremes |
| **EUPHORIA** | extreme greed **+** crowded long funding | defensive: **no new longs**, trim/tighten |
| **RISK_OFF** | extreme fear, or a downtrend (spot/long-only) | **cash**: stand aside |

The thesis: in a live-PnL competition the metric that decides everything is
**drawdown** ("most profit without blowing up"). The single largest drawdown
saver is refusing to trade in the wrong season — so Batavia's most important
output is often `entry.on: "none"`. A strategy skill that knows *when not to
trade* is rarer than one that always has an opinion.

## How an agent uses it

1. Read CMC context for the token:
   - `get_crypto_quotes_latest` → 1h candles → **trend_score**, **vol_state**
   - `get_crypto_technical_analysis` → RSI/MACD/EMA (corroborates trend/vol)
   - `get_global_crypto_derivatives_metrics` → funding/OI → **funding_stress**
   - `get_fear_and_greed_latest` → **fear_greed**
2. Classify the regime and emit a `strategy_spec` (see
   `schema/regime_strategy.schema.json`).
3. Hand the spec to any backtester — it is engine-agnostic; field meanings live
   in the schema.

```bash
# from CMC-derived signals (pass what the tools returned)
python generate_spec.py ETH --fear-greed 72 --trend 0.7 --funding 0.2

# or derive trend/vol straight from a 1h OHLCV csv
python generate_spec.py ETH --csv data/eth_1h.csv --fear-greed 35
```

Ready-made examples: `examples/eth_trending.json`, `examples/btc_risk_off.json`.

## Validation — framework, not fabricated numbers

Batavia ships a **runnable** harness, not pre-baked results:

```bash
python backtest/regime_router.py --selftest          # verify the router mechanics
python backtest/regime_router.py --csv your_1h.csv --context your_ctx.csv
```

`--selftest` builds four synthetic seasons and asserts the classifier labels each
correctly, then runs the router against buy-and-hold — demonstrating that
stepping out in EUPHORIA/RISK_OFF is what protects the drawdown. The performance
numbers you cite must come from running this on real data. See
[docs/METHODOLOGY.md](docs/METHODOLOGY.md) for the regime taxonomy, thresholds,
and the validation design (router vs three static baselines).

## Limitations

Long-only, spot (the eligible BEP-20 universe can't be shorted, so downtrends map
to cash, not to a short). Regime thresholds are transparent and tunable, not
fitted to a single backtest. Past performance is not a guarantee. This is a
research artifact — there is no execution layer here by design (that is Track 1's
job).
