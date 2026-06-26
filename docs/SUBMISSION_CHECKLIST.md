# Submission Checklist

**Deadline:** 2026-06-21 12:00 UTC / 19:00 WIB

## Required deliverables

- [x] Public GitHub, GitLab, or Bitbucket repository target.
- [x] Demo link/video, or setup instructions clear enough to reproduce.
- [x] Valid CMC Strategy Skill in `SKILL.md`.
- [x] Backtestable, machine-readable strategy contract.
- [x] No Track 1 wallet, execution, or on-chain proof requirement.
- [x] No API secret committed to the repository.

## Technical acceptance

- [x] `python verify.py` passes.
- [x] Skill validator passes.
- [x] Both example receipts pass JSON Schema validation.
- [x] Golden CMC fixture produces the exact expected receipt.
- [x] All seven candidate policies use the shared execution engine.
- [x] Clean-room scan is clear.
- [ ] Seven-asset CMC historical manifest exists.
- [ ] `results/validation.json` exists.
- [ ] `python backtest/check_reproduction.py` passes.
- [ ] Final strategy selection is reflected consistently in code and docs.

## Judging narrative

- **Technical execution:** deterministic receipt, strict schema, provenance,
  freshness gate, shared no-look-ahead engine, and reproducible documentation.
- **Originality:** Batavia compiles what evidence permits instead of emitting an
  unstructured prediction or forcing a trade.
- **Real-world relevance:** research agents, analysts, and execution systems can
  consume the receipt as a risk boundary.
- **Demo:** show `ACTIVE`, `STAND_ASIDE`, and `INSUFFICIENT_DATA`, then prove all
  three are schema-valid and deterministic.
- **Special prize:** target Best Use of Agent Hub. Do not claim TWAK. Point to
  `SKILL.md`, the receipt `agent_hub` block, source tool provenance, and the
  evidence hash.

## Submission form steps

1. Choose Track 2 / Strategy Skills.
2. Paste the repository URL:
   `https://github.com/kun2s/batavia-strategy-trading-skill`.
3. Paste the project name, tagline, and BUIDL description from
   `docs/SUBMISSION_PROFILE.md`.
4. Use `docs/DEMO.md` for the video script, or cite the offline setup commands
   if the form accepts reproducible instructions instead of a video.
5. In the special-prize or notes field, state that the target is Best Use of
   Agent Hub because the live workflow is CMC MCP-first and every receipt
   records Agent Hub provenance.
6. Do not enter an agent wallet address for Track 2 unless the form incorrectly
   requires it. Batavia has no wallet by design.

## Owner actions

1. Push the repository to
   `https://github.com/kun2s/batavia-strategy-trading-skill`.
2. Record/upload the demo using `docs/DEMO.md` if the submission form requires
   a video URL instead of reproducible setup instructions.
3. Ask CMC support or the hackathon Builder Telegram to enable historical OHLCV
   for the project key, or provide the approved hackathon route to the same CMC
   hourly history.
4. If historical OHLCV access is granted before the deadline, generate
   `results/validation.json` and rerun `backtest/check_reproduction.py`.
5. Submit before the deadline.

Suggested support message:

```text
I am submitting a Track 2 Strategy Skill to BNB Hack. My CMC key authenticates
for /v1/cryptocurrency/map and /v3/fear-and-greed/historical, but
/v2/cryptocurrency/ohlcv/historical returns HTTP 403. The published strategy
validation requires 365 days of hourly OHLCV for seven assets. Can you enable
this endpoint for the hackathon key or confirm the approved CMC route for this
historical dataset? I will not use a third-party substitute.
```

Never paste the API key into a public issue, Telegram message, video, commit, or
submission form.
