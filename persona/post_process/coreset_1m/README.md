---
pretty_name: MatrAIx Persona 1M Public Release
task_categories:
- text-generation
tags:
- persona
- coreset
- synthetic
- survey
- parquet
size_categories:
- 100K<n<1M
---

# MatrAIx Persona 1M Public Release

This dataset is a deterministic, quality-filtered and deduplicated 1,000,000-row
coreset of the MatrAIx 8.4B persona corpus. It contains exactly **600,000
human-grounded personas (60%)** and **400,000 synthetic personas (40%)**.

## Build status and interpretation

The production build is submitted from the accepted 8,399,989,719-row unified
snapshot. That snapshot omits 10,289 rows from one failed Wiki task, but retains
1,936,153 Wiki rows, well above the 323,438 required for this coreset.

The 60/40 human-grounded/synthetic split is a data-product design choice, not an
estimate of a real-world source ratio. Calibration is a best-effort match to
the listed one-dimensional population margins among personas where each field
is known. It does not impute missing fields, guarantee a representative joint
distribution, or remove source-selection bias. The build records known and
missing counts plus achieved marginal errors in `audit.json` and `RESULTS.md`.

The initial array-based production DAG (`33781136`, `33781139`, `33781143`, and
`33781144`) was cancelled before any task started. The production build uses one
small CPU job followed by one dependent upload job. It scans all approximately
2.21M available human-grounded rows for the four calibration fields. For the
synthetic candidate pool, it uses one seed-selected Parquet file and row group
from 40 distinct seed-selected synthetic shards, yielding approximately 2.2M
distributed candidates before selecting 400,000. The selected shards, file
parts, and row-group positions are deterministic for seed `20260720` and are
spread across the corpus rather than always taking the beginning of each shard.

The production seed selects exactly 2,187,354 synthetic candidates across 40
shards, 16 Parquet part positions, and 34 row-group positions. The active
production chain is:

| Stage | Slurm job | State at submission |
|---|---:|---|
| Calibrated 1M build | `33782802` | Cancelled before starting to rename this document |
| Hugging Face upload | `33782808` | Cancelled with its unstarted build dependency |
| Replacement calibrated build | `33783087` | Submitted after README rename |
| Replacement Hugging Face upload | `33783089` | Pending on successful replacement build |

This simplification changes only candidate I/O and scheduling. The build still
performs one global deterministic calibration: it selects 323,438 Wiki rows to
move the human-grounded component toward the target margins, computes the
remaining demographic residual after all 600,000 human-grounded rows, and then
selects 400,000 synthetic rows to reduce that residual. It writes known/missing
counts and achieved errors to `audit.json` and `RESULTS.md`.

The Hugging Face target is:

```text
https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M_Public_Release/tree/main
```

Legacy contents were removed before this run in Hugging Face commit
`a75d403bc834c80c90c9cd76e725a8c9d73e84df`; only `.gitattributes` remains until
the new build uploads.

## Source composition

| Source | Rows | Inclusion rule |
|---|---:|---|
| Wiki extraction | 323,438 | Calibrated sample from 1,936,153 available retained rows |
| Amazon Review extraction | 97,915 | All retained rows |
| Stack Overflow survey extraction | 113,120 | All retained rows |
| PRISM Alignment | 1,487 | All retained rows |
| GSS | 63,532 | All retained rows |
| Real Human Survey | 508 | All rows |
| Full-DAG synthetic | 400,000 | Calibrated sample from 40 seed-selected source shards |

“Human-grounded” means derived from a real profile, history, respondent, or
survey record. It does not mean every model-extracted attribute is a verified
fact. Wiki, Amazon, Stack Overflow, and PRISM descriptions/evidence can contain
model extraction errors. GSS and Survey mappings depend on crosswalk quality.

## Calibration method

The build uses constrained, without-replacement calibration rather than trying
to reproduce a full joint world distribution that is not observed in any
single source.

1. Apply the upstream contradiction filter and 0.95 MinHash deduplication.
2. Include every retained row from the five smaller human-grounded products.
3. Fit bounded inclusion weights for Wiki against evidence-supported global
   marginal targets.
4. Compute the human sample's known-value counts. Missing attributes remain
   missing and are never imputed merely to satisfy a quota.
5. Convert each global target into a synthetic residual target. If $h_{dv}$ is
   the human count for value $v$ of dimension $d$, then the desired synthetic
   count is

   $$r_{dv}=p_{dv}(H_d+400{,}000)-h_{dv}.$$

   Negative residuals are clipped and the remainder is projected back onto the
   400,000-row simplex; clipped mass is reported as infeasibility rather than
   hidden.
6. Draw an approximately 2.2M-row synthetic candidate pool by selecting 40
   distinct shards with the fixed seed, then selecting one Parquet file and one
   row group within each shard. Calibrate and sample 400,000 rows from this
   distributed pool.
7. Use deterministic exponential-race priorities for weighted sampling without
   replacement. At every calibration iteration, solve $t$ so that

   $$\sum_i (1-e^{-t w_i})=n,$$

   then update category weights using the resulting fixed-size inclusion
   probabilities. Stable source row IDs and seed `20260720` make the result
   reproducible and input-order independent.

This approach is efficient because optimization sees only a few integer
calibration codes per candidate. Full 1,290-attribute rows, descriptions, and
grounding are read only for selected records.

## Calibration scope and evidence

The hard evidence scope is global population in 2024:

- `age_bracket`: UN World Population Prospects 2024.
- `region`: UN WPP 2024 with the repository's documented region crosswalk.
- `gender_identity`: UN binary sex totals anchor only Woman/Man. The small
  non-binary/self-described/prefer-not-to-say tail is a schema prior, not a UN
  estimate. This target is therefore medium confidence.
- `urbanicity`: World Bank WDI/UN urban share; the split among dense urban,
  suburban, and small town retains the schema prior and is medium confidence.

The evidence bundle proposed in `MatrAIx2026/Existing_Data` discussion #59 is
well curated: it pins ACS PUMS, BLS OEWS, O*NET, UN WPP, ILOSTAT, World Bank
WDI, CLDR, Glottolog, and Stack Overflow sources with checksums and license
records. We deliberately do **not** hard-calibrate language from CLDR (metadata
is not population prevalence), nor education/employment from unconditional
marginals (they require age/region conditioning). GSS, WVS, Pew, and IPIP raw
files were also excluded from that bundle where redistribution permission was
uncertain.

Calibration matches each dimension among rows where that dimension is known.
It does not claim the resulting joint distribution is a statistically
representative survey sample. Marginal targets can conflict, real-grounded
sources have selection bias, and schema categories are coarser than source
statistics. `calibration_targets.json` is the machine-readable contract;
`audit.json` records feasibility and source diagnostics.

## Columns

The Parquet files preserve the unified Persona8B representation:

- `source`, `source_row_index`, `source_record_id`: provenance.
- `attributes`: 645-byte packed vector for 1,290 categorical attributes.
- `null_bitmap`: missing-attribute bitmap; null means no attributes are missing.
- `attribute_overrides`: exact legacy values outside the current codebook.
- `populated_attribute_count`: number of non-null attributes in this row.
- `has_description`, `description_count`, `descriptions`: field-level natural
  language availability and text. Synthetic personas are skeletons and have no
  generated descriptions.
- `grounding`: sparse evidence, confidence, and assignment type.
- `metadata_json`: source-specific metadata.

Decode packed attributes with `persona_codes.schema.json`: field $i$ uses the
low nibble when $i$ is even and the high nibble when $i$ is odd. Apply the null
bitmap and then sparse overrides.

## Files and reproducibility

`data/` contains ten 100K-row Zstandard-compressed Parquet shards. `manifest.json`
contains exact source counts, byte sizes, and SHA-256 hashes. `RESULTS.md`
summarizes the completed build. The implementation and tests live under
`persona/post_process/coreset_1m/` in the MatrAIx repository.

Source licenses and terms continue to apply. Do not treat model-generated
descriptions or inferred sensitive attributes as independently verified facts.