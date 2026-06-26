# Batavia - BNB Hack Track 2

> CoinMarketCap evidence in. Auditable strategy receipt out.

- **Track:** Strategy Skills
- **Repository:** https://github.com/kun2s/batavia-strategy-trading-skill
- **Demo:** Offline demo and recording script in `docs/DEMO.md`
- **Judge brief:** `docs/JUDGING_BRIEF.md`

## Problem

An LLM can turn a market-data response into confident prose even when inputs are
stale, incomplete, or contradictory. That is not a strategy another system can
audit or backtest.

## Product

Batavia is a CMC Skill that compiles market evidence into a deterministic
strategy receipt. It resolves a stable CMC asset identity, records source and
freshness metadata, classifies the market state, and returns one of three clear
statuses:

- `ACTIVE`: evidence authorizes the fully specified momentum setup;
- `STAND_ASIDE`: evidence is complete but does not authorize risk;
- `INSUFFICIENT_DATA`: Batavia refuses to manufacture certainty.

The receipt includes entry, exit, sizing, costs, invalidation, rejected
alternatives, and a reproducible evidence hash.

## CoinMarketCap integration

The live workflow uses CMC search, quotes, technical analysis, global metrics,
Fear & Greed, and derivatives context through Agent Hub MCP. Historical research
uses CMC hourly OHLCV and CMC Fear & Greed by numeric CMC ID.

CMC is not decorative context: its evidence directly determines whether Batavia
authorizes momentum, holds cash, or abstains.

## Special prize target

Batavia should be positioned for **Best Use of Agent Hub**.

The submission does not claim TWAK execution or BNB SDK integration. Its special
prize case is that Agent Hub is the actual research interface: the Skill
declares the CMC MCP tools it needs, the receipt records those tools and
timestamps, and the evidence hash makes the decision replayable. The CLI and
offline demo are review aids; the live path remains CMC Agent Hub evidence in
and schema-validated strategy receipt out.

## Technical execution

The emitted rules and the backtester share exact semantics: closed-bar signals,
next-bar-open execution, stop-first intrabar fills, fees on both sides,
mark-to-market equity, bounded ATR sizing, and final-bar liquidation.

Seven candidate policies are evaluated across seven assets and three
chronological windows. The selection gate is published before the results and
the human-readable report is generated directly from committed JSON.

The engine and selection gate are complete. Final historical performance
figures are intentionally not claimed unless the CMC historical-OHLCV endpoint
is available for the submitting key. Batavia does not replace denied CMC history
with another provider or an old cache.

## Why it matters

Batavia is the research boundary an autonomous system needs before execution:
not another opinion, but a small machine-readable contract that states what the
evidence permits, what invalidates it, and when the honest answer is no trade.

## Reproduce

```bash
pip install -r requirements.txt
python -m unittest discover -v
export CMC_API_KEY=...
python backtest/fetch_cmc.py --days 365
python backtest/validate_basket.py --out results/validation.json
python backtest/render_results.py
python backtest/check_reproduction.py
```

## Limits

Long-only research; no execution layer. Historical funding is not assumed, so
the euphoria branch is synthetic-test evidence rather than a historical claim.
Past performance does not guarantee future results.
