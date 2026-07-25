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
| Replacement calibrated build | `33783087` | Running since 2026-07-21 02:37 EDT |
| Replacement Hugging Face upload | `33783089` | Pending on successful replacement build |

### Progress update: 2026-07-21 02:55 EDT

- Build `33783087` has run for approximately 18 minutes on one CPU with a 24 GB
   memory allocation. The live process is active at about 74% CPU and 296 MB RSS;
   stderr and stdout remain empty.
- The process has read approximately 809 MB through the four-field candidate
   scan and is currently CPU-bound with no further read or write growth. This is
   consistent with the first iterative calibration stage rather than a stalled
   process.
- No output directory or Parquet file exists yet. The build intentionally
   creates the output only after human and synthetic candidate calibration has
   completed.
- Expected remaining phases are synthetic candidate scan/calibration, selected
   row materialization into ten 100K Parquet files, SHA-256/manifest generation,
   final validation, and the dependent upload.
- Based on a same-implementation four-margin benchmark and current production
   behavior, the build is expected to complete in roughly 1.5-4 hours from its
   start; a conservative pathological-convergence bound is 4-6 hours. The Slurm
   limit is eight hours.
- Upload job `33783089` is correctly pending on `afterok:33783087`. The expected
   1M release size is approximately 5-6 GB, so upload should normally take about
   10-30 minutes after the build succeeds.

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

## Calibration mechanics with examples

### Shared sample weights, not one greedy decision at a time

Calibration does not add one persona to the final pool and then immediately
update all realized counts. Instead, every candidate persona has one shared
positive sampling weight $w_i$. Age, region, gender identity, and urbanicity all
update that same weight. After those weights approximately satisfy all supplied
margins in expectation, the build performs one fixed-size, without-replacement
sample.

For category $v$ of dimension $d$, the basic multiplicative update is

$$
w_i \leftarrow w_i\frac{T_{dv}}{E_{dv}}
\quad\text{for candidates }i\text{ with }x_{id}=v,
$$

where $T_{dv}$ is the target expected count and $E_{dv}$ is the current expected
count. A category that is overrepresented receives a factor below one; an
underrepresented category receives a factor above one.

The expected counts use fixed-size inclusion probabilities rather than raw
candidate counts. Given current weights, the algorithm solves $t$ such that

$$
\pi_i=1-e^{-t w_i},
\qquad
\sum_i\pi_i=n,
$$

where $n$ is the required sample size. The current expected count for one
category is

$$
E_{dv}=\sum_{i:x_{id}=v}\pi_i,
$$

and its target count is $T_{dv}=n p_{dv}$ for target share $p_{dv}$.

### Numerical age example

Suppose a pool has 100 candidates and the build must select 20. The pool has 80
Young and 20 Old candidates, while the desired age margin is 60% Young and 40%
Old. With equal initial weights, each candidate initially has expected inclusion
probability 0.2, so the expected sample is:

| Age | Current expected count | Target count | Update factor |
|---|---:|---:|---:|
| Young | 16 | 12 | $12/16=0.75$ |
| Old | 4 | 8 | $8/4=2.00$ |

All Young weights are multiplied by 0.75 and all Old weights by 2.00. This does
not yet select anyone; it changes their relative inclusion probabilities.

### Why all margins must be revisited

Now also require a 50% Urban and 50% Rural margin. After the age update, suppose
the expected sample contains 14 Urban and 6 Rural candidates. The region factors
are therefore $10/14=0.714$ and $10/6=1.667$. Because each row has one shared
weight, the combined effects are approximately:

| Candidate profile | Age factor | Region factor | Combined weight |
|---|---:|---:|---:|
| Young + Urban | 0.75 | 0.714 | 0.536 |
| Young + Rural | 0.75 | 1.667 | 1.250 |
| Old + Urban | 2.00 | 0.714 | 1.428 |
| Old + Rural | 2.00 | 1.667 | 3.334 |

The region update can move the age margin away from 60/40. The algorithm
therefore cycles through age, region, gender identity, and urbanicity repeatedly:

```text
age -> region -> gender identity -> urbanicity -> age -> ...
```

Later updates can partially undo earlier ones, but the next sweep observes and
corrects that error. This is why the method is iterative rather than a single
pass. The implementation uses bounded positive weights, at most 200 sweeps, and
a small expected-margin convergence tolerance. Correlated or incompatible
margins may prevent an exact solution; in that case the result is a bounded
compromise and the achieved errors are reported.

The `quality` and `weight` entries in `calibration_targets.json` document target
provenance and confidence. The current optimizer applies every supplied margin
sequentially; those metadata weights do not alter the multiplicative update.

### Turning calibrated weights into an exact-size sample

After expected margins converge, deterministic exponential-race sampling assigns
candidate $i$ the priority

$$
q_i=\frac{-\log U_i}{w_i},
$$

where $U_i$ is generated deterministically from the seed and stable row ID. The
build selects the $n$ smallest priorities. This gives exactly $n$ unique rows,
favors candidates with larger calibrated weights, is independent of input order,
and is reproducible for the same seed. It is not a sequential greedy procedure.

Expected margins can differ slightly from the realized fixed-size sample. The
final audit therefore measures the actual selected rows rather than assuming the
expectations were achieved.

### Human-to-synthetic residual example

Synthetic calibration is not asked to match the global target independently.
It compensates for the human-grounded component. Suppose one field has two
categories with a 60%/40% target. Assume that field is known for 500,000 of the
600,000 selected human-grounded rows and for all 400,000 synthetic rows. The
final known-value denominator is therefore 900,000, giving desired counts:

$$
T_A=900{,}000\times0.60=540{,}000,
\qquad
T_B=900{,}000\times0.40=360{,}000.
$$

If the human-grounded selection already contains 350,000 known $A$ values and
150,000 known $B$ values, the synthetic residual is

$$
r_A=540{,}000-350{,}000=190{,}000,
\qquad
r_B=360{,}000-150{,}000=210{,}000.
$$

The synthetic target is thus 47.5% $A$ and 52.5% $B$, even though the global
target is 60%/40%. Combining human-grounded and synthetic rows then moves the
full coreset toward the global target.

If the human-grounded component already exceeds a category's final target, its
raw residual is negative and synthetic rows cannot subtract observations. The
implementation clips that residual to zero, renormalizes the remaining positive
residuals, and records the clipped mass as infeasibility in `audit.json`.

### Missing values and acceptance evidence

Missing calibration values receive no update for that dimension and are never
imputed. Consequently, a statement such as "age matches the target" means the
age distribution among selected rows with known age. `audit.json` and
`RESULTS.md` report, for every calibrated dimension:

- target and achieved share for each category;
- absolute error and maximum absolute error;
- number of known and missing selected rows;
- negative residual mass when the human-grounded component makes a target
   category infeasible; and
- exact synthetic candidate file and row-group provenance.

These outputs distinguish best-effort marginal calibration from a claim of a
fully representative joint population sample.

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