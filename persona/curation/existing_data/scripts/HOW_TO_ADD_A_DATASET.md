# How to standardize a dataset into the 1290-dim schema

A step-by-step guide for mapping an existing persona dataset onto MatrAIx's **1,290-dimension**
schema (`persona/schema/dimensions.json`) using the shared toolkit in this folder — so you write a
small **crosswalk**, not a whole pipeline. Worked example: [`crosswalks/prism.py`](crosswalks/prism.py)
(the PRISM extraction was built exactly this way).

## The method: two faithful layers + §8

| Layer | What | Tool |
|---|---|---|
| **1. Observed (exact)** | fields the source *states* (demographics, coded survey answers) → exact schema values | [`crosswalk_engine.py`](crosswalk_engine.py) |
| **2. Inferred** | the remaining ~1,290 dims, inferred from the persona's free text, grounded in verbatim quotes | LLM pass (team's evidence-grounded prompt) |
| **3. Normalize (§8)** | demote absence/ungrounded values, null off-allowed, overlay the exact dims | [`postprocess_engine.py`](postprocess_engine.py) |

**Faithfulness is the rule** (see `../../../human_extraction/docs/BENCHMARK.md` §8): unobserved → `null`;
a mapped value **must** be in the dim's allowed set; nothing is invented — unreliable inferences are
demoted to `unsupported`, never forced to a "reasonable-looking" value.

## Steps

**1. Explore your source.** Decide which fields map *cleanly* to a schema dim (→ crosswalk) vs which
need inference (→ LLM). Coded surveys (GSS, Afrobarometer) are mostly crosswalk; free-text sources
(reviews, conversations) lean on the LLM layer.

**2. Write a crosswalk** — copy `crosswalks/prism.py` to `crosswalks/<yourdataset>.py`:
```python
CROSSWALK = {
    "<dim_id>": {"src": "<source_field>", "map": {"<src value>": "<target>" | None}, "prov": "observed"},
    "<dim_id>": {"compute": lambda row: "<target>" | None, "prov": "observed"},  # multi-field/derived
}
```
`map` value `None` = present-but-deliberately-unmapped → null (e.g. a bucket too coarse for the schema).
Nest-heavy sources: flatten the row first (surface `a.b` as `a_b`). Verify with `python crosswalks/<yourdataset>.py --selftest`.

**3. Render a faithful `profile_text`** per persona — the natural-language text the LLM will ground
on. Include **only** facts the source states (demographics + verbatim self-description / free text);
omit missing fields, never fabricate.

**4. Run the inferred layer.** Feed each `profile_text` through the team's evidence-grounded prompt
(per-category chunking, ≤50 dims/chunk = 53 chunks, `max_tokens=8192`) — via the wiki/Amazon
`run_extraction.py` (vLLM) or an OpenAI-compatible API. Output per persona: `{user_id, fields:[...]}`,
each field `{field_id, value, confidence, evidence, description, assignment_type}`.

**5. Compose the layers + normalize (§8):**
```python
from postprocess_engine import load_schema, normalize
from crosswalk_engine import apply_crosswalk
from crosswalks.yourdataset import CROSSWALK

order, allowed = load_schema("persona/schema/dimensions.json")

for row in source_rows:
    row = flatten(row)                                             # your flattener (if nested)
    observed, prov, unmapped = apply_crosswalk(row, CROSSWALK, allowed)   # layer 1 (exact)
    profile_text = render(row)                                     # your renderer (faithful NL)
    raw_fields = llm_extract(profile_text)                        # layer 2 (LLM)
    fields = normalize(raw_fields, order, allowed,                # layer 3 (§8 + exact overlay)
                       profile_text=profile_text, observed=observed)
    emit({"user_id": row["id"], "fields": fields, "observed": observed})
```

**6. Validate — must be 0 errors:**
```
python persona/human_extraction/scripts/validate_extraction.py \
    --input <dataset>/extraction_v1/shard_00.jsonl.gz \
    --schema persona/schema/dimensions.json --profiles <profiles.jsonl>
```

**7. Upload** to `MatrAIx2026/MatrAIx-1290-extractions` following that repo's `CONTRIBUTING.md`
(one folder per dataset, `extraction_v1/` shard + `manifest.json`, PR for review).

## Checklist
- [ ] crosswalk written + `--selftest` passes
- [ ] `profile_text` is faithful (no invented facts)
- [ ] LLM layer run over all 1,290 dims (53 chunks)
- [ ] `normalize()` applied (§8 + observed overlay)
- [ ] `validate_extraction.py` → 0 errors
- [ ] uploaded per `CONTRIBUTING.md`

Questions → see the PRISM worked example, or ping the `team-coordinator` channel.
