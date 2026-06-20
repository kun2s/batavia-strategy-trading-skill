# Batavia — a regime-detection strategy skill

> Markets move through seasons. No single signal is right in all of them.
> Batavia reads the *season* from CoinMarketCap data and emits the strategy that
> season calls for — including the seasons where the right move is to hold cash.

**BNB Hack — Track 2 (Strategy Skills, CoinMarketCap).** This is a *CMC Skill*
that produces a **backtestable strategy spec**, not a live trading agent. There
is no execution layer here by design — Track 2 is judged on the strategy, not
on-chain plumbing.

## Why it's different

Most strategy skills ship one signal and an opinion for every bar. Batavia ships
a **router**: it classifies the market into one of four regimes and switches the
active sub-strategy accordingly.

```
                   ┌─ EXTREME GREED + hot funding ──→  EUPHORIA   → no new longs, trim
   CMC signals ──→ ┤  EXTREME FEAR / downtrend ─────→  RISK_OFF   → hold cash
  (F&G, funding,   │  clear uptrend ───────────────→  TRENDING_UP → momentum + trail
   trend, vol)     └─ otherwise (calm, no trend) ───→  RANGING    → mean-reversion
```

The design is **drawdown-first**. In a live-PnL competition the metric that
decides everything is max drawdown ("most profit without blowing up"), and the
biggest drawdown saver is *not trading in the wrong season*. So Batavia's most
important output is often `entry.on: "none"` — a strategy skill that knows when
to stand aside.

## Layout

| Path | What it is |
|---|---|
| `SKILL.md` | The CMC Skill definition — methodology + CMC inputs |
| `batavia/regime.py` | Regime classifier + the season→strategy playbook |
| `batavia/indicators.py` | Pure-Python EMA/RSI/ATR + signal derivation (no numpy) |
| `generate_spec.py` | CLI: signals in → schema-valid strategy spec out |
| `schema/regime_strategy.schema.json` | JSON Schema for the spec (engine-agnostic) |
| `examples/` | Ready-made example specs (trending, risk-off) |
| `backtest/regime_router.py` | Runnable validation harness (`--selftest` or `--csv`) |
| `docs/METHODOLOGY.md` | Regime taxonomy, thresholds, validation design |

## Quickstart

```bash
pip install -r requirements.txt        # only jsonschema, for validating specs

# generate a spec from CMC-derived signals
python generate_spec.py ETH --fear-greed 72 --trend 0.7 --funding 0.2

# verify the router mechanics on synthetic seasons
python backtest/regime_router.py --selftest
```

The self-test builds four synthetic seasons, asserts the classifier labels each
correctly, then shows the router sidestepping a crash that buy-and-hold eats —
the mechanical proof of the drawdown-first thesis. **It ships no fabricated
performance numbers**; cite results only from running the harness on real data.

## Honesty notes

- Long-only, spot. The eligible BEP-20 universe can't be shorted, so downtrends
  map to **cash**, never to a short.
- Regime thresholds are transparent and tunable (see METHODOLOGY), not fitted to
  one backtest.
- Validation is a *framework + harness*, not baked numbers. Past performance is
  not a guarantee.

## License

MIT — see [LICENSE](LICENSE).
