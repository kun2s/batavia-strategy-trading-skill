# Validation Results

The v0.2 results page is generated from `results/validation.json` by:

```bash
python backtest/render_results.py
```

No v0.1 performance numbers are retained because the old engine did not execute
the published strategy contract faithfully. Run the independent CoinMarketCap
fetch and validation commands in the README to produce the final report.

## Current validation status

On 2026-06-20, the supplied CMC key authenticated successfully for asset
identity and Fear & Greed data, but hourly historical OHLCV returned HTTP 403
(`Forbidden`). Therefore:

- no v0.2 winner has been declared;
- no incomplete or alternative-provider dataset has been substituted;
- no performance number is presented as final evidence.

See `docs/PROJECT_STATUS.md` for the exact continuation procedure.
