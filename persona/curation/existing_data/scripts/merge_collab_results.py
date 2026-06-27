#!/usr/bin/env python3
"""Validate and merge Flow-1 collaborator results.jsonl files into one dataset.

Each collaborator returns a plain `results.jsonl` (from collab_kit): one record
per profile, `{global_idx, task_id, qid, model, fields:[...]}`. This script is
the owner-side ingest for that flow:

  1. format check    — same contract checker collaborators run (conformance.py)
  2. identity check  — (optional, --db) every global_idx exists in the source
                       SQLite and its task_id/qid match, so a returned profile
                       can't be silently swapped or mislabeled
  3. allowed-value   — (optional, --dimensions) values stay inside the catalog;
                       field_ids outside the catalog are flagged as drift
  4. merge           — union fields per global_idx across all files; profiles
                       are usually disjoint across collaborators, but if two
                       files cover the same profile (e.g. split by category)
                       their fields are unioned and any field_id that disagrees
                       on value is reported as a conflict

Output: one merged record per global_idx (JSONL, gzip if --out ends in .gz):
  {global_idx, task_id, qid, fields:[...], n_attributed, sources:[files]}

  python3 scripts/merge_collab_results.py \
      --results alice.jsonl --results bob.jsonl \
      --dimensions persona/schema/dimensions.json \
      --db /tmp/personabench-wiki-profiles.sqlite \
      --out merged.jsonl.gz --report merge_report.json

Exit 0 if accepted, 1 if any blocking errors were found (nothing is written
when there are errors, unless --force).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BASE_DIR.parents[2]
KIT_DIR = REPO_ROOT / "persona/curation/existing_data/wiki_collab/collab_kit"
if str(KIT_DIR) not in sys.path:
    sys.path.insert(0, str(KIT_DIR))

import conformance  # noqa: E402  (the shared contract checker, bundled with the kit)

MANIFEST_FILE_SHA_KEY = "_package_manifest_file_sha256"


def load_dimensions(path: Path | None) -> list[dict[str, Any]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    dims = payload.get("dimensions") if isinstance(payload, dict) else payload
    if not isinstance(dims, list):
        raise ValueError(f"{path}: expected a dimensions list")
    return dims


def package_manifest_sha256(manifest: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in manifest.items()
        if not key.startswith("_")
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_package_manifest(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    manifest = json.loads(raw.decode("utf-8"))
    if isinstance(manifest, dict):
        manifest[MANIFEST_FILE_SHA_KEY] = hashlib.sha256(raw).hexdigest()
    return manifest


def fetch_db_identity(db_path: Path, indices: list[int]) -> dict[int, dict[str, Any]]:
    if not indices:
        return {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    columns = {
        row["name"]
        for row in conn.execute("pragma table_info(profiles)")
    }
    wanted = ["global_idx", "task_id", "qid"]
    if "input_sha256" in columns:
        wanted.append("input_sha256")
    out: dict[int, dict[str, Any]] = {}
    CHUNK = 900  # stay under SQLite's variable limit
    for i in range(0, len(indices), CHUNK):
        chunk = indices[i : i + CHUNK]
        placeholders = ",".join("?" for _ in chunk)
        for row in conn.execute(
            f"select {', '.join(wanted)} from profiles where global_idx in ({placeholders})",
            chunk,
        ):
            meta = {"task_id": row["task_id"], "qid": row["qid"]}
            if "input_sha256" in row.keys():
                meta["input_sha256"] = row["input_sha256"]
            out[int(row["global_idx"])] = meta
    conn.close()
    return out


def _is_attributed(field: dict[str, Any]) -> bool:
    return field.get("value") is not None and field.get("assignment_type") != "unsupported"


def _runs_for_tally(row: dict[str, Any], run: dict[str, Any]) -> list[dict[str, Any]]:
    unit_runs = run.get("unit_runs")
    if run.get("mixed_provenance") and isinstance(unit_runs, list):
        return [item for item in unit_runs if isinstance(item, dict)]
    return [run] if run else []


def merge_results(
    results_files: list[Path],
    *,
    dimensions: list[dict[str, Any]] | None,
    db_path: Path | None,
    package_manifests: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (merged_records, report). report['errors'] empty == accepted."""
    errors: list[str] = []
    warnings: list[str] = []
    conflicts: list[str] = []
    per_source: dict[str, dict[str, int]] = {}
    models: dict[str, int] = {}
    efforts: dict[str, int] = {}
    runner_versions: dict[str, int] = {}

    # global_idx -> {task_id, qid, fields: {field_id: field}, sources, runs}
    merged: dict[int, dict[str, Any]] = {}
    manifest_by_result: dict[Path, dict[str, Any]] = {}
    if package_manifests:
        if len(package_manifests) != len(results_files):
            errors.append(
                "expected one package manifest per results file in the same order "
                f"(got {len(package_manifests)} manifest(s) for {len(results_files)} result file(s))"
            )
        else:
            manifest_by_result = {
                path: manifest
                for path, manifest in zip(results_files, package_manifests)
            }

    loaded: list[tuple[Path, list[dict[str, Any]]]] = []
    for path in results_files:
        rows = conformance.load_jsonl(path)
        loaded.append((path, rows))
        # 1) format + allowed-value check (no task coverage here)
        f_errors, f_warnings = conformance.check_results(rows, dimensions)
        errors.extend(f"{path.name}: {e}" for e in f_errors)
        warnings.extend(f"{path.name}: {w}" for w in f_warnings)

    # 2) identity check against the source DB
    db_meta: dict[int, dict[str, Any]] = {}
    if db_path is not None:
        all_idx = sorted({
            r["global_idx"]
            for _, rows in loaded
            for r in rows
            if isinstance(r.get("global_idx"), int)
        })
        db_meta = fetch_db_identity(db_path, all_idx)

    for path, rows in loaded:
        name = str(path)  # full path so same-named results.jsonl don't collide
        counts = per_source.setdefault(name, {"records": 0, "attributed": 0})
        for row in rows:
            gi = row.get("global_idx")
            if not isinstance(gi, int):
                continue  # already reported by the format check
            counts["records"] += 1

            # provenance: which model/version/effort produced this record
            run = row.get("run") if isinstance(row.get("run"), dict) else {}
            tally_runs = _runs_for_tally(row, run)
            if not tally_runs:
                model = row.get("model") or "(unspecified)"
                models[model] = models.get(model, 0) + 1
                efforts["(unspecified)"] = efforts.get("(unspecified)", 0) + 1
                runner_versions["(unspecified)"] = runner_versions.get("(unspecified)", 0) + 1
            for tally_run in tally_runs:
                model = tally_run.get("model") or row.get("model") or "(unspecified)"
                effort = tally_run.get("effort") or "(unspecified)"
                rver = tally_run.get("runner_version") or "(unspecified)"
                models[model] = models.get(model, 0) + 1
                efforts[effort] = efforts.get(effort, 0) + 1
                runner_versions[rver] = runner_versions.get(rver, 0) + 1
            if not run:
                warnings.append(f"{name}: global_idx {gi} has no run provenance (model/effort/version)")

            if db_path is not None:
                meta = db_meta.get(gi)
                if meta is None:
                    errors.append(f"{name}: global_idx {gi} not found in --db dataset")
                    continue
                for key in ("task_id", "qid"):
                    if row.get(key) is not None and row.get(key) != meta[key]:
                        errors.append(
                            f"{name}: global_idx {gi} {key} mismatch "
                            f"(result {row.get(key)!r} != dataset {meta[key]!r})"
                        )
                expected_input_sha = meta.get("input_sha256")
                if expected_input_sha:
                    returned_input_sha = row.get("input_sha256")
                    if not returned_input_sha:
                        errors.append(f"{name}: global_idx {gi} has no returned input_sha256")
                    elif returned_input_sha != expected_input_sha:
                        errors.append(
                            f"{name}: global_idx {gi} input_sha256 mismatch "
                            f"(result {returned_input_sha!r} != dataset {expected_input_sha!r})"
                        )

            if package_manifests:
                manifest = manifest_by_result.get(path)
                if manifest is None:
                    continue
                assignment = run.get("assignment") if isinstance(run, dict) else None
                if not isinstance(assignment, dict):
                    errors.append(f"{name}: global_idx {gi} has no run.assignment provenance")
                else:
                    expected_assignment = manifest.get("assignment", {})
                    files = manifest.get("files", {})
                    expected_aid = expected_assignment.get("assignment_id")
                    if expected_aid is not None and assignment.get("assignment_id") != expected_aid:
                        errors.append(
                            f"{name}: global_idx {gi} assignment_id mismatch "
                            f"(result {assignment.get('assignment_id')!r} != manifest {expected_aid!r})"
                        )
                    for key in ("worker_id", "range_start", "range_end"):
                        if key in expected_assignment and assignment.get(key) != expected_assignment.get(key):
                            errors.append(
                                f"{name}: global_idx {gi} assignment {key} mismatch "
                                f"(result {assignment.get(key)!r} != manifest {expected_assignment.get(key)!r})"
                            )
                    start = expected_assignment.get("range_start")
                    end = expected_assignment.get("range_end")
                    if isinstance(start, int) and isinstance(end, int) and not start <= gi < end:
                        errors.append(
                            f"{name}: global_idx {gi} outside assignment range [{start}, {end})"
                        )
                    expected_tasks = files.get("tasks.jsonl", {}).get("sha256")
                    if expected_tasks and assignment.get("tasks_sha256") != expected_tasks:
                        errors.append(
                            f"{name}: global_idx {gi} tasks_sha256 mismatch "
                            f"(result {assignment.get('tasks_sha256')!r} != manifest {expected_tasks!r})"
                        )
                    expected_dims = files.get("dimensions.json", {}).get("sha256")
                    if expected_dims and assignment.get("dimensions_sha256") != expected_dims:
                        errors.append(
                            f"{name}: global_idx {gi} dimensions_sha256 mismatch "
                            f"(result {assignment.get('dimensions_sha256')!r} != manifest {expected_dims!r})"
                        )
                    expected_manifest_sha = manifest.get(MANIFEST_FILE_SHA_KEY)
                    if expected_manifest_sha:
                        returned_manifest_sha = assignment.get("package_manifest_sha256")
                        if not returned_manifest_sha:
                            errors.append(f"{name}: global_idx {gi} has no package_manifest_sha256")
                        elif returned_manifest_sha != expected_manifest_sha:
                            errors.append(
                                f"{name}: global_idx {gi} package_manifest_sha256 mismatch "
                                f"(result {returned_manifest_sha!r} != manifest {expected_manifest_sha!r})"
                            )

            entry = merged.setdefault(
                gi,
                {"task_id": row.get("task_id"), "qid": row.get("qid"),
                 "fields": {}, "sources": [], "runs": []},
            )
            if name not in entry["sources"]:
                entry["sources"].append(name)
            if run and run not in entry["runs"]:
                entry["runs"].append(run)

            for field in row.get("fields", []):
                if _is_attributed(field):
                    counts["attributed"] += 1
                fid = field.get("field_id")
                if not isinstance(fid, str):
                    continue
                prev = entry["fields"].get(fid)
                if prev is None:
                    entry["fields"][fid] = field
                elif prev.get("value") != field.get("value"):
                    # two collaborators disagree on the same dimension for the
                    # same profile; keep the higher-confidence one, report it.
                    conflicts.append(
                        f"global_idx {gi} field '{fid}': {prev.get('value')!r} vs "
                        f"{field.get('value')!r} (kept higher confidence)"
                    )
                    if (field.get("confidence") or 0) > (prev.get("confidence") or 0):
                        entry["fields"][fid] = field

    records = []
    for gi in sorted(merged):
        entry = merged[gi]
        fields = list(entry["fields"].values())
        records.append({
            "global_idx": gi,
            "task_id": entry["task_id"],
            "qid": entry["qid"],
            "fields": fields,
            "n_attributed": sum(1 for f in fields if _is_attributed(f)),
            "sources": entry["sources"],
            "runs": entry["runs"],
        })

    report = {
        "files": [str(p) for p in results_files],
        "merged_profiles": len(records),
        "total_fields": sum(len(r["fields"]) for r in records),
        "total_attributed": sum(r["n_attributed"] for r in records),
        "multi_source_profiles": sum(1 for r in records if len(r["sources"]) > 1),
        "per_source": per_source,
        "provenance": {
            "models": models,
            "efforts": efforts,
            "runner_versions": runner_versions,
        },
        "conflicts": conflicts,
        "errors": errors,
        "warnings": warnings,
        "accepted": not errors,
    }
    return records, report


def write_merged(out: Path, records: list[dict[str, Any]]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if out.suffix == ".gz" else open
    with opener(out, "wt", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", action="append", type=Path, required=True,
                    help="a collaborator's results.jsonl (repeatable)")
    ap.add_argument("--dimensions", type=Path, default=None,
                    help="catalog for allowed-value + drift checks (recommended)")
    ap.add_argument("--db", type=Path, default=None,
                    help="source SQLite to verify global_idx/task_id/qid identity")
    ap.add_argument("--package-manifest", action="append", type=Path, default=None,
                    help="package_manifest.json for assignment provenance checks "
                         "(repeat once per --results, in the same order)")
    ap.add_argument("--out", type=Path, required=True, help="merged JSONL (.gz to gzip)")
    ap.add_argument("--report", type=Path, default=None, help="write a JSON summary here")
    ap.add_argument("--force", action="store_true",
                    help="write the merged output even if there are errors")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dimensions = load_dimensions(args.dimensions)
    manifests = [load_package_manifest(path) for path in (args.package_manifest or [])]
    records, report = merge_results(
        args.results,
        dimensions=dimensions,
        db_path=args.db,
        package_manifests=manifests or None,
    )

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")

    for w in report["warnings"]:
        print(f"WARN  {w}")
    for c in report["conflicts"][:20]:
        print(f"CONFLICT {c}")
    for e in report["errors"][:20]:
        print(f"ERROR {e}")

    if report["errors"] and not args.force:
        print(f"\nFAIL: {len(report['errors'])} error(s); nothing written. "
              f"Fix the inputs or pass --force.")
        return 1

    write_merged(args.out, records)
    print(f"\n{'(forced) ' if report['errors'] else ''}Merged "
          f"{report['merged_profiles']} profiles, {report['total_attributed']} attributed "
          f"fields -> {args.out}")
    prov = report["provenance"]
    print(f"  provenance: models={prov['models']} efforts={prov['efforts']} "
          f"runner_versions={prov['runner_versions']}")
    if report["conflicts"]:
        print(f"  {len(report['conflicts'])} value conflict(s) across sources (see report).")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
