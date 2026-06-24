# Persona Attribution — Developer Kit

You get a batch of Wikipedia person profiles and a list of persona **dimensions**
(each with a closed set of allowed values). For every profile, decide which
dimension values the text supports, with evidence. Send the results back.

You **work on `solver.py`**. Everything else is provided. The only hard rule is
that your output matches the contract — `conformance.py` enforces it, and both
sides run it, so the format we exchange is guaranteed to line up.

## The contract (what we exchange)

| direction | file | schema |
|---|---|---|
| owner → you | `tasks.jsonl` — one profile per line | [`schemas/task.input.schema.json`](schemas/task.input.schema.json) |
| owner → you | `dimensions.json` — the dimensions to fill | [`schemas/dimensions.schema.json`](schemas/dimensions.schema.json) |
| you → owner | `results.jsonl` — one record per line | [`schemas/result.output.schema.json`](schemas/result.output.schema.json) |

One result field:

```json
{ "field_id": "age_bracket",
  "value": "55–64",                       // one of that dimension's allowed values, verbatim, or null
  "confidence": 0.4,                       // number in [0, 1]
  "evidence": "(February 12, 1809 - ...)", // short quote copied from profile_text; required if value != null
  "assignment_type": "structured_claim" }  // direct | structured_claim | summary_inference | unsupported
```

Rules: `field_id` must be an id from `dimensions.json`; `value` must be one of
that id's allowed values (verbatim) or `null`; `global_idx` in your result must
equal the task's `global_idx` (that's how it's joined back). Omit a dimension
you didn't attempt; use `value: null` + `"unsupported"` for ones the text
doesn't support.

## Quickstart

```bash
cd personas/existing_data_curation/wiki_collab/collab_kit

# 1) Smoke test — mock backend, the bundled sample. Proves the pipeline + format.
./run.sh --tasks sample/tasks.jsonl --dimensions sample/dimensions.json \
         --out results.jsonl --backend mock

# 2) Check any results file against the contract (run this before sending back).
python3 conformance.py --results results.jsonl --dimensions sample/dimensions.json --tasks sample/tasks.jsonl

# 3) The real thing with your Claude subscription (claude already logged in):
export WIKI_COLLAB_CLAUDE_CMD="python3 ../claude_json_backend.py"
./run.sh --tasks tasks.jsonl --dimensions dimensions.json \
         --out results.jsonl --backend claude-code-acp --jobs 6
#   …or --backend codex-acp with WIKI_COLLAB_CODEX_CMD set to your Codex wrapper.
```

`harness.py` writes `results.jsonl` and runs the conformance check for you, so a
green run means you're ready to send.

## What you edit

**`solver.py`** — the one function `attribute(profile, dimensions) -> [field]`.
Change the prompt, the model/backend, the batching, add normalization or a
second pass, swap in your own API client — anything. The reference version
builds a prompt and calls the bundled backend adapters (`mock`,
`claude-code-acp`, `codex-acp`, `anthropic-api`, `openai-api`). As long as
`conformance.py` passes, your improvements are welcome.

Don't change the contract files (`schemas/`) or the record shapes — that's the
interface we agreed on. `harness.py` and `conformance.py` are provided; edit
only if you want to (e.g. different batching), but keep the output format.

## Files

```
collab_kit/
  README.md            you are here
  schemas/             the contract (input task, dimensions, output result)
  solver.py            << YOUR CODE: attribute(profile, dimensions) -> fields
  harness.py           tasks.jsonl + dimensions.json -> results.jsonl (calls solver)
  conformance.py       validates results.jsonl against the contract (both sides run it)
  run.sh               convenience wrapper for harness.py
  sample/              tasks.jsonl, dimensions.json, results.jsonl (a conformant example)
```

## For the owner

- Send each worker a `tasks.jsonl` (a disjoint slice of your dataset) + a
  `dimensions.json` (any subset of the 1339-dim catalog;
  `protocols/persona_attribution_by_category/<slug>/category_manifest.json`
  already has the `{id,label,description,values}` shape, and
  `personas/dimensions+new.json` is the full catalog).
- On return, run `conformance.py --results theirs.jsonl --dimensions dimensions.json --tasks tasks.jsonl`
  before ingesting. Same checker both sides ⇒ formats always match.
