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
| owner → you | `assignment.json` — metadata and hashes | plain JSON |
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
# From an unpacked assignment package:
./run_assignment.sh

# Direct commands if you do not want the menu:
./run_assignment.sh --configure
./run_assignment.sh --status
./run_assignment.sh --backend mock --model mock-model --effort high --jobs 2 --yes --run
./run_assignment.sh --backend claude-code-acp --model claude-opus-4-8 --effort high --jobs 6 --yes --run
./run_assignment.sh --backend codex-acp --model gpt-5.5 --effort high --jobs 4 --yes --run
./run_assignment.sh --validate
```

`run_assignment.sh` verifies package checksums before every action, saves
settings in `.wiki_collab_settings.yaml`, writes `results.jsonl`, and runs the
conformance check for you. A green run means you're ready to send that file
back.

## Run on your own account (auth)

The default method (the prompt in `solver.py`) is the same one the owner uses.
The code is identical for everyone — only your credentials differ. Pick the
backend that matches what you have; nothing to edit:

| you have | backend | how to authenticate |
|---|---|---|
| a **Claude subscription** | `--backend claude-code-acp` | log in once with the `claude` CLI; the kit calls it for you |
| a **Codex subscription** | `--backend codex-acp` | log in once with the `codex` CLI; the kit calls it for you |
| an **Anthropic API key** | `--backend anthropic-api` | `export WIKI_COLLAB_ANTHROPIC_CMD='<your wrapper>'` |
| an **OpenAI API key** | `--backend openai-api` | `export WIKI_COLLAB_OPENAI_CMD='<your wrapper>'` |
| nothing / just testing | `--backend mock` | none (writes all-`unsupported`, proves the pipeline) |

Each wrapper command reads the prompt on stdin and prints one JSON object with a
`fields` array on stdout. The bundled Claude and Codex adapters are pure
stdlib. You can still override commands with `WIKI_COLLAB_CLAUDE_CMD` or
`WIKI_COLLAB_CODEX_CMD`.

Pick the model and reasoning effort with `--model` and `--effort`:

```bash
./run_assignment.sh --backend claude-code-acp --model claude-opus-4-8 --effort high --jobs 6 --yes --run
```

## Pause, resume, and progress

The run is **resumable**. Every finished (profile × category) unit is
checkpointed to `<out>.progress.jsonl`, so you can stop any time — Ctrl-C, or
your model quota runs out — and **just run the exact same command again later**
to continue. Finished units are skipped; only the remaining ones are attempted.
A unit that errors (e.g. a 429) is left pending and retried on the next run.

```bash
# how far along am I? (reads the checkpoint, runs nothing)
./run_assignment.sh --status

# start over, discarding progress
./run_assignment.sh --restart --backend claude-code-acp --model claude-opus-4-8 --effort high --jobs 6 --yes --run
```

`results.jsonl` is rewritten from the checkpoint on every run, so it always
reflects what is done so far. When all units are done, the harness runs the
conformance check and tells you it is ready to send.

## What you edit

**`solver.py`** — the one function `attribute(profile, dimensions) -> [field]`.
It ships with the owner's **default extraction method** (the prompt in
`build_prompt`) so it works out of the box on any backend above. You are
encouraged to **improve it**: change the prompt, the model/backend, the
batching, add normalization or a second pass, swap in your own API client —
anything. As long as `conformance.py` passes, your improvements are welcome.

Don't change the contract files (`schemas/`) or the record shapes — that's the
interface we agreed on. `harness.py` and `conformance.py` are provided; edit
only if you want to (e.g. different batching), but keep the output format.

## Files

```
collab_kit/
  README.md             you are here
  schemas/              the contract (input task, dimensions, output result)
  solver.py             << YOUR CODE: attribute(profile, dimensions) -> fields
  harness.py            tasks.jsonl + dimensions.json -> results.jsonl (calls solver)
  assignment_runner.py  package menu, settings, checksums, run/status/validate
  conformance.py        validates results.jsonl against the contract (both sides run it)
  backends.py           backend adapters (mock / claude / codex / api) — bundled, stdlib only
  claude_json_backend.py  CLI adapter: uses YOUR Claude subscription
  codex_json_backend.py   CLI adapter: uses YOUR Codex subscription
  run.sh                convenience wrapper for harness.py
  sample/               tasks.jsonl, dimensions.json, results.jsonl (a conformant example)
```

## For the owner

- Send each worker a `tasks.jsonl` (a disjoint slice of your dataset) + a
  `dimensions.json` (any subset of the 1339-dim catalog;
  `protocols/persona_attribution_by_category/<slug>/category_manifest.json`
  already has the `{id,label,description,values}` shape, and
  `personas/dimensions+new.json` is the full catalog).
- Prefer `scripts/make_collab_package.py` to create the package. It writes
  `assignment.json`, `package_manifest.json`, hashes the outgoing files, copies
  this kit, and emits a `.tar.gz` that is ready to send.
- On return, run `conformance.py --results theirs.jsonl --dimensions dimensions.json --tasks tasks.jsonl`
  before ingesting. Same checker both sides ⇒ formats always match.
- Merge everyone's returns with `scripts/merge_collab_results.py` (repeat
  `--results` and `--package-manifest` per worker). With `--db` it verifies each
  `global_idx`/`task_id`/`qid`/`input_sha256` against the source SQLite, unions
  fields per profile, reports value conflicts, and tallies the model/effort/
  version each return was produced with. Each returned record carries that
  provenance in its `run` block.
