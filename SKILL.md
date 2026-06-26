---
name: batavia-regime-compiler
description: >
  Compile CoinMarketCap technical, sentiment, volatility, and derivatives
  evidence into an auditable, backtestable strategy receipt. Use when a user
  asks whether a crypto setup has enough current evidence to authorize a
  long-only momentum strategy, stand aside, or abstain because data is stale or
  incomplete. This skill performs research only and never executes a trade.
---

# Batavia CMC strategy compiler

Batavia converts live CoinMarketCap evidence into a deterministic JSON strategy
receipt. Do not improvise missing values and do not substitute another market
data provider.

## Workflow

1. Resolve the requested asset with `search_cryptos`. Retain its numeric CMC ID;
   never rely on symbol alone after resolution.
2. Call `get_crypto_quotes_latest` for the resolved ID.
3. Call `get_crypto_technical_analysis` for EMA/RSI/MACD context.
4. Call `get_global_metrics_latest` for global conditions and Fear & Greed.
5. Call `get_global_crypto_derivatives_metrics` for funding, open interest, and
   leverage context. Funding is optional; never replace an unavailable value
   with invented data.
6. Record each tool name and observation timestamp.
7. Normalize evidence:
   - `trend_score`: EMA20/EMA50 spread mapped to `[-1, 1]`;
   - `vol_state`: `low`, `normal`, or `high` from hourly ATR percentage;
   - `fear_greed`: CMC value in `[0, 100]`;
   - `funding_stress`: normalized funding in `[-1, 1]`, or `null`.
8. Compile the receipt with `generate_spec.py` or `batavia.regime.build_spec`.
9. Validate it against `schema/regime_strategy.schema.json`.
10. Present the decision status, regime, rationale, invalidation conditions,
    evidence freshness, and rejected alternatives. Never present the receipt as
    financial advice or execution confirmation.

## Agent Hub special-prize contract

Batavia is intentionally shaped as an Agent Hub-native Skill:

- The live path is MCP-first: CMC identity, quotes, technicals, global metrics,
  Fear & Greed, and derivatives context are collected through Agent Hub tools.
- The output records an `agent_hub` block naming the Skill surface, MCP surface,
  replay surface, required CMC tools, optional research tools, and x402 policy.
- The receipt hash includes the Agent Hub contract, source tool names, source
  timestamps, normalized signals, CMC ID, and confirmation count.
- Offline demos and CLI replay never replace CMC evidence; they only prove the
  deterministic compiler and schema contract without exposing an API key.
- x402 is treated as an Agent Hub access path for live CMC tool calls, not a
  fake trading-payment feature. If x402 is enabled by the runtime, the same
  receipt schema remains valid.

## Decision rules

Priority order:

1. F&G at or below 20 -> immediate `RISK_OFF`.
2. F&G at or above 80 plus funding stress at or above 0.5 -> immediate `EUPHORIA`.
3. Trend score at or above 0.5 for three hourly bars -> `TRENDING_UP`.
4. Trend score at or below -0.5 for three hourly bars -> `RISK_OFF`.
5. Otherwise -> `RANGING`.

Only confirmed `TRENDING_UP` may produce `ACTIVE`. All other complete evidence
produces `STAND_ASIDE`. Required evidence older than two hours, or missing Fear &
Greed/trend/volatility, produces `INSUFFICIENT_DATA`.

## Active strategy

- Entry signal: fresh close cross above EMA20 on a closed hourly bar.
- Execution assumption: next hourly bar open.
- Stop: 2.5%; target: 8%; maximum hold: 72 hours.
- Invalidation: confirmed regime stops being `TRENDING_UP`.
- Position fraction: ATR-targeted, bounded to 5%-25%.
- Costs: 0.05% per side.

`RANGING`, `EUPHORIA`, and `RISK_OFF` allocate zero. Mean reversion is retained
only as a validation baseline, not silently activated by the Skill.

## Failure behavior

- Unknown asset: report that CMC identity resolution failed.
- Tool failure: retry once, then mark the input missing.
- Rate limit: report the limit; do not fill gaps with assumptions.
- Stale evidence: emit `INSUFFICIENT_DATA`.
- Conflicting evidence: preserve all values and let the deterministic priority
  rules resolve them.

## Validation

The same strategy semantics run through `backtest/engine.py`. All candidate
policies share next-bar execution, stop-first intrabar fills, mark-to-market
equity, fees, sizing, and final liquidation. Generated results are in
`docs/RESULTS.md`.
