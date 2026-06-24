# Amazon Reviews 2023 CV Collaboration Package Design

## Goal

Support outbound collaboration packages for Amazon Reviews 2023 while using
multiple reviews from the same reviewer as internal validation evidence. The
package should let a worker run the same `collab_kit` workflow as the existing
wiki package and return the same `results.jsonl` contract.

This design only covers what we send to workers and the default starter-code
method they receive. Owner-side result ingestion and downstream aggregation are
out of scope.

## Scope

- Input source: `user_histories.jsonl` rows produced by
  `retrieve_amazon_user_histories.py`.
- Task unit: one Amazon reviewer per `tasks.jsonl` row.
- Cross-validation unit: folds of reviews within the same reviewer.
- Return contract: unchanged `results.jsonl` with one record per reviewer task.
- Existing wiki packages must keep working without behavior changes.

## Package Shape

Add an Amazon-specific package builder:

```bash
python personas/existing_data_curation/scripts/make_amazon_collab_package.py \
  --user-histories raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl \
  --range 0:100 \
  --out-dir outbound/amazon_review_2023/alice_0000000000_0000000100 \
  --assignment-id amazon23-alice-0001 \
  --worker-id alice \
  --dataset-id amazon_reviews_2023_user_histories_v1 \
  --dataset-sha256 <sha256> \
  --force
```

The output directory mirrors the wiki package:

- `assignment.json`
- `tasks.jsonl`
- `dimensions.json`
- `README.md`
- `collab_kit/`
- sibling `.tar.gz` archive unless disabled

The raw Amazon source files stay local. Workers receive only the selected and
rendered task rows.

## Task Row Contract

Each task row should include the fields already expected by `collab_kit`:

- `global_idx`
- `task_id`
- `qid`
- `title`
- `source_url`
- `profile_text`
- `input_sha256`

Amazon rows also include metadata useful for debugging and later validation:

- `source: "amazon_reviews_2023"`
- `user_id`
- `review_count`
- `categories`
- `cv_folds`
- `min_support_folds`

`task_id` should be stable, for example
`amazon_reviews_2023:<user_id>`. `qid` can be a stable pseudo-id such as
`amazon_user:<user_id>`.

## Review Rendering

The builder converts selected reviews into plain text evidence. It should use
stable review ids (`r0001`, `r0002`, ...), include fold labels, and keep enough
fields for direct evidence citation:

- review id
- fold id
- date
- category
- rating
- title
- text
- verified purchase flag
- helpful vote count

The default limits should be conservative enough for model context windows:

- `--cv-folds 3`
- `--min-support-folds 2`
- `--max-reviews-per-user 90`
- `--max-review-text-chars 900`
- `--max-profile-text-chars 70000`

Reviews should be ordered by timestamp before fold assignment. Fold assignment
should be deterministic and balanced across time, so each fold gets a spread of
early and late reviews rather than a single contiguous time block.

## Dimensions Sent

By default, the Amazon package sends only dimensions whose schema categories are
supported by `amazon_review_evidence_mapping.json`, excluding categories marked
as skip-by-default. This avoids asking workers to infer demographics, health,
identity, narrative history, or other weakly supported attributes from shopping
behavior.

The builder should provide an override such as `--all-dimensions` for full
1,339-dimension packages when needed.

## Starter Code Behavior

`collab_kit/solver.py` keeps the wiki behavior for normal wiki tasks. For
Amazon tasks, the default method should:

1. Detect `source == "amazon_reviews_2023"` or fold markers in the task row.
2. Split the rendered evidence by fold.
3. Run attribution independently on each fold.
4. Merge fold outputs by exact `(field_id, value)`.
5. Keep a non-null dimension only when it appears in at least
   `min_support_folds` folds.
6. Combine evidence quotes from supporting folds.
7. Use conservative confidence based on fold support and returned model
   confidence.
8. Return unsupported fields for dimensions without sufficient support.

The default merge should prefer precision over recall. A dimension supported by
only one fold should not become a non-null returned value unless the worker
chooses to modify the starter method.

## Error Handling

- Empty or malformed `user_histories.jsonl` should fail with a clear error.
- A requested range must contain exactly `range_end - range_start` users.
- Users with no usable reviews should fail package creation by default, because
  the cross-validation contract cannot be satisfied.
- If `cv_folds` is greater than the usable review count, the builder should set
  `effective_cv_folds = usable_review_count`. It should fail clearly when
  `effective_cv_folds < 2`, because one fold cannot support internal
  cross-validation.
- Archive generation should avoid duplicate tar members and should include the
  bundled sample files in `collab_kit`.

## Testing

Add focused tests for the outbound package:

- Building an Amazon package from a tiny synthetic `user_histories.jsonl`.
- Verifying one task row per user and stable Amazon metadata.
- Verifying rendered `profile_text` contains fold labels and stable review ids.
- Verifying default dimensions are filtered by Amazon-supported schema
  categories.
- Verifying `--all-dimensions` includes every supplied dimension.
- Verifying the archive has unique members and includes `collab_kit` sample
  outputs.
- Running the packaged `collab_kit` mock backend and conformance checker on the
  synthetic package.

## Non-Goals

- No owner-side merge or database writeback in this step.
- No cross-user validation in this step.
- No changes to the Amazon retrieval script.
- No requirement that workers use the default solver unchanged.

## Open Defaults

The initial implementation should use:

- `cv_folds = 3`
- `min_support_folds = 2`
- Amazon-supported dimensions only
- one reviewer per task row
- same `results.jsonl` return contract as wiki packages
