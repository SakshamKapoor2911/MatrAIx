# Hugging Face Upload Record: Persona8B 1B Subset

Date: 2026-07-04

This file records the upload of the first 1B rows from the completed Full DAG 10B run to the Hugging Face dataset repository.

## Target Repository

```text
repo: MatrAIx2026/Persona8B
url: https://huggingface.co/datasets/MatrAIx2026/Persona8B
repo_type: dataset
private flag observed via API: false
```

The repository was observed as non-private via the Hugging Face API. Access may still be gated on the Hugging Face side, but this is not the same as a private repository.

## Source Data

```text
source local run: persona/synthesis/generated/full_dag_10b_20260703/
source run record: persona/synthesis/jobs/graph_10b_generation/RUN_FULL_DAG_10B_20260703.md
subset: shard ids 0000-0009
total subset rows: 1,000,000,000
rows per shard: 100,000,000
attributes per row: 1,290
format: codes.gz
packing: nibble
compression: gzip
rendered text stored: no
```

Local staging folder:

```text
persona/synthesis/generated/hf_persona8b_1b_20260704/
```

The staging folder was created with hardlinks to the local 10B generated shards, so it did not duplicate the 404GB payload locally.

## Staged Files

```text
README.md
SUBSET_1B_MANIFEST.json
SHA256SUMS.txt
RUN_FULL_DAG_10B_20260703.md
manifests/
  10 x .manifest.json
shards/
  10 x .codes.gz
  10 x .codes.gz.schema.json
```

Local staged size:

```text
codes shards: 10
schema sidecars: 10
manifests: 10
codes bytes: 403,970,976,287
codes decimal TB: 0.403971 TB
du -sh staging folder: 377G
```

## Upload Commands

Metadata was uploaded first:

```bash
hf upload-large-folder MatrAIx2026/Persona8B . \
  --repo-type dataset \
  --include README.md SUBSET_1B_MANIFEST.json SHA256SUMS.txt RUN_FULL_DAG_10B_20260703.md 'manifests/*.manifest.json' \
  --num-workers 4
```

Shard files and schema sidecars were uploaded next:

```bash
hf upload-large-folder MatrAIx2026/Persona8B . \
  --repo-type dataset \
  --include 'shards/*.codes.gz' 'shards/*.schema.json' \
  --num-workers 8
```

The large upload was interrupted/killed during terminal execution, but `hf upload-large-folder` successfully committed the shard files before termination. The final remote verification below confirmed the upload completed.

## Remote Verification

Final Hugging Face repository check:

```text
remote file count: 35
remote codes files: 10
remote schema files: 10
remote manifest files: 10
root metadata files present:
  README.md
  SUBSET_1B_MANIFEST.json
  SHA256SUMS.txt
  RUN_FULL_DAG_10B_20260703.md
```

Remote size check:

```text
remote shards/ files: 20
remote shards/ bytes: 403,974,233,857
remote manifests/ files: 10
remote manifests/ bytes: 8,970
local-vs-remote size mismatches: 0
```

The `shards/` byte total includes both the large `.codes.gz` files and small `.schema.json` sidecars. Local-vs-remote size verification matched all staged shard, schema, manifest, and metadata files.

## Notes

- The uploaded 1B subset is already compressed; it is not Parquet and not rendered text.
- The full local 10B run remains under `persona/synthesis/generated/full_dag_10b_20260703/` and is not uploaded in full because it is ~4.04TB compressed.
- For Hugging Face usability, a smaller Parquet preview can be added later, but the large primary artifact is the compact `codes.gz` representation.
- Do not print or commit Hugging Face tokens. The upload used `HF_TOKEN_matraix` from the user's shell configuration.
