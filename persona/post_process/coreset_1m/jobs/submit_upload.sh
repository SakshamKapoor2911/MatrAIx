#!/bin/bash
set -euo pipefail
R="${REPO_ROOT:-/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx}"
P="${PYTHON_BIN:-/n/home08/xiaominli/.conda/envs/env05/bin/python}"
HF="${HF_BIN:-/n/home08/xiaominli/.conda/envs/env05/bin/hf}"
D="$R/persona/post_process/coreset_1m"
SUBMISSION="$D/results/submission.json"
[[ -n "${HF_TOKEN_matraix:-${HF_TOKEN:-}}" ]] || { echo "Export HF_TOKEN_matraix or HF_TOKEN first" >&2; exit 2; }
build=$("$P" -c 'import json,sys; print(json.load(open(sys.argv[1]))["build_job"])' "$SUBMISSION")
output=$("$P" -c 'import json,sys; print(json.load(open(sys.argv[1]))["output"])' "$SUBMISSION")
repo=$("$P" -c 'import json,sys; print(json.load(open(sys.argv[1]))["repo"])' "$SUBMISSION")
common="ALL,REPO_ROOT=$R,PYTHON_BIN=$P,HF_BIN=$HF,OUTPUT=$output,REPO_ID=$repo"
cd "$D/jobs"
upload=$(sbatch --parsable --job-name=persona1m_upload \
  --dependency="afterok:$build" --export="$common" "$D/jobs/upload.job")
"$P" - "$SUBMISSION" "$upload" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text())
payload["upload_job"] = sys.argv[2]
payload["authentication_required"] = False
path.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
print(json.dumps(payload, indent=2))
PY