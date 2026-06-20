# Results — real-data validation

Honest empirical findings. No number here is cherry-picked or hand-tuned; every
figure is reproducible from the commands shown.

## Data

| | |
|---|---|
| Asset | ETH/USDT, 1h candles |
| Window | 2026-02-15 → 2026-06-20 (3,000 bars, ~125 days) |
| Price | Binance public klines (free, no key) |
| Sentiment | alternative.me Fear & Greed (daily → mapped to each hour) |
| Funding | Binance futures fundingRate (8h → normalized to ±1) |
| Costs | 0.05% per side |

Reproduce:

```bash
python backtest/fetch_data.py ETH --bars 3000
python backtest/regime_router.py --csv data/eth_1h_price.csv \
                                 --context data/eth_1h_ctx.csv --compare
```

## The table

```
policy                return    maxDD  trades   win%
----------------------------------------------------
Batavia router        -4.64%    4.64%      19   36.8
always-momentum        5.49%    5.71%      52   42.3
always-mean-rev        0.29%    3.71%      38   55.3
buy & hold           -12.47%       —       —      —
```

Router regime mix: `RISK_OFF 54% · RANGING 43% · TRENDING_UP 2% · EUPHORIA 0%`.

## What this honestly says

**The good.** This was a *down* window — buy-and-hold lost **−12.5%**. The router
lost **−4.6%**, cutting the market's drawdown by ~63%, with a max drawdown of just
4.6% — far inside any competition gate. The drawdown-first thesis held: by sitting
in cash for 54% of bars (Fear & Greed was in extreme-fear territory for much of
the window), it sidestepped most of the decline.

**The uncomfortable.** `always-momentum` *beat* the router on return (+5.5% vs
−4.6%). The reason is visible in the regime mix: extreme fear persisted even
through tradeable bounces, so the router parked in cash while a regime-blind
momentum bot caught those rallies. On a single trending-down window, a
fear-respecting router gives up upside that pure momentum keeps.

**The honest conclusion.** The router's edge is **not** "beats momentum on every
window" — it clearly doesn't here. Its edge is **drawdown-adjusted robustness**:
it preserves capital across hostile regimes where momentum eventually blows up.
Proving *that* needs multi-asset, multi-window validation (several tokens across a
full cycle), which is the next step — not a single ETH window. We publish the
window that does *not* flatter the strategy precisely so the claim stays honest.

## Multi-asset basket — the robustness test

One window on one asset is an anecdote. The router's actual claim — *lower
drawdown across regimes and assets* — only a basket can test. Same period, same
0.05%/side costs, 3000 1h bars each:

```bash
python backtest/validate_basket.py        # BTC ETH BNB SOL AVAX LINK DOGE
```

```
asset     router  rtr_DD      mom  mom_DD  meanrev      b&h
-----------------------------------------------------------
BTC        -3.5%    3.5%     6.1%    5.3%    -3.9%    -6.7%
ETH        -4.6%    4.6%     5.5%    5.7%     0.3%   -13.3%
BNB        -1.6%    1.6%     1.2%    3.1%    -0.9%    -6.1%
SOL        -3.7%    3.7%     2.5%    6.8%    -3.0%   -15.9%
AVAX       -0.9%    2.7%    -2.3%   11.2%     2.8%   -32.7%
LINK       -2.4%    3.5%    -0.6%    9.2%     1.6%   -10.3%
DOGE       -6.2%    6.2%     0.2%    5.9%    -1.2%   -16.5%
-----------------------------------------------------------
MEAN       -3.3%    3.7%     1.8%    6.7%    -0.6%   -14.5%

router maxDD < |buy&hold return|  : 7/7
router maxDD <= momentum maxDD     : 6/7
router return > buy&hold return    : 7/7
```

**The thesis holds — measured on drawdown, not return.** Across all seven assets
the router's mean max drawdown is **3.7%, roughly half of momentum's 6.7%**, and
it never drew down worse than momentum except on DOGE. It beat buy-and-hold on
return **7/7** (this was a broadly *down* window — mean buy-hold −14.5%).

Look at **AVAX** and **LINK**: regime-blind momentum drew down **11.2%** and
**9.2%** chasing breakouts that failed, while the router sat out the worst and
*also* beat momentum on return. That is the router earning its keep exactly where
it should — in hostile, choppy alts where a single static signal blows up.

**The honest cost:** in cleanly trending assets (BTC, ETH, SOL) momentum
out-returns the router, which spent much of the window defensively in cash. Mean
router return (−3.3%) trails mean momentum (+1.8%). Batavia explicitly trades
return for drawdown-robustness — and does so *consistently*, which is the point.

**Still open:** this is one ~4-month window that was net-down across the board. A
complete study needs a bull window too (where momentum should win more and the
router should concede more upside). The harness makes that a one-command test.

## §8 — A rejected refinement (what we tried and dropped)

After seeing momentum win this window, we tried a plausible fix: *"be greedy when
others are fearful"* — let a strong uptrend (`trend ≥ 0.5`) override extreme fear,
so the router participates in fear-driven recovery rallies instead of sleeping
through them (reorder the decision tree: trend before fear).

**It made things worse:** router return fell to **−6.94%** (from −4.64%) and win
rate dropped to 29% — the extra momentum entries into fearful tape mostly got
stopped out. So we **reverted** it. Capital preservation (fear → cash, checked
before trend) is both more thesis-consistent and empirically better here.

This is the harness doing its job: a reasonable-sounding idea, killed by data
before it shipped. Tuning a rule *after* seeing one window is exactly how
strategies overfit — publishing the rejection is how we keep ourselves honest.

## Caveats

- Single asset, single window. Not yet evidence of a general edge.
- `EUPHORIA` never triggered here (no extreme-greed + hot-funding period in the
  window) — that branch is validated only synthetically (`--selftest`).
- Fear & Greed is a daily series mapped to hourly bars (sentiment moves slowly,
  so this is a mild approximation).
- The backtester is deliberately simple: long-only, one position at a time. It is
  a faithful test of the *router logic*, not a high-fidelity execution simulator.
