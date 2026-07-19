# Chatbot eval artifacts (platform-managed)

Playground **auto / host / user-sim** runs produce two artifact roots:

| Root | Writer | Purpose |
|------|--------|---------|
| `/app/output/` | Harness / sidecar | Conversation trace and eval-run summary |
| `verifier/` | Task verifier (`tests/test_state.py` or `tests/test.sh`) | Pass/fail and structured trial evaluation |

Neither root is a SUT API contract and neither is a task-contributor output
responsibility beyond implementing the verifier. The harness and verifier
produce these files for traceability, UI debrief, and downstream scoring.

Task `instruction.md` files describe **how to interact with the chatbot** only.
They should not ask the agent to save files under `/app/output/` — harness and
verifier artifacts are platform-managed (below).

## Where `/app/output/` lives

`/app/output/` is Harbor's **logical container path**, not necessarily a literal
directory on the host.

| Environment | Resolved path |
|-------------|---------------|
| Docker trial | `/app/output/` inside the main container |
| Host trial (`user_sim_chat`) | `jobs/<job>/<trial>/artifacts/app/output/` |

Harbor rewrites `/app/output/...` in shell commands to the resolved path. The
verifier reads the same directory through `PLAYGROUND_OUTPUT_DIR` /
`MATRIX_OUTPUT_DIR`, which the host environment sets to that mapped location.

Collected artifacts also appear under `jobs/<job>/<trial>/artifacts/app/output/`
after a trial completes.

## Playground auto / user-sim writes harness artifacts

Playground chat jobs use the **`persona-user-sim`** agent (`user_sim_chat`
trial profile). That agent drives the multi-turn chat loop and **automatically
writes** harness artifacts after the conversation:

- `transcript.json` — fetched from the sidecar/API and normalized
- `application_result.json` — slim eval-run summary
- `user_feedback.json` — persona self-report from `input/self_report_schema.yaml`

The agent does not read task `instruction.md` for artifact I/O. Manual save steps
in older instructions were redundant for this path and have been removed from
chatbot tasks.

Non–user-sim agents (for example manual `curl` smoke runs) may still need to
write `/app/output/` themselves; on host trials the path is rewritten as above.

## Where `verifier/` lives

In a normal Harbor trial:

`jobs/<job>/<trial>/verifier/`

Harbor sets `HARBOR_VERIFIER_DIR` to that path before running the verifier.
Playground reads `verifier/structured_output.json` and `verifier/reward.txt`
from the trial directory for debrief and aggregation.

When running a verifier locally outside Harbor, the task falls back to
`<task-root>/verifier/` if `/logs/verifier` cannot be created. Do **not**
commit these directories; they are runtime output. If you run a verifier from
the repo root without setting `HARBOR_VERIFIER_DIR`, a stray `./verifier/` may
appear at the cwd — delete it or rerun from the task folder.

## Harness artifacts (`/app/output/`)

### `transcript.json`

Conversation record for the trial. Includes user/assistant turns and any structured
fields the task exposes via `input/chatbot.yaml` `structuredExposure.fields[]`
(list capability id `structured_exposure` in `capabilities`; it is also
auto-added when those fields exist; selectors are the source of truth for
concrete field names).

Harness may stamp run metadata on the root object:

- `sessionId`: eval session handle (from the sidecar/API when available, otherwise harness-generated)
- `applicationId`: configured application under test
- `applicationContext`: configured scenario label

Task-specific structured data (tool plans, persona-visible sidecars, etc.) live on
individual turns in `transcript.json`, not in `application_result.json`.

### `application_result.json`

Slim **eval-run summary** written by the Playground harness after the chat loop:

| Field | Meaning |
|-------|---------|
| `sessionId` | Same session handle as `transcript.json` |
| `applicationId` | Configured application id for this run |
| `applicationContext` | Configured scenario / context label |
| `turnCount` | Number of completed user/assistant turns |

Do **not** add SUT-specific fields here. Objective task metrics belong in
`verifier/structured_output.json` (below); subjective feedback belongs in
`user_feedback.json` (see task `input/self_report_schema.yaml`).

### `user_feedback.json`

Written by the persona self-report step when the task defines
`input/self_report_schema.yaml`. Field semantics live in that YAML file.

Common fields across chatbot tasks:

| Field | Meaning |
|-------|---------|
| `needConstraintSatisfaction` | `yes` / `partially` / `no` |
| `personalPreferenceSatisfaction` | `yes` / `partially` / `no` |
| `overallExperienceRating` | integer 1–10 |
| `reason` | short persona-voice explanation |
| `askedUsefulClarificationQuestions` | boolean |
| `clarifyingNotes` | which clarifications helped, or why not |
| `trustLevel` | optional integer 1–10 |
| `feltUnderstood` | optional boolean |

The task verifier reads this file and copies normalized facets into
`verifier/structured_output.json` under a `user_feedback` context (for example
`clarification_questions_useful`, `feedback_reason`, `trust_level`) per the
[`README.md`](README.md) reporting contract.

## Verifier artifacts (`verifier/`)

Written after the trial by the task verifier. Common files:

| File | Meaning |
|------|---------|
| `reward.txt` | `1` = verifier passed, `0` = failed |
| `structured_output.json` | Structured trial evaluation for reporting and UI debrief |
| `test-stdout.txt` | Captured verifier stdout (Harbor runs) |

### `structured_output.json`

Machine-readable evaluation report. Follow the shared chatbot contract in
[`README.md`](README.md) (`contexts[]`, `facets[]`, `taskType: "chatbot"`).
Typical contents:

- `presenceCheck`: required artifacts found or missing (e.g. `transcript.json`)
- `sourceArtifacts`: paths to inputs the verifier read (`transcript.json`,
  `user_feedback.json`, …)
- `contexts`: normalized metrics such as `task_outcome`, `conversation_summary`,
  and `user_feedback`

Do **not** duplicate this shape in per-task docs. Contributors implement the
verifier and emit contexts that match the shared contract; batch reporting and
Playground UI consume the normalized shape from the trial `verifier/` directory.
