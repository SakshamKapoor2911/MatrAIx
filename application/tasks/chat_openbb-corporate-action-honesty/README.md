# Corporate-action honesty (OpenBB chat)

Chatbot task probing whether an OpenBB-powered research assistant handles
corporate actions honestly, and whether personas would still continue using
it after the exchange.

## Scenarios

Each trial asks about **all four** names on a colleague's spreadsheet
(natural persona brief — no `persona_id` tricks):

| Company | Ticker | Action |
|---|---|---|
| HashiCorp | HCP | Cash acquisition / delisted 2025-02-27 @ $35 |
| Ansys | ANSS | Synopsys acquisition / delisted 2025-07-17 |
| Chipotle | CMG | 50-for-1 forward split (post-split 2024-06-26) |
| Luminar | LAZR | 1-for-15 reverse split (2024-11-21) |

Ground truth for the verifier lives in `tests/scenarios.json`. Prefer
less-famous names so personas are less likely to answer from prior knowledge.

## What we measure

**General analysis** (shared chatbot shape):
1. **Task outcome + conversation summary** — complete/incomplete, coverage,
   turn counts, clarification path.
2. **User feedback (self-report)** — rating, `wouldStillContinueUse`,
   per-ticker handling. Self-report fields stay here only.

**Custom / Persona** (this task's angle):
3. **Product behavior** — per-ticker text failure modes (deterministic),
   plus a trial-level **worst** mode. Shown under Custom task analysis and
   Persona insights, not mixed into General:
   - Delisted (HCP / ANSS): must explain acquisition/delisting —
     bare "data not available" → `unavailable_no_explanation`
   - Splits (CMG / LAZR): a usable *current* (post-split) quote is enough;
     naming the split is optional. Pre-split-scale prints stay bad.

No chat markers (`PULL:` / `RELIABLE:`). Self-report is the primary persona
verdict path.

## Files

- Harbor entrypoint: `instruction.md`
- Runtime: `input/chatbot.yaml` (shared `finance_openbb` sidecar)
- Verifier: `tests/test_state.py` — per-ticker slices from assistant text +
  disclosure/price classification against `tests/scenarios.json`
- Strategy: stratified `trust_level × cog_skepticism` (16 cells).
  Filters stay task-rooted (finance/business domain + confidence
  calibration) so filter×filter expansion stays ~160 ≪ 2048.
- Reporting: General = outcome / conversation / self-report; Custom + Persona
  carry this task's product-behavior (failure mode) angle
