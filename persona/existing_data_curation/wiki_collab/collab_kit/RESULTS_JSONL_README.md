# results.jsonl Format

`results.jsonl` is the file returned by a collaborator after running a
persona-attribution assignment. It is JSON Lines: each non-empty line is one
complete JSON object, and the file itself is not wrapped in `[]`.

The authoritative schema is `schemas/result.output.schema.json`. The practical
validator is `conformance.py`, which both the worker and owner should run before
the file is accepted.

## Top-Level Record

Each line represents one assigned profile. The minimum required shape is:

```json
{"global_idx": 0, "fields": []}
```

The runner normally writes this richer shape:

```json
{"global_idx":0,"task_id":"wiki_profile:0000000000","qid":"Q91","input_sha256":"...","model":"gpt-5.5","run":{"backend":"codex-acp","model":"gpt-5.5","effort":"high","runner_version":"1.0.0"},"fields":[{"field_id":"age_bracket","value":"55–64","confidence":0.8,"evidence":"short quote from profile_text","assignment_type":"structured_claim"}]}
```

Top-level keys:

| Key | Required | Type | Rule |
| --- | --- | --- | --- |
| `global_idx` | yes | integer | Must match the corresponding task row. This is the join key. |
| `fields` | yes | array | One object per attempted persona dimension. |
| `task_id` | no, but recommended | string | Mirrors the task row. Used for owner-side identity checks. |
| `qid` | no, but recommended | string | Mirrors the task row. Used for owner-side identity checks. |
| `input_sha256` | no, but recommended | string | Mirrors the task row. Used to detect swapped or edited inputs. |
| `model` | no | string or null | Backward-compatible mirror of `run.model`. |
| `run` | no, but recommended | object | Provenance for model/backend/effort/version. Missing provenance is a warning. |

`global_idx` values must not repeat within one `results.jsonl`.

## Field Records

Every object inside `fields` must contain all of these keys:

```json
{"field_id":"age_bracket","value":"55–64","confidence":0.8,"evidence":"short quote from profile_text","assignment_type":"structured_claim"}
```

Field keys:

| Key | Required | Type | Rule |
| --- | --- | --- | --- |
| `field_id` | yes | non-empty string | Must be an id from `dimensions.json`. No duplicate `field_id` within the same profile record. |
| `value` | yes | string or null | If the dimension has allowed values, this must match one allowed value exactly, or be `null`. |
| `confidence` | yes | number | Must be in `[0, 1]`. Booleans are invalid. |
| `evidence` | yes | string | Required. If `value` is not `null`, this must be non-empty. Prefer a short quote from `profile_text`. |
| `assignment_type` | yes | string | Must be one of `direct`, `structured_claim`, `summary_inference`, or `unsupported`. |
| `run` | no | object | Optional per-field provenance, used when resumed or mixed-backend runs produce different fields. |

Unattempted dimensions may be omitted. Dimensions that were checked but not
supported should be returned as `value: null` with `assignment_type: "unsupported"`.

## Assignment Types

Use one of these exact strings:

| Value | Meaning |
| --- | --- |
| `direct` | The profile text directly states the value. |
| `structured_claim` | The value is supported by a structured fact or close paraphrase in the profile. |
| `summary_inference` | The value is a cautious inference from multiple profile details. |
| `unsupported` | The profile does not support a non-null value for this dimension. |

For `unsupported`, use:

```json
{"field_id":"demo_marital_status","value":null,"confidence":0.0,"evidence":"","assignment_type":"unsupported"}
```

## Complete Example

A valid file with two lines:

```jsonl
{"global_idx":0,"task_id":"wiki_profile:0000000000","qid":"Q91","input_sha256":"abc123","model":"gpt-5.5","run":{"backend":"codex-acp","model":"gpt-5.5","effort":"high","runner_version":"1.0.0"},"fields":[{"field_id":"age_bracket","value":"55–64","confidence":0.8,"evidence":"short quote from profile_text","assignment_type":"structured_claim"},{"field_id":"demo_marital_status","value":null,"confidence":0.0,"evidence":"","assignment_type":"unsupported"}]}
{"global_idx":1,"task_id":"wiki_profile:0000000001","qid":"Q42","input_sha256":"def456","model":"gpt-5.5","run":{"backend":"codex-acp","model":"gpt-5.5","effort":"high","runner_version":"1.0.0"},"fields":[]}
```

The second line is format-valid, but an empty `fields` list means no dimensions
were attributed for that profile.

## Validation

From an unpacked assignment package, prefer:

```bash
./run_assignment.sh --validate
```

To run the checker directly:

```bash
python3 collab_kit/conformance.py \
  --results results.jsonl \
  --dimensions dimensions.json \
  --tasks tasks.jsonl
```

In the repository source tree:

```bash
python3 persona/existing_data_curation/wiki_collab/collab_kit/conformance.py \
  --results results.jsonl \
  --dimensions dimensions.json \
  --tasks tasks.jsonl
```

Exit code meanings:

| Code | Meaning |
| --- | --- |
| `0` | No blocking format errors. |
| `1` | Contract violations were found. |
| `2` | Bad checker invocation. |

## Common Rejection Reasons

- The file is a JSON array instead of JSON Lines.
- A line is not valid JSON.
- `global_idx` is missing, not an integer, duplicated, or outside the assigned tasks.
- `fields` is missing or is not a list.
- A field is missing one of `field_id`, `value`, `confidence`, `evidence`, or `assignment_type`.
- `field_id` is not in `dimensions.json`.
- `value` is not a string or `null`.
- `value` does not exactly match the allowed values for that dimension.
- `confidence` is outside `[0, 1]` or is a boolean.
- `assignment_type` is not one of the four allowed strings.
- `value` is non-null but `evidence` is empty.
- The same `field_id` appears more than once in one profile record.
