# PRISM Persona Extraction — Handoff / Runbook

Goal: standardize the **1,500 real users** of the PRISM Alignment Corpus into
MatrAIx's **1,290-dimension** persona schema (`persona/schema/dimensions.json`),
one persona = one PRISM survey respondent. Field schema is **identical to the
wiki/Amazon extractors**; the run is **resumable, idempotent, and self-healing**.

## Status (2026-07-14)
- ✅ Complete: 1,500 / 1,500 personas extracted, post-processed, audited.
- Output: `prism_personas_v1.jsonl` (full) + `prism_sample_100.jsonl` (sample).
- 1,494/1,500 have all 53 chunks; 6 lost 1–2 chunks to transient blips (filled to
  1,290 with `null`/`unsupported` by post-processing — every record has 1,290 fields).

## Method (two layers + team §8 post-processing)
1. **Rule-based observed overlay** (`render_prism_profiles.py`): 9 demographic dims
   (age, gender, education, marital, employment, English proficiency, ethnicity,
   religion, region) mapped **exactly** from PRISM survey fields → allowed schema
   values. Provenance = ground truth; overrides the LLM. (~8.7 exact dims/persona.)
2. **LLM extraction** (`run_extraction_api.py`): the team's **evidence-grounded
   prompt** (reused verbatim from `human_extraction`), 53 per-category chunks
   (≤50 dims), `max_tokens=8192`, emit-all. Input = a faithful `profile_text`
   (demographics + the user's verbatim self-description + their stated AI
   preferences). One JSON object per dim: `{field_id, value, confidence, evidence,
   description, assignment_type}`.
3. **Post-processing** (`postprocess.py`) — applies **BENCHMARK.md §8** verbatim:
   absence/ungrounded values → `assignment_type=unsupported` + evidence dropped;
   off-allowed values → nulled; exact observed dims win. Nothing fabricated;
   unreliable inferences are demoted, not deleted.

## Model — deliberate upgrade, documented
- **Qwen3-235B-A22B** (2507 release, text-only) via an OpenAI-compatible API
  proxy, **not** the team's Qwen3.6-35B-A3B.
- Why: the 35B-A3B is **not deployed** on the available proxy, and 235B
  is a strict quality upgrade. Quality validated against the team's own §8 scoring:
  **~178 grounded attributions/persona here vs the team's ~182** — on par, same
  methodology.

## Infra — API, not vLLM (no GPU needed)
- Pure Python **stdlib** client (`urllib`); no `openai`/`vllm`/pip deps.
- **Token-paced** under the key's **200K TPM** limit via a `TokenBucket`
  (target 180K/min, 10% margin) → never 429s. Concurrent (`--workers 22`),
  **resumable + self-healing** (drops partial/dup records, redoes them).
- Cost ≈ **$130–230** (well under the key's $10K budget); wall-time ≈ **16 h**
  (purely TPM-limited, not compute-limited).

## Key files
- `render_prism_profiles.py` — PRISM survey → `profile_text` + exact observed dims (CPU, no key).
- `run_extraction_api.py` — LLM extractor (stdlib, throttled, resumable).
- `postprocess.py` — §8 normalization → team-format `prism_personas_v1.jsonl`.
- `audit_extraction.py` — validity/grounding audit.
- Schema: `persona/schema/dimensions.json` (1,290 dims).

## Reproduce
```bash
# 1. build profiles (downloads PRISM survey.jsonl from HF, public)
python3 render_prism_profiles.py --out out/prism_profiles.jsonl
# 2. extract (set LLM_API_KEY + LLM_API_BASE_URL in your shell first; ~16 h, resumable)
python3 run_extraction_api.py --profiles out/prism_profiles.jsonl \
    --model '<the Qwen3-235B-A22B model id your proxy exposes>' \
    --out out/prism_extracted.jsonl --workers 22 --max-tokens 8192 --tpm 180000
# 3. post-process to team format
python3 postprocess.py --in out/prism_extracted.jsonl --out out/prism_personas_v1.jsonl
```

## Output format
One JSON object per user, field schema identical to wiki/Amazon:
`{user_id, source:"PRISM", model, fields:[{field_id, value, confidence, evidence,
description, assignment_type} × 1290], observed:{dim:value}}`.
`observed` is our value-add (exact demographics) — additive, harmless to consumers
expecting only `fields`.

## Results
- 1,500 personas · avg **178 grounded** + **8.7 exact** attributions/persona · rest null.
- assignment_type: direct 87,640 · structured_claim 33,954 · summary_inference 145,489.
- Top categories filled: Linguistic/Communication, Big-Five, Values & Motivation,
  Character, Demographics, Worldview, Life Events, Expertise, AI Workflow/Adoption.

## Known caveats
- 6 profiles under-emitted 1–2 chunks (model quirk / transient); filled to 1,290 null.
- §8 residual: a few absence-values with plausible-but-off evidence may survive as
  low-confidence positives — treat `confidence`/`assignment_type` as weak signals,
  as the team advises. Grounded positive value+evidence+description are trustworthy.
