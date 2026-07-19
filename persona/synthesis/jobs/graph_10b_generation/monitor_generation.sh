#!/bin/bash
# Monitor a Full DAG generation run.
# Usage:
#   ./monitor_generation.sh <RUN_TAG> [SLURM_JOB_ID]
#   OUTPUT_ROOT=/path/to/run ./monitor_generation.sh custom [SLURM_JOB_ID]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
RUN_TAG="${1:-}"
JOB_ID="${2:-${JOB_ID:-}}"
TAIL_LINES="${TAIL_LINES:-60}"
BYTES_PER_ROW_ESTIMATE="${BYTES_PER_ROW_ESTIMATE:-403.98}"

if [[ -z "$RUN_TAG" && -z "${OUTPUT_ROOT:-}" ]]; then
  echo "Usage: $0 <RUN_TAG> [SLURM_JOB_ID]" >&2
  exit 2
fi

OUTPUT_ROOT="${OUTPUT_ROOT:-$REPO_ROOT/persona/synthesis/generated/$RUN_TAG}"
SHARD_DIR="$OUTPUT_ROOT/shards"
MANIFEST_DIR="$OUTPUT_ROOT/manifests"

printf '=== Full DAG generation monitor ===\n'
printf 'time=%s\n' "$(date -Is)"
printf 'output_root=%s\n' "$OUTPUT_ROOT"
printf 'job_id=%s\n' "${JOB_ID:-none}"
printf '\n'

if [[ -n "$JOB_ID" ]]; then
  echo '--- squeue ---'
  squeue -j "$JOB_ID" -o '%.18i %.9P %.30j %.8u %.2t %.10M %.6D %.8C %R' || true
  echo
  echo '--- sacct ---'
  sacct -j "$JOB_ID" --format=JobID,JobName%30,Partition,AllocCPUS,State,ExitCode,Elapsed,NodeList 2>/dev/null | sed -n '1,40p' || true
  echo
fi

echo '--- output size ---'
if [[ -d "$OUTPUT_ROOT" ]]; then
  du -sh "$OUTPUT_ROOT" 2>/dev/null || true
else
  echo 'output root does not exist yet'
fi
printf '\n'

echo '--- shard files ---'
if [[ -d "$SHARD_DIR" ]]; then
  find "$SHARD_DIR" -maxdepth 1 -type f -name '*.codes.gz' -printf '%f %s\n' | sort | sed -n '1,20p'
  shard_count=$(find "$SHARD_DIR" -maxdepth 1 -type f -name '*.codes.gz' | wc -l)
  schema_count=$(find "$SHARD_DIR" -maxdepth 1 -type f -name '*.schema.json' | wc -l)
  echo "shard_count=$shard_count schema_count=$schema_count"
else
  echo 'no shard directory yet'
fi
printf '\n'

echo '--- manifest summary ---'
if [[ -d "$MANIFEST_DIR" ]]; then
  python - <<PY
import json
from pathlib import Path
base = Path("$MANIFEST_DIR")
paths = sorted(base.glob("*.manifest.json"))
print(f"manifest_count={len(paths)}")
rows = 0
seconds = 0
bytes_total = 0
for path in paths:
    m = json.loads(path.read_text())
    rows += int(m.get("rows", 0))
    seconds += int(m.get("elapsed_seconds", 0))
    bytes_total += int(m.get("codes_bytes", 0))
print(f"completed_rows={rows}")
if rows:
    print(f"completed_codes_bytes={bytes_total}")
    print(f"avg_bytes_per_row={bytes_total / rows:.3f}")
if seconds:
    print(f"sum_sampler_seconds={seconds}")
    print(f"aggregate_rows_per_sampler_second={rows / seconds:.1f}")
print("recent_manifests:")
for path in paths[-10:]:
    m = json.loads(path.read_text())
    elapsed = int(m.get("elapsed_seconds", 0))
    shard_rows = int(m.get("rows", 0))
    rps = shard_rows / elapsed if elapsed else 0
    print(f"  {path.name}: rows={shard_rows} elapsed={elapsed}s rps={rps:.1f} bytes={m.get('codes_bytes')} node={m.get('hostname')}")
PY
else
  echo 'no manifest directory yet'
fi
printf '\n'

echo '--- estimated in-progress rows from shard file sizes ---'
if [[ -d "$SHARD_DIR" ]]; then
  python - <<PY
from pathlib import Path
import os
bytes_per_row = float("$BYTES_PER_ROW_ESTIMATE")
base = Path("$SHARD_DIR")
for path in sorted(base.glob("*.codes.gz"))[-20:]:
    size = path.stat().st_size
    est_rows = int(size / bytes_per_row)
    print(f"{path.name}: {size} bytes ~= {est_rows:,} rows at {bytes_per_row:.2f} B/row")

temp_dirs = sorted(base.glob("*.codes.gz.shards.*"))
if temp_dirs:
  print("temporary shard directories:")
for path in temp_dirs[-20:]:
  total = 0
  for root, _, files in os.walk(path):
    for name in files:
      try:
        total += (Path(root) / name).stat().st_size
      except FileNotFoundError:
        pass
  est_rows = int(total / bytes_per_row)
  print(f"{path.name}: {total} bytes ~= {est_rows:,} rows at {bytes_per_row:.2f} B/row")
PY
fi
printf '\n'

echo '--- log tails ---'
cd "$SCRIPT_DIR"
if [[ -n "$JOB_ID" ]]; then
  files=(sbatch_logs/*"$JOB_ID"*.out sbatch_logs/*"$JOB_ID"*.err)
else
  files=( $(ls -t sbatch_logs/*.out sbatch_logs/*.err 2>/dev/null | head -6) )
fi
for file in "${files[@]}"; do
  [[ -e "$file" ]] || continue
  echo "### $file"
  tail -n "$TAIL_LINES" "$file" || true
  echo
 done
