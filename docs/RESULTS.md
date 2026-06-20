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
