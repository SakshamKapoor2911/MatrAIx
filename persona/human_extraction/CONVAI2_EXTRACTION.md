# ConvAI2 / PersonaChat -> MatrAIx 1,290 dimensions

This pipeline maps the 18,560 deduplicated personas in
`MatrAIx2026/MatrAIx2026/convai2_personas/personas.parquet` to the MatrAIx schema
using deterministic phrase rules only. No LLM or API is used.

The original persona sentences are the sole evidence source. The source table's
`domain` and `seniority_level` columns are upstream inferences and are excluded.
Placeholder names are also excluded. Every dimension without an explicit,
schema-compatible statement is emitted as `null` / `unsupported`.

Source license: CC BY 4.0, per ParlAI's PersonaChat task documentation.

## Download

```bash
huggingface-cli download MatrAIx2026/MatrAIx2026 \
  convai2_personas/personas.parquet --repo-type dataset \
  --local-dir data/matraix2026
```

## Prepare and validate a smoke test

```bash
python persona/human_extraction/scripts/prepare_convai2.py \
  --input data/matraix2026/convai2_personas/personas.parquet \
  --out out/convai2_profiles_5.jsonl --limit 5

python persona/human_extraction/scripts/postprocess_convai2.py \
  --profiles out/convai2_profiles_5.jsonl \
  --schema persona/schema/dimensions.json \
  --out out/convai2_personas_5.jsonl

python persona/human_extraction/scripts/validate_extraction.py \
  --input out/convai2_personas_5.jsonl \
  --schema persona/schema/dimensions.json \
  --profiles out/convai2_profiles_5.jsonl
```

## Full compressed JSONL extraction

Remove `--limit 5`, write a full profiles JSONL, then run:

```bash
python persona/human_extraction/scripts/postprocess_convai2.py \
  --profiles out/convai2_profiles_full.jsonl \
  --schema persona/schema/dimensions.json \
  --out convai2/extraction_v1/shard_00.jsonl.gz
```

The output contains one JSON object per persona and a `fields` list with exactly
1,290 ordered objects. Exact crosswalk matches are also collected in the
top-level `observed` object; all other dimensions remain null and unsupported.

> **Coverage note:** this rule-only extraction is intentionally sparse. It maps
> 0.262 dimensions per persona on average, and only 4,568 of 18,560 personas
> (24.6%) receive any mapping. Treat it as a high-precision observed layer, not
> a dense persona extraction. Rich ConvAI2 coverage requires the LLM extraction
> layer on top of these deterministic assignments.

## Current extraction statistics

- Personas / unique users: 18,560 / 18,560
- Fields per persona: 1,290
- Exact non-null assignments: 4,859
- Mean mapped dimensions per persona: 0.262
- Personas with at least one mapping: 4,568
- Invalid lengths or assignments: 0
- Output size: about 187 MB (gzip-compressed JSONL)
