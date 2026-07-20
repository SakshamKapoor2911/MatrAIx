# Persona Quality Filter

This package scans all six persona products against conservative categorical
contradiction rules in `contradictions.json`.

Filtering is non-destructive. Every source shard produces:

- `*.reject.bits`: one little-endian packed bit per source row, where `1` means
  reject and `0` means keep;
- `*.report.json`: source and rule provenance, row totals, rejection totals,
  per-rule counts, and relevant off-schema values.

Synthetic shards are checked directly from nibble-packed codes. Human-product
JSONL records are checked from populated `fields`; missing and unsupported
fields do not trigger a contradiction.

Run all canonical products through Slurm:

```bash
cd persona/post_process/quality_filter/jobs
./submit_all.sh
```

The canonical inventory contains 100 synthetic, 200 Wiki, 256 Amazon, three
Stack Overflow, one PRISM, and five GSS tasks. Amazon selection matches the
validated final assembly policy: 167 continuation buckets plus 89 source
buckets. Stack Overflow uses only the PR #53-compatible files.

After both arrays succeed, a dependent job validates all 565 shard reports and
writes `summary.json` with dataset-level and global rejection counts.

Outputs and generated manifests are intentionally ignored by git.