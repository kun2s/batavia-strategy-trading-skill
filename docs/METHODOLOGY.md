# Methodology

## Research question

Can CoinMarketCap market-state evidence improve when a long-only momentum
strategy participates, without introducing look-ahead bias or unverifiable LLM
discretion?

Batavia answers by compiling evidence into explicit rules and replaying those
rules with the same engine used for every baseline.

## Evidence

- Hourly OHLCV: CMC `/v2/cryptocurrency/ohlcv/historical`, resolved by CMC ID.
- Sentiment: CMC `/v3/fear-and-greed/historical`.
- Live technical context: CMC MCP `get_crypto_technical_analysis`.
- Live global context: CMC MCP `get_global_metrics_latest`.
- Live derivatives context: CMC MCP `get_global_crypto_derivatives_metrics`.

Historical funding is not assumed. Missing funding remains `null`; the
EUPHORIA branch is tested with deterministic synthetic evidence.

The historical OHLCV endpoint is subscription-gated by CMC. The research run
requires a key that can access `/v2/cryptocurrency/ohlcv/historical`; successful
authentication to free endpoints does not guarantee this entitlement.

## Regime confirmation

Extreme fear and euphoria are immediate risk overrides. All other label changes
must persist for three closed hourly bars. This hysteresis is fixed before
evaluation and exists to prevent boundary flicker, not to optimize a window.

## Candidate policies

| Policy | Behavior |
|---|---|
| `router` | Momentum in confirmed uptrends, RSI/Bollinger baseline in ranges, otherwise cash |
| `trend_cash` | Momentum in confirmed uptrends, otherwise cash |
| `sentiment_momentum` | Momentum except during extreme sentiment/funding risk |
| `momentum` | Regime-blind momentum baseline |
| `mean_reversion` | Regime-blind RSI/Bollinger baseline |
| `buy_hold` | Fully invested benchmark |
| `cash` | Zero-risk benchmark |

Mean reversion appears only in research. The public playbook allocates cash in
`RANGING` unless a future independently validated version changes the contract.

## Execution semantics

- Signals use closed bars only and execute at the next bar open.
- A fresh momentum entry requires the previous close at/below EMA20 and the
  latest close above EMA20.
- Mean reversion requires RSI(14) below 30 and close at/below the lower
  Bollinger band.
- Every active signal policy uses the same ATR-targeted position fraction,
  2.5% stop, 8% target, and 72-hour maximum hold. Strategy-specific signal
  exits remain part of the strategy being tested.
- Stops and targets use intrabar high/low; if both are touched, the stop wins.
- Entry and exit each cost 0.05%.
- Equity is marked to market every bar.
- Open positions liquidate on the final bar.

## Selection gate

The seven assets are split into three non-overlapping chronological windows.
Before the split, every asset is aligned to the same continuous hourly
timestamp intersection. Fear & Greed is joined as-of publication time, never by
calendar date, so an observation cannot appear before it was available.
A regime-aware candidate is eligible only if:

1. median window return is positive; and
2. cumulative return is positive on at least four of seven assets.

Among eligible candidates, median return/max-drawdown selects the published
policy. If none passes, `sentiment_momentum` is the declared fallback and the
failure is published rather than hidden.

## Reproduction

```bash
export CMC_API_KEY=...
python backtest/fetch_cmc.py --days 365
python backtest/validate_basket.py --out results/validation.json
python backtest/render_results.py
python backtest/check_reproduction.py
python -m unittest discover -v
```

The fetch writes a provenance manifest containing the request range, CMC IDs,
row coverage, timestamps, endpoint names, and SHA-256 checksums. Validation must
stop rather than substitute another source when CMC denies historical access.
