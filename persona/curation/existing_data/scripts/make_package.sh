#!/usr/bin/env bash
#
# Owner-side one-liner: turn a slice into a ready-to-send collaborator package.
#
#   ./make_package.sh 0:100
#
# Input is the slice (START:END, half-open). Defaults are for wiki packages.
# To package Amazon histories, set SOURCE=amazon and USER_HISTORIES locally:
#
#   SOURCE=amazon USER_HISTORIES=/path/to/user_histories.jsonl ./make_package.sh 0:10 bob
#
# Owner-side source data lives ONLY on your machine; collaborators receive a
# lightweight .tar.gz (tasks.jsonl + dimensions.json + collab_kit/) — no DB, no
# build step on their side.
#
# Optional 2nd/3rd args:
#   ./make_package.sh 0:100 alice                       # set worker id
#   ./make_package.sh 0:100 alice demographic_core      # only some dimensions
#   SOURCE=amazon USER_HISTORIES=/path/to/user_histories.jsonl ./make_package.sh 0:10 alice
#
set -euo pipefail

# ---- config (edit these once) ----------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
SOURCE="${SOURCE:-wiki}"
CLEAN_DIR="${CLEAN_DIR:-/data2/zonglin/wiki_dumps/enwiki/20260601/person_text_derivatives/person_pages_clean}"
case "${SOURCE}" in
  wiki)
    DEFAULT_DATASET_ID="personabench_wiki_profiles_20260601_v1"
    ;;
  amazon|amazon_reviews_2023)
    SOURCE="amazon"
    DEFAULT_DATASET_ID="amazon_reviews_2023_local"
    ;;
  *)
    echo "unknown SOURCE='${SOURCE}'; expected wiki or amazon" >&2
    exit 2
    ;;
esac
DATASET_ID="${DATASET_ID:-${DEFAULT_DATASET_ID}}"
DB="${DB:-/tmp/${DATASET_ID}.sqlite}"
MANIFEST="${MANIFEST:-/tmp/${DATASET_ID}.manifest.json}"
DIMENSIONS="${DIMENSIONS:-${REPO_ROOT}/persona/schema/dimensions.json}"
OUT_ROOT="${OUT_ROOT:-/tmp/personabench_packages}"
USER_HISTORIES="${USER_HISTORIES:-}"
DATASET_SHA256="${DATASET_SHA256:-}"
EVIDENCE_MAPPING="${EVIDENCE_MAPPING:-${REPO_ROOT}/persona/curation/existing_data/amazon_review_evidence_mapping.json}"
CV_FOLDS="${CV_FOLDS:-3}"
MIN_SUPPORT_FOLDS="${MIN_SUPPORT_FOLDS:-2}"
MAX_REVIEWS_PER_USER="${MAX_REVIEWS_PER_USER:-90}"
MAX_REVIEW_TEXT_CHARS="${MAX_REVIEW_TEXT_CHARS:-900}"
MAX_PROFILE_TEXT_CHARS="${MAX_PROFILE_TEXT_CHARS:-70000}"
ALL_DIMENSIONS="${ALL_DIMENSIONS:-0}"
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

sha256_path() {
  python3 - "$1" <<'PY'
import hashlib
import sys

h = hashlib.sha256()
with open(sys.argv[1], "rb") as fh:
    for chunk in iter(lambda: fh.read(1024 * 1024), b""):
        h.update(chunk)
print(h.hexdigest())
PY
}

ASSIGNMENT_ID="${ASSIGNMENT_ID:-}"
if [[ -z "${ASSIGNMENT_ID}" && "${SOURCE}" == "amazon" ]]; then
  ASSIGNMENT_ID="AMZ_${START}_${END}"
elif [[ -z "${ASSIGNMENT_ID}" ]]; then
  ASSIGNMENT_ID="A_${START}_${END}"
fi
OUT_DIR="${OUT_ROOT}/${ASSIGNMENT_ID}_${WORKER_ID}"

PACKAGE_ARGS=(
  --source "${SOURCE}"
  --dimensions "${DIMENSIONS}"
  --range "${RANGE}"
  --out-dir "${OUT_DIR}"
  --assignment-id "${ASSIGNMENT_ID}"
  --worker-id "${WORKER_ID}"
  --dataset-id "${DATASET_ID}"
  --force
)

if [[ "${SOURCE}" == "wiki" ]]; then
  # Build the profile DB once (owner only). Reused on later runs.
  if [[ ! -f "${DB}" || ! -f "${MANIFEST}" ]]; then
    echo ">> building profile DB (one-time): ${DB}"
    python3 persona/curation/existing_data/scripts/build_wiki_profile_db.py \
      --clean-dir "${CLEAN_DIR}" \
      --out-db   "${DB}" \
      --manifest "${MANIFEST}" \
      --dataset-id "${DATASET_ID}"
  fi
  if [[ -z "${DATASET_SHA256}" ]]; then
    DATASET_SHA256="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['db_sha256'])" "${MANIFEST}")"
  fi
  PACKAGE_ARGS+=(--db "${DB}")
  [[ -n "${CATEGORIES}" ]] && PACKAGE_ARGS+=(--categories "${CATEGORIES}")
else
  if [[ -z "${USER_HISTORIES}" ]]; then
    echo "SOURCE=amazon requires USER_HISTORIES=/path/to/user_histories.jsonl" >&2
    exit 2
  fi
  if [[ -n "${CATEGORIES}" ]]; then
    echo "categories is wiki-only; use ALL_DIMENSIONS=1 or EVIDENCE_MAPPING for Amazon" >&2
    exit 2
  fi
  if [[ -z "${DATASET_SHA256}" ]]; then
    DATASET_SHA256="$(sha256_path "${USER_HISTORIES}")"
  fi
  PACKAGE_ARGS+=(
    --user-histories "${USER_HISTORIES}"
    --evidence-mapping "${EVIDENCE_MAPPING}"
    --cv-folds "${CV_FOLDS}"
    --min-support-folds "${MIN_SUPPORT_FOLDS}"
    --max-reviews-per-user "${MAX_REVIEWS_PER_USER}"
    --max-review-text-chars "${MAX_REVIEW_TEXT_CHARS}"
    --max-profile-text-chars "${MAX_PROFILE_TEXT_CHARS}"
  )
  [[ "${ALL_DIMENSIONS}" == "1" ]] && PACKAGE_ARGS+=(--all-dimensions)
fi

PACKAGE_ARGS+=(--dataset-sha256 "${DATASET_SHA256}")

echo ">> packaging slice ${RANGE} for '${WORKER_ID}'"
python3 persona/curation/existing_data/scripts/make_package.py "${PACKAGE_ARGS[@]}" >/dev/null

ARCHIVE="${OUT_DIR}.tar.gz"
echo ""
echo "✅ done. send this file to your collaborator:"
echo "   ${ARCHIVE}"
