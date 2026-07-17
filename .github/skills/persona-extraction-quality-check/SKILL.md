---
name: persona-extraction-quality-check
description: 'Evaluate extracted personas against their source profiles with the canonical EXTRACTION_QUALITY_RUBRIC.md. Use when asked to check persona quality, score Stack Overflow/Wikipedia/Amazon persona extractions, run M1-M7 validation, compare LLM judges, or perform parallel multi-model persona review. Reviews exactly one persona per judge task and supports GPT-5.6 Sol, Claude Opus 4.8, Gemini 3.5 Flash, MAI-Code-1-Flash, and other capable models.'
argument-hint: 'source=<CSV/JSONL/dir> extraction=<JSONL/ZIP/dir> [sample=100|all] [mode=panel|sharded] [concurrency=8] [output=<dir>]'
user-invocable: true
disable-model-invocation: false
---

# Persona Extraction Quality Check

Evaluate extraction quality one complete persona at a time. The source profile is ground truth. Never score an extraction without pairing it to its exact source record.

## Canonical rubric

Before judging anything, read the complete canonical rubric at:

`persona/human_extraction/docs/EXTRACTION_QUALITY_RUBRIC.md`

Use its M1–M7 definitions and 1–5 anchors verbatim. Do not invent a replacement scale or silently reinterpret a metric. Read [the judge protocol](./references/judge-protocol.md) before dispatching reviewers.

## Non-negotiable rules

1. **One judge task receives exactly one persona packet.** Never ask one reviewer call to score several personas.
2. **Judge the full persona.** Do not split one persona's fields across workers; M4–M7 require whole-record context.
3. **Inspect fields before record-level scoring.** Check every emitted field for M1 value, M2 evidence, and M3 description, then score M4–M7.
4. **Parallelize across independent reviews, not within a persona.** Multiple personas and/or independent model reviews may run concurrently.
5. **Keep reviewers independent.** A reviewer must not see another review before producing its own result.
6. **Fail closed on identity mismatch.** Never pair records by guessed position if `ResponseId`, `response_id`, `row_index`, or another stable ID conflicts.
7. **Do not treat confidence as correctness.** Verify the value and evidence against the source even when confidence is 1.0.
8. **Resume safely.** Skip an existing valid `(persona_id, actual_model)` review unless the user explicitly requests overwrite.
9. **Do not claim a model was used unless the runtime actually selected it.** Record both requested and actual model names.
10. **Never expose one person's full source profile in aggregate reports.** Keep source text in per-persona packets; aggregate only scores and concise issue summaries.

## Inputs

Require these logical inputs:

- **Source profiles:** CSV, JSONL, SQLite, or a directory containing them. For Stack Overflow 2025, prefer the exact filtered CSV used by extraction, normally `results_2025_completeness_60.csv`, not the broader raw CSV.
- **Extracted personas:** one or more JSONL files, a ZIP containing JSONL shards, or a directory of shards.
- **Output directory:** packets, independent reviews, consensus, and summaries go here.
- **Selection:** explicit IDs, a deterministic sample, or all records.

If only a source directory is supplied, resolve a single unambiguous source file. If multiple plausible files remain, ask which one was used for extraction. Do not choose silently.

The example Stack Overflow source directory is external to this repository and contains source survey rows, not necessarily the extracted persona JSONL. Locate or request the extraction output separately.

All source types must be normalized to [the shared review packet contract](./references/packet-contract.md). The bundled `prepare_persona_packets.py` is currently the Stack Overflow CSV adapter. Wikipedia and Amazon use the same downstream workflow but require source-specific packet adapters as described in that contract; do not claim the CSV adapter supports them directly.

## Step 1 — Preflight and packet preparation

1. Confirm the rubric exists and note its Git blob/hash or file SHA-256 in run metadata.
2. Confirm source and extraction files are readable.
3. Inspect one extraction record to identify its ID fields and `fields` layout.
4. Verify the join strategy on at least three records before preparing the full selection:
   - Prefer extraction `response_id` ↔ source `ResponseId`.
   - Cross-check `row_index` against the zero-based row in the exact filtered source CSV when both are available.
   - For other datasets, use stable IDs such as `global_idx`, `uuid`, or `qid` only when both sides agree.
5. Prepare one self-contained packet per persona that conforms to [the packet contract](./references/packet-contract.md). For Stack Overflow CSV data, use [prepare_persona_packets.py](./scripts/prepare_persona_packets.py). For Wikipedia or Amazon, use the corresponding dataset adapter. A packet contains the complete source profile, complete extracted field list, matching schema definitions for emitted fields, and identity metadata.
6. Use a deterministic seed for sampling and record it. The rubric's standard validation size is 100 personas unless the user requests another size.
7. Stop if there are duplicate persona IDs, duplicate extraction records, missing source matches, or conflicting IDs. Report the exact counts; do not grade a partial or misjoined set as though it were complete.

## Step 2 — Choose review mode

### Panel mode — recommended for a validation sample

Every selected persona is independently reviewed by every available requested model. Use this for the canonical 100-persona validation, model comparison, or consensus scoring.

Preferred reviewer pool when available:

- GPT-5.6 Sol
- Claude Opus 4.8 (also accept the UI alias “Claude 4.8 Opus”)
- Gemini 3.5 Flash
- MAI-Code-1-Flash (the currently available MAI reviewer; resolve again at runtime if model names change)

All models receive the same packet, canonical rubric, protocol, and output contract. Model-specific reasoning styles must not change the score definitions.

### Sharded mode — recommended for a large/full dataset

Assign each persona to one available model in deterministic round-robin order. Each persona still receives one complete independent review, but not a four-model panel. Record the assignment so the run is reproducible.

### Single-model fallback

This skill is model-neutral and can be executed when GPT, Claude, Gemini, or MAI is the currently selected model. If explicit cross-model subagent selection is unavailable, use the current model, record the limitation, and do not pretend a multi-model panel occurred.

## Step 3 — Parallel dispatch

Use the host's parallel task/subagent facility when available.

- Default global concurrency: **8 reviewer calls**.
- In four-model panel mode, process at most two persona panels concurrently at concurrency 8.
- Each worker input: one packet path, rubric path, protocol path, requested model, run ID.
- Each worker output: exactly one JSON review conforming to the protocol.
- The orchestrator, not the reviewer, writes the returned JSON to avoid concurrent file collisions.
- Suggested path: `reviews/<persona_id>/<sanitized-actual-model>.json`.
- Continue launching work as slots free up; do not load all source profiles into model context at once.
- Retry malformed output once with a schema-repair request. Never change the substantive scores during repair.
- After a second malformed response, record a failed review and continue; do not fabricate scores.

For each reviewer task, require this order:

1. Read the whole source profile.
2. Read the whole extracted persona.
3. Inspect every field in original order; collect only flagged field findings in output, but report exact checked counts.
4. Score M1, M2, and M3 from field-level findings.
5. Step back and score M4 and M5 on the complete record.
6. Check cross-field contradictions for M6.
7. Assign M7 only after M1–M6.
8. Return JSON only, with concise reasons citing concrete field IDs and source columns/quotes.

## Step 4 — Validate each review

Before accepting a review, verify:

- `persona_id` exactly matches the packet.
- The actual model name is present.
- `checked_field_count` equals the packet's extracted field count.
- M1, M2, M4, M5, M6, and M7 are integers from 1 through 5.
- M3 is 1–5 or `"n/a"` only when no extracted field has a description.
- Reasons are non-empty and cite concrete evidence.
- No score was inferred from extraction confidence alone.
- The review contains no fields or source claims belonging to another persona.

Reject and retry invalid reviews rather than coercing arbitrary scores.

## Step 5 — Consensus and aggregation

After independent reviews finish, use [aggregate_reviews.py](./scripts/aggregate_reviews.py).

For each persona and metric, report:

- all individual model scores,
- unique majority score when one exists,
- median (may be `.5` with an even panel),
- minimum, maximum, and range,
- exact agreement indicator,
- disagreement flag when range is at least 2 or no unique majority exists.

Do not hide disagreement by averaging it away. Send disagreement cases to human adjudication, prioritizing M1, M2, M4, and M5.

Across the run, report:

- score distributions and means by metric and model,
- completed/failed/missing reviews,
- agreement rate by metric,
- count of personas requiring adjudication,
- recurring field IDs in value, grounding, over-claim, coverage, and consistency findings,
- sample seed, source/extraction fingerprints, rubric fingerprint, requested models, actual models, and concurrency.

## Required artifacts

A completed run should contain:

- `run_config.json`
- `packets/` — one source/extraction pair per persona
- `manifest.jsonl`
- `reviews/<persona_id>/<model>.json`
- `per_persona_consensus.jsonl`
- `per_persona_consensus.csv`
- `summary.json`
- `README.md` — concise methodology, limitations, model availability, failures, and headline results

## Reporting language

Distinguish clearly between:

- **Automated structural validity**: parseability, schema enums, duplicate IDs, missing fields.
- **Rubric quality**: M1–M7 judgments against the source profile.
- **Consensus**: agreement among independent model judges.
- **Human-calibrated quality**: only claim this after comparison with human annotations.

Never call an LLM-only score “ground truth” or “human validated.”
