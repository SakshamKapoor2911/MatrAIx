#!/usr/bin/env bash
# Monitor the Amazon persona extraction (A100, one array task = one user_bucket).
# Usage: bash monitor_amazon.sh
set -uo pipefail
USER_ID="${USER:-xiaominli}"
OUT="/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx/persona/human_extraction/data/amazon/extraction_v1"
LOGS="/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx/persona/human_extraction/jobs/sbatch_logs"
TARGET=100000

echo "=== queue (extract_shard_amazon.job) ==="
squeue -u "$USER_ID" -r -n extract_shard_amazon.job -o "%.14i %.9P %.8T %.11M %R" 2>/dev/null | head -40
echo "state counts:"
squeue -u "$USER_ID" -r -h -n extract_shard_amazon.job -o "%T" 2>/dev/null | sort | uniq -c

echo
echo "=== recent sacct (last 1 day) ==="
sacct --starttime now-1days -n --name extract_shard_amazon.job \
  --format=JobID%18,State,ExitCode,Elapsed -P 2>/dev/null \
  | grep -vE "\.batch|\.extern" | awk -F'|' '{print $2}' | sort | uniq -c

echo
echo "=== output progress ==="
if compgen -G "$OUT/shard_*.jsonl" >/dev/null; then
  n=$(cat "$OUT"/shard_*.jsonl 2>/dev/null | wc -l)
  s=$(ls "$OUT"/shard_*.jsonl 2>/dev/null | wc -l)
  pct=$(awk "BEGIN{printf \"%.2f\", 100*$n/$TARGET}")
  echo "$n / $TARGET users ($pct%) across $s / 256 shard files"
else
  echo "no shard output yet"
fi

echo
echo "=== error scan (real failures) ==="
grep -aliE "Traceback|CUDA error|out of memory|OutOfMemory|ValueError" \
  "$LOGS"/extract_shard_amazon.job_*.err 2>/dev/null | tail -10 || echo "none"

echo
echo "tip: tail a live shard log ->  tail -f $LOGS/extract_shard_amazon.job_<JOBID>_<ARRAYID>.out"
