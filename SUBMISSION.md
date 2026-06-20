# Batavia — Submission (BNB Hack, Track 2: Strategy Skills)

> A CMC Skill that reads the market's *season* and emits the backtestable strategy
> that season calls for — including the seasons where the right move is to hold cash.

- **Track:** 2 — Strategy Skills (CoinMarketCap). Deliverable is a *strategy spec*,
  no live execution.
- **Repo:** *(public repo link here)*
- **Demo:** *(2-min video / asciinema link here)* — or run the Quickstart below.

---

## The problem

Every trading signal is a hidden bet on market structure. Trend-following bets the
market trends; mean-reversion bets it ranges. Each is *right* in some regimes and
actively *harmful* in others — momentum gets chopped up in ranges and buys
blow-off tops; mean-reversion gets run over by strong trends. Most "strategy
skills" ship one signal and an opinion for every bar, so they are wrong half the
time by construction.

## The insight

Don't pick one signal and hope. **Detect the regime, then deploy the strategy that
fits it — and in hostile regimes, deploy nothing.** In a live-PnL competition the
metric that actually decides everything is **max drawdown** ("most profit without
blowing up"), and the single biggest drawdown saver is *refusing to trade in the
wrong season*. So Batavia's most important output is often `entry.on: "none"`.

## How it works

Four seasons, classified from CoinMarketCap Agent Hub data:

| Regime | Detected from CMC | Strategy emitted |
|---|---|---|
| **TRENDING_UP** | quotes → EMA trend, no euphoria | momentum + trailing exit |
| **RANGING** | no trend, calm sentiment | mean-reversion (fade oversold) |
| **EUPHORIA** | Fear&Greed ≥ 80 **+** hot perp funding | **no new longs** (blow-off risk) |
| **RISK_OFF** | Fear&Greed ≤ 20, or a downtrend | **cash** |

Signals: `get_crypto_quotes_latest` (trend, volatility), `get_fear_and_greed_latest`
(sentiment), `get_global_crypto_derivatives_metrics` (funding/positioning). The
classifier is a transparent, tunable decision tree (not fitted to one backtest);
each regime maps to a fully-specified, schema-valid sub-strategy. Output validates
against `schema/regime_strategy.schema.json`, so any backtester can run it.

## Validation — on real, free public data (and honest about it)

We pulled **real** 1h OHLCV (Binance), Fear & Greed (alternative.me), and funding
(Binance) — and tested across a **7-asset basket** (BTC/ETH/BNB/SOL/AVAX/LINK/DOGE,
3000 bars each, Feb–Jun 2026, 0.05%/side costs):

```
MEAN     router -3.3% / maxDD 3.7%    momentum +1.8% / maxDD 6.7%    buy&hold -14.5%
router maxDD <= momentum maxDD : 6/7      router return > buy&hold : 7/7
```

- The router's mean max drawdown is **3.7% — roughly half of momentum's 6.7%** —
  and it beat buy-and-hold on return on **all 7 assets** (a down window).
- On the volatile alts (AVAX, LINK) regime-blind momentum drew down **9–11%**
  chasing failed breakouts; the router sat them out and *also* won on return.
- **Honest cost:** in cleanly trending majors, momentum out-returns the router.
  Batavia trades return for drawdown-robustness — *consistently*. That's the point,
  not a bug.

We also ship what we **rejected**: a "be greedy when fearful" tweak that sounded
good and made real-data results *worse* (−6.9% vs −4.6% on ETH), so we dropped it
(see `docs/RESULTS.md` §8). Tuning a rule after seeing one window is how strategies
overfit; publishing the rejection is how we stay honest. **No number in this
submission is fabricated** — every figure reproduces from `backtest/`.

## Why it's different

Most entries chase the highest backtested return. Batavia is built around the
metric that decides a live-PnL competition — **drawdown** — and is the rare
strategy skill that knows *when not to trade*. It ships a runnable validation
harness, a multi-asset robustness test, and a documented rejected experiment, not
a single hand-picked equity curve.

## Real-world relevance

This is the strategy brain a self-custody user would actually let run unattended:
it defaults to *out of the market* and only takes the trade the current regime
justifies. The same spec drives a Track-1-style live agent without changing the
research artifact.

## Quickstart

```bash
pip install -r requirements.txt
python generate_spec.py ETH --fear-greed 72 --trend 0.7 --funding 0.2   # spec out
python backtest/regime_router.py --selftest                              # mechanics
python backtest/validate_basket.py                                       # real basket
```

## Limitations

Long-only, spot (downtrends map to cash, not shorts). Validated on one ~4-month
*down* window across 7 assets — a complete study needs a bull window too (where
momentum should win more). EUPHORIA never triggered in this window (validated
synthetically via `--selftest`). Hourly Fear & Greed is a daily series mapped to
the hour. The backtester is a faithful test of the *router logic*, not a
high-fidelity execution simulator. Past performance is not a guarantee.
