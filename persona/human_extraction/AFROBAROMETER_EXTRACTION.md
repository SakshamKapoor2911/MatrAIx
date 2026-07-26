# Afrobarometer Round 9 -> MatrAIx 1,290 dimensions

This pipeline maps the derived 53,384-row Afrobarometer persona parquet to the
MatrAIx schema using only deterministic crosswalk rules. No LLM, API key, model
server, inferred layer, or token budget is required. Every dimension without an
exact source mapping is emitted as `null` with `assignment_type="unsupported"`.

The source `name` is synthetic, and `domain`/`seniority_level` may be inferred.
They are deliberately not exact overlays.  Source `65+`, generic `urban`,
`tertiary`, and `postgraduate` categories are also too coarse for a single target
enum and remain null unless supported more precisely by evidence.

## 1. Download

The Hugging Face dataset is authenticated.  Log in first if necessary:

```bash
huggingface-cli login
huggingface-cli download MatrAIx2026/MatrAIx2026 \
  afrobarometer/afrobarometer_round9.parquet --repo-type dataset \
  --local-dir data/matraix2026
```

## 2. Prepare and test five people

```bash
python persona/human_extraction/scripts/prepare_afrobarometer.py \
  --input data/matraix2026/afrobarometer/afrobarometer_round9.parquet \
  --out out/afrobarometer_profiles_5.jsonl --limit 5
```

Create the complete 1,290-field records directly from the observed mappings:

```bash
python persona/human_extraction/scripts/postprocess_afrobarometer.py \
  --profiles out/afrobarometer_profiles_5.jsonl \
  --schema persona/schema/dimensions.json \
  --out out/afrobarometer_personas_5.jsonl
```

## 3. Validate

```bash
python persona/human_extraction/scripts/validate_extraction.py \
  --input out/afrobarometer_personas_5.jsonl \
  --schema persona/schema/dimensions.json \
  --profiles out/afrobarometer_profiles_5.jsonl
```

The postprocessor selects Parquet output when `--out` ends in `.parquet`; otherwise
it writes JSONL. The existing validator consumes JSONL, so use a `.jsonl` smoke-test
output for that command. The validator must report zero errors.

## 4. Run all 53,384 people

Remove `--limit 5`, prepare a new full profiles file, and run the same rule-only
postprocessor and validator against it. Runtime is local CPU/file-processing time;
there are no API calls or model costs.

For the canonical compressed JSONL deliverable, use:

```bash
python persona/human_extraction/scripts/postprocess_afrobarometer.py \
  --profiles out/afrobarometer_profiles_full.jsonl \
  --schema persona/schema/dimensions.json \
  --out afrobarometer/extraction_v1/shard_00.jsonl.gz
```

Every field includes `provenance`: `observed` for exact crosswalk values and
`unobserved` for null dimensions.
