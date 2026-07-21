# Persona Dataset Statistics

This package profiles the six major persona products once and stores compact
aggregates for fast paper analysis and plotting.

```text
dataset_statistics/
  profile_datasets.py          Streaming profiler; reads the large artifacts.
  dataset_statistics.ipynb     Fast cache-only tables and plotting notebook.
  results/
    dataset_statistics.json    Cached aggregate and distribution data.
    dataset_summary.csv        One paper-ready row per product.
    category_summary.csv       Product-by-category coverage statistics.
    dimension_summary.csv      Product-by-dimension prevalence statistics.
    images/                    PNG and PDF figures created by the notebook.
```

## Coverage policy

- **Synthetic:** no 3.7 TB scan. Counts come from the completed 10B manifests;
  all 1,290 dimensions are assigned by construction.
- **Wiki:** deterministic 5,000-row stratified sample: three upgraded rows from
  shard 0 (matching their share of the corpus) plus 263 Qwen rows from each of
  19 evenly spaced shards (`0010` through `0190`). The exact extracted row count
  remains 1,997,743. Sample-derived metrics are labeled estimates.
- **Amazon:** full 100K scan assembled from the 167 completed continuation
  buckets and 89 completed source buckets.
- **Stack Overflow:** full scan of the three PR #53-compatible translated files;
  raw files are not counted again.
- **PRISM and GSS:** full scans of all gzip JSONL shards.

## Metrics

The cache records dataset scale and method, emitted and populated attributes per
persona, category and dimension prevalence, assignment-type mix, evidence and
description coverage among populated fields, confidence distributions,
observed-layer counts, and basic contract anomalies. `null` and empty values do
not count as populated attributes.

Run the expensive stage only when source data changes:

```bash
/n/home08/xiaominli/.conda/envs/env05/bin/python \
  persona/post_process/dataset_statistics/profile_datasets.py
```

To refresh selected products while retaining the other cached results:

```bash
python persona/post_process/dataset_statistics/profile_datasets.py \
  --products wiki --merge-existing
```

Then rerun the notebook as often as needed. It reads only cached JSON/CSV files
and normally finishes in seconds.
