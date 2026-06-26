# Batavia Judging Brief

Batavia is designed for Track 2: a CoinMarketCap Strategy Skill that emits a
backtestable strategy spec, not a live-trading agent.

## Why this fits Track 2

The hackathon asks Track 2 teams to turn CMC market data into a trading
strategy. Batavia does that as a deterministic research boundary:

- CMC evidence in: asset identity, quotes, technical context, Fear & Greed,
  derivatives/funding context, source names, and observation timestamps.
- Strategy receipt out: `ACTIVE`, `STAND_ASIDE`, or `INSUFFICIENT_DATA`.
- Backtestable contract: entry, exit, sizing, fees, invalidation, rejected
  alternatives, and a schema-validated evidence hash.

Batavia never executes trades or signs transactions. That is intentional for
Track 2.

## Criteria Map

| Judging criterion | What to look at |
|---|---|
| Technical execution | `SKILL.md`, `schema/regime_strategy.schema.json`, `batavia/regime.py`, `backtest/engine.py`, `verify.py` |
| Originality | Refusal-to-decide behavior, deterministic receipt, evidence hash, rejected alternatives |
| Real-world relevance | Analysts and agents can use the receipt as a risk boundary before execution |
| Demo and presentation | `docs/DEMO.md`, `demo.py`, `examples/`, `python verify.py` |

## CMC Surface Area

Batavia uses CoinMarketCap as the source of decision evidence, not decorative
context:

- CMC asset identity prevents symbol ambiguity.
- CMC technical analysis drives the trend score.
- CMC global metrics and Fear & Greed drive risk overrides.
- CMC derivatives context drives the euphoria/crowded-long branch.
- CMC historical OHLCV is the intended independent validation data source.

The implementation intentionally refuses to substitute another provider when CMC
historical OHLCV is unavailable for the submitting key.

## Best Use of Agent Hub Case

Batavia's special-prize target is Best Use of Agent Hub, not TWAK.

What to look at:

- `SKILL.md` defines the live MCP workflow and the failure behavior for missing,
  stale, rate-limited, or conflicting CMC evidence.
- The JSON receipt includes an `agent_hub` section with the Skill, MCP, and CLI
  replay surfaces plus required and optional CMC tools.
- The evidence hash includes the Agent Hub contract, normalized signals,
  source tool names, timestamps, CMC ID, and confirmation count.
- The demo is review-safe and offline, but it preserves the same schema and
  replay path used by the live Agent Hub workflow.

This means Agent Hub is not only mentioned in the README. It is part of the
machine-readable strategy contract judges can inspect and validate.

## Demo Arc

Use a two-minute demo:

1. Show the problem: market prose is not an auditable strategy.
2. Show `SKILL.md`: CMC evidence collection and deterministic rules.
3. Run `python demo.py`: three outcomes appear immediately.
4. Run `python demo.py --json`: point to `agent_hub`, provenance, freshness,
   sizing, invalidation, rejected alternatives, and hash.
5. Run `python verify.py`: prove the contract, examples, and engine semantics
   are tested.

## Honest Limit

Final multi-asset historical performance is not claimed unless the CMC
historical-OHLCV endpoint is available. This is a strength of the submission:
Batavia abstains instead of manufacturing certainty from stale, unavailable, or
non-CMC data.
