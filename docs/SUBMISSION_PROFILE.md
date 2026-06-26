# Batavia Submission Profile

## Project name

**Batavia**

## Tagline

**Market evidence in. Auditable strategy receipt out.**

## Short description

Batavia turns live CoinMarketCap evidence into deterministic, schema-validated
strategy receipts that tell agents when to act, stand aside, or refuse a
decision because the data is stale or incomplete.

## BUIDL description

Crypto agents can turn market data into confident prose, but prose is difficult
to verify, backtest, or safely pass to another system. Batavia creates a clear
research boundary between market evidence and execution.

Built as a CoinMarketCap Strategy Skill, Batavia resolves assets by stable CMC
ID, records source and freshness metadata, normalizes technical, sentiment,
volatility, and derivatives signals, and classifies the current market regime.
It then emits one of three explicit outcomes: `ACTIVE`, `STAND_ASIDE`, or
`INSUFFICIENT_DATA`.

Each output is a deterministic JSON receipt containing exact entry, exit,
sizing, cost, and invalidation rules, plus rejected alternatives and a SHA-256
evidence hash. The receipt is validated against a strict versioned schema, so
an analyst, research agent, or future execution layer can inspect precisely what
the evidence permits without inventing missing certainty.

For the Best Use of Agent Hub special prize, Batavia makes Agent Hub part of the
machine-readable contract: the Skill declares the CMC MCP tools it needs, each
receipt records the Agent Hub surfaces and tool provenance, and the evidence
hash covers the CMC ID, source tool names, timestamps, normalized signals, and
confirmation count. The offline demo is a deterministic replay path, while the
live workflow remains CMC Agent Hub evidence in and auditable strategy receipt
out.

Batavia never signs transactions or forces a trade. Only a confirmed uptrend
with complete, fresh evidence can authorize its long-only momentum setup; every
other condition holds cash or abstains. Its shared backtesting engine uses
closed-bar signals, next-bar execution, explicit fees, stop-first intrabar
fills, bounded ATR sizing, and chronological validation windows.

The result is not another market opinion. It is a small, reproducible contract
for evidence-aware strategy decisions.

## One-line pitch

Batavia is an auditable decision layer that compiles CoinMarketCap evidence into
backtestable strategy receipts for crypto agents.

## Elevator pitch

Trading agents are getting faster, but their reasoning is still too hard to
audit. Batavia gives them a missing control layer: before an agent can act, it
must compile CMC evidence into a small receipt that says what the market data
permits, what invalidates the idea, and when the honest answer is no trade.

Instead of another confident market opinion, Batavia produces a replayable
contract: CMC tools in, normalized signals through a deterministic regime
router, schema-valid strategy out. It is built for researchers today and for
future autonomous execution systems that need a clean boundary between
evidence, decision, and action.

## Suggested category

**Strategy Skills / AI Agents / Market Intelligence**

## Logo concept

The recommended poster mark uses oversized, tightly set typography and an
asymmetric rule to give Batavia a bold editorial identity. Three horizontal
lines represent evidence entering the compiler; the amber arrow is the single
decision permitted by that evidence. A quieter symbol-only alternative is also
included for small UI placements.

- Submission logo: `assets/batavia-logo-poster.svg`
- Compact symbol: `assets/batavia-logo.svg`

### Brand colors

- Navy: `#11263D`
- Amber: `#D99A2B`
- Warm white: `#F7F4ED`
