# Demo Guide

## Offline demo

The deterministic demo needs no API key:

```bash
pip install -r requirements.txt
python demo.py
python demo.py --json
python verify.py
```

It demonstrates three distinct product behaviors:

| Evidence | Expected output |
|---|---|
| Fresh evidence plus three confirmed uptrend bars | `ACTIVE`, momentum receipt |
| Fresh extreme-fear evidence | `STAND_ASIDE`, risk-off cash receipt |
| Evidence older than two hours | `INSUFFICIENT_DATA`, cash receipt |

Every output is checked against strategy contract `v0.2` before it is printed.

## Suggested recording

Keep the video around two minutes:

1. State the problem: market-data prose is not an auditable strategy.
2. Show `SKILL.md` and its CMC evidence workflow.
3. Run `python demo.py` and explain the three decision statuses.
4. Run `python demo.py --json`; point to provenance, freshness, invalidation,
   the `agent_hub` contract, sizing, rejected alternatives, and the evidence
   hash.
5. Run `python verify.py` to demonstrate that the implementation works.
6. Show the generated backtest results after historical CMC access is resolved.
7. Close with the user: an agent or analyst that needs a deterministic research
   boundary before execution.

Do not claim historical performance in the recording until
`results/validation.json` exists and `backtest/check_reproduction.py` passes.
