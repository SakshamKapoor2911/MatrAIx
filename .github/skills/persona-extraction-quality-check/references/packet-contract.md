# Persona Review Packet Contract

All dataset adapters must produce this common packet so the judge protocol, parallel reviewer panel, validation, and aggregation remain dataset-independent.

## Required top-level shape

```json
{
  "packet_version": "1.0",
  "persona_id": "<globally unique stable string>",
  "identity": {},
  "source": {
    "path": "<source container>",
    "source_profile": []
  },
  "extracted_persona": {
    "origin": {},
    "metadata": {},
    "fields": []
  },
  "emitted_dimension_schema": [],
  "missing_schema_field_ids": [],
  "rubric_path": "<canonical rubric>"
}
```

## Invariants

1. One packet represents exactly one source person/user/respondent and one complete extracted persona.
2. `persona_id` is stable, unique within the run, and includes the dataset/source namespace.
3. `source.source_profile` contains the complete source material that the extractor was allowed to use. Do not truncate it for judging.
4. `extracted_persona.fields` contains the complete field list in original order. Do not split fields across packets.
5. `emitted_dimension_schema` contains the schema definition for every emitted `field_id` when available.
6. Source and extraction identities must be cross-checked before writing the packet. Any conflict is a hard error.
7. Source text and extracted fields must not come from different versions or filtering stages.
8. Packet creation is deterministic for fixed inputs, selection IDs/seed, and adapter version.

## Dataset adapters

### Stack Overflow

- Source: exact filtered survey CSV used by extraction.
- Primary join: extraction `response_id` ↔ source `ResponseId`.
- Cross-check: extraction `row_index` ↔ zero-based row in that exact filtered CSV.
- Source profile representation: ordered non-missing `{column, value}` pairs.
- Suggested persona ID: `stackoverflow-<year>-response-<ResponseId>`.
- Bundled adapter: `../scripts/prepare_persona_packets.py`.

### Wikipedia

- Source: the exact SQLite/JSONL profile set used by extraction, including complete `profile_text`.
- Primary join: `global_idx`; cross-check `qid`, `task_id`, `input_sha256`, or equivalent immutable identifiers when available.
- Source profile representation: full `profile_text` plus identifying metadata; do not substitute the extracted evidence snippets for the source.
- Suggested persona ID: `wikipedia-<dataset-version>-global-<global_idx>`.
- Future adapter: `prepare_wiki_packets.py` or an adapter registered in a shared packetizer.

### Amazon

- Source: the exact review history used by extraction, grouped by stable reviewer/user ID with the same ordering and preprocessing used to build the extractor's profile.
- Primary join: extraction `uuid`/reviewer ID ↔ source reviewer ID; cross-check review count and source hash when available.
- Source profile representation: complete ordered review history, preserving review text, rating, timestamp, and product context supplied to extraction.
- Suggested persona ID: `amazon-<dataset-version>-reviewer-<uuid>`.
- Future adapter: `prepare_amazon_packets.py` or an adapter registered in a shared packetizer.

## Adapter output validation

Before reviewer dispatch, validate:

- no duplicate `persona_id`,
- no unmatched selected extraction,
- no identity disagreement,
- no empty source profile,
- `fields` is a list of objects,
- packet field count matches the manifest,
- every packet records source and extraction origins,
- the run manifest and input fingerprints are written.

Only packet preparation is dataset-specific. The canonical rubric, judge protocol, multi-model dispatch, review JSON, consensus logic, and human-adjudication workflow must remain shared.
