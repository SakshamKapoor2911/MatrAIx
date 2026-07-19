#!/usr/bin/env bash
#
# Owner-side one-liner: turn an Amazon Reviews 2023 user-history slice into a
# ready-to-send collaborator package.
#
#   ./make_amazon_package.sh /path/to/user_histories.jsonl.gz 0:100 alice
#
# Collaborators receive a lightweight .tar.gz (tasks.jsonl + dimensions.json +
# collab_kit/) -- no raw source JSONL and no owner-side database.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${MATRIX_REPO_ROOT:-$(cd "${SCRIPT_DIR}/../../.." && pwd)}"
DATASET_ID="${AMAZON_DATASET_ID:-matraix_amazon_reviews_2023_v1}"
DIMENSIONS="${MATRIX_DIMENSIONS:-${REPO_ROOT}/persona/dimensions.json}"
CACHE_ROOT="${MATRIX_PACKAGE_CACHE_ROOT:-${TMPDIR:-/tmp}}"
OUT_ROOT="${MATRIX_PACKAGE_OUT_ROOT:-${CACHE_ROOT}/matraix_packages}"

USER_HISTORIES="${1:-}"
RANGE="${2:-}"
WORKER_ID="${3:-worker}"
DIMENSION_SCOPE="${4:-supported}"

if [[ -z "${USER_HISTORIES}" || ! -f "${USER_HISTORIES}" ]]; then
  echo "usage: $0 USER_HISTORIES_JSONL START:END [worker_id] [supported|all]" >&2
  exit 2
fi
if [[ -z "${RANGE}" || ! "${RANGE}" =~ ^[0-9]+:[0-9]+$ ]]; then
  echo "usage: $0 USER_HISTORIES_JSONL START:END [worker_id] [supported|all]" >&2
  echo "  e.g. $0 /data/amazon/user_histories.jsonl.gz 0:100 alice" >&2
  exit 2
fi
if [[ "${DIMENSION_SCOPE}" != "supported" && "${DIMENSION_SCOPE}" != "all" ]]; then
  echo "dimension scope must be 'supported' or 'all'" >&2
  exit 2
fi

START="${RANGE%%:*}"
END="${RANGE##*:}"
ASSIGNMENT_ID="AMZ_${START}_${END}"
OUT_DIR="${OUT_ROOT}/${ASSIGNMENT_ID}_${WORKER_ID}"

cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}"

DATASET_SHA256="$(python3 -c 'import hashlib,sys; d=hashlib.sha256(); f=open(sys.argv[1], "rb"); [d.update(c) for c in iter(lambda: f.read(1024*1024), b"")]; print(d.hexdigest())' "${USER_HISTORIES}")"

SCOPE_ARGS=()
[[ "${DIMENSION_SCOPE}" == "all" ]] && SCOPE_ARGS=(--all-dimensions)

echo ">> packaging Amazon slice ${RANGE} for '${WORKER_ID}'"
python3 persona/existing_data_curation/scripts/make_amazon_collab_package.py \
  --user-histories "${USER_HISTORIES}" \
  --dimensions "${DIMENSIONS}" \
  --range "${RANGE}" \
  --out-dir "${OUT_DIR}" \
  --assignment-id "${ASSIGNMENT_ID}" \
  --worker-id "${WORKER_ID}" \
  --dataset-id "${DATASET_ID}" \
  --dataset-sha256 "${DATASET_SHA256}" \
  --force \
  "${SCOPE_ARGS[@]}" >/dev/null

ARCHIVE="${OUT_DIR}.tar.gz"
echo ""
echo "done. send this file to your collaborator:"
echo "   ${ARCHIVE}"
