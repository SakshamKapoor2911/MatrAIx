#!/usr/bin/env bash
#
# Owner-side one-liner: turn a slice into a ready-to-send collaborator package.
#
#   ./make_package.sh 0:100
#
# Input is just the slice (START:END, half-open). Everything else has a default
# below. The profile DB lives ONLY on your machine; it is built once and reused.
# Collaborators receive a lightweight .tar.gz (tasks.jsonl + dimensions.json +
# collab_kit/) -- no DB, no build step on their side.
#
# Optional 2nd/3rd args:
#   ./make_package.sh 0:100 alice                       # set worker id
#   ./make_package.sh 0:100 alice demographic_core      # only some dimensions
#
set -euo pipefail

# ---- config ---------------------------------------------------------------
# WIKI_CLEAN_DIR must point at a JSONL/JSONL.GZ clean person-profile layer with
# page_id, qid, title, source_url, and profile_text/plain_text/text.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${MATRIX_REPO_ROOT:-$(cd "${SCRIPT_DIR}/../../.." && pwd)}"
: "${WIKI_CLEAN_DIR:?Set WIKI_CLEAN_DIR to a clean Wikipedia person-profile JSONL directory or file.}"
DATASET_ID="${WIKI_DATASET_ID:-matraix_wiki_profiles_20260601_v1}"
CACHE_ROOT="${MATRIX_PACKAGE_CACHE_ROOT:-${TMPDIR:-/tmp}}"
DB="${WIKI_PROFILE_DB:-${CACHE_ROOT}/${DATASET_ID}.sqlite}"
MANIFEST="${WIKI_PROFILE_MANIFEST:-${CACHE_ROOT}/${DATASET_ID}.manifest.json}"
DIMENSIONS="${MATRIX_DIMENSIONS:-${REPO_ROOT}/persona/dimensions.json}"
OUT_ROOT="${MATRIX_PACKAGE_OUT_ROOT:-${CACHE_ROOT}/matraix_packages}"
# ----------------------------------------------------------------------------

RANGE="${1:-}"
WORKER_ID="${2:-worker}"
CATEGORIES="${3:-}"

if [[ -z "${RANGE}" || ! "${RANGE}" =~ ^[0-9]+:[0-9]+$ ]]; then
  echo "usage: $0 START:END [worker_id] [categories]" >&2
  echo "  e.g. $0 0:100" >&2
  exit 2
fi
START="${RANGE%%:*}"
END="${RANGE##*:}"

cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}"

# 1) Build the profile DB once (owner only). Reused on later runs.
if [[ ! -f "${DB}" || ! -f "${MANIFEST}" ]]; then
  echo ">> building profile DB (one-time): ${DB}"
  python3 persona/existing_data_curation/scripts/build_wiki_profile_db.py \
    --clean-dir "${WIKI_CLEAN_DIR}" \
    --out-db   "${DB}" \
    --manifest "${MANIFEST}" \
    --dataset-id "${DATASET_ID}"
fi

DATASET_SHA256="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['db_sha256'])" "${MANIFEST}")"

# 2) Slice + package (make_collab_package writes the .tar.gz for us).
ASSIGNMENT_ID="A_${START}_${END}"
OUT_DIR="${OUT_ROOT}/${ASSIGNMENT_ID}_${WORKER_ID}"

CAT_ARGS=()
[[ -n "${CATEGORIES}" ]] && CAT_ARGS=(--categories "${CATEGORIES}")

echo ">> packaging slice ${RANGE} for '${WORKER_ID}'"
python3 persona/existing_data_curation/scripts/make_collab_package.py \
  --db "${DB}" \
  --dimensions "${DIMENSIONS}" \
  --range "${RANGE}" \
  --out-dir "${OUT_DIR}" \
  --assignment-id "${ASSIGNMENT_ID}" \
  --worker-id "${WORKER_ID}" \
  --dataset-id "${DATASET_ID}" \
  --dataset-sha256 "${DATASET_SHA256}" \
  --force \
  "${CAT_ARGS[@]}" >/dev/null

ARCHIVE="${OUT_DIR}.tar.gz"
echo ""
echo "done. send this file to your collaborator:"
echo "   ${ARCHIVE}"
