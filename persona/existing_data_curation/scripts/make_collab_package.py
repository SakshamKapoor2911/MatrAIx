#!/usr/bin/env python3
"""Create a worker-facing persona attribution package.

This script is intentionally about the outbound handoff only: it writes the
files a collaborator needs to start work (`tasks.jsonl`, `dimensions.json`,
`assignment.json`, and `collab_kit/`). Owner-side ingestion is handled
separately.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tarfile
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from persona.existing_data_curation.wiki_collab.core import sha256_file, write_json  # noqa: E402

DEFAULT_DIMENSIONS = REPO_ROOT / "persona" / "dimensions.json"
COLLAB_KIT_SRC = (
    REPO_ROOT / "persona/existing_data_curation/wiki_collab/collab_kit"
)
ROOT_LAUNCHER_SRC = REPO_ROOT / "persona/existing_data_curation/wiki_collab/run_assignment.sh"
SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = SLUG_RE.sub("_", value.strip().lower()).strip("_")
    return slug or "uncategorized"


def load_dimensions(dimensions_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(dimensions_path.read_text(encoding="utf-8"))
    dimensions = payload.get("dimensions") if isinstance(payload, dict) else payload
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError(f"{dimensions_path}: expected a non-empty dimensions list")
    return [dict(item) for item in dimensions]


def filter_dimensions(
    dimensions: list[dict[str, Any]], categories: list[str] | None
) -> list[dict[str, Any]]:
    if not categories:
        return dimensions
    wanted = {item.strip() for item in categories if item.strip()}
    filtered = [
        dim
        for dim in dimensions
        if str(dim.get("category", "")) in wanted
        or slugify(str(dim.get("category", ""))) in wanted
    ]
    if not filtered:
        raise ValueError(f"no dimensions matched categories: {sorted(wanted)}")
    return filtered


def load_tasks(db_path: Path, range_start: int, range_end: int) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in conn.execute(
            """
            select global_idx, task_id, qid, title, source_url, profile_text, input_sha256
            from profiles
            where global_idx >= ? and global_idx < ?
            order by global_idx
            """,
            (range_start, range_end),
        )
    ]
    conn.close()
    expected_count = range_end - range_start
    if len(rows) != expected_count:
        raise ValueError(
            f"range [{range_start}, {range_end}) expected {expected_count} rows, got {len(rows)}"
        )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _ignore_collab_kit(dir_path: str, names: list[str]) -> set[str]:
    ignored = set()
    source_dir = Path(dir_path).resolve()
    kit_root = COLLAB_KIT_SRC.resolve()
    for name in names:
        if name == "__pycache__":
            ignored.add(name)
        elif name.endswith(".pyc"):
            ignored.add(name)
        elif name == "worker_out":
            ignored.add(name)
        elif name.endswith(".tar.gz"):
            ignored.add(name)
        elif source_dir == kit_root and (
            name == "results.jsonl" or name.endswith(".progress.jsonl")
        ):
            ignored.add(name)
    return ignored


def copy_collab_kit(out_dir: Path) -> None:
    dst = out_dir / "collab_kit"
    shutil.copytree(COLLAB_KIT_SRC, dst, ignore=_ignore_collab_kit)


def copy_root_launcher(out_dir: Path) -> None:
    dst = out_dir / "run_assignment.sh"
    shutil.copy2(ROOT_LAUNCHER_SRC, dst)
    dst.chmod(dst.stat().st_mode | 0o111)


def _manifest_file_entry(path: Path, *, root: Path, mode: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "path": str(path.relative_to(root)),
    }


def write_package_manifest(out_dir: Path, assignment: dict[str, Any]) -> None:
    immutable = [
        out_dir / "assignment.json",
        out_dir / "tasks.jsonl",
        out_dir / "dimensions.json",
        out_dir / "run_assignment.sh",
        out_dir / "collab_kit" / "harness.py",
        out_dir / "collab_kit" / "conformance.py",
        out_dir / "collab_kit" / "backends.py",
        out_dir / "collab_kit" / "assignment_runner.py",
        out_dir / "collab_kit" / "claude_json_backend.py",
        out_dir / "collab_kit" / "codex_json_backend.py",
    ]
    immutable.extend(sorted((out_dir / "collab_kit" / "schemas").glob("*.json")))

    files: dict[str, Any] = {}
    for path in immutable:
        if path.exists():
            rel = str(path.relative_to(out_dir))
            files[rel] = _manifest_file_entry(path, root=out_dir, mode="immutable")

    solver = out_dir / "collab_kit" / "solver.py"
    if solver.exists():
        rel = str(solver.relative_to(out_dir))
        files[rel] = _manifest_file_entry(solver, root=out_dir, mode="editable")

    manifest = {
        "manifest_version": 1,
        "assignment": {
            "assignment_id": assignment["assignment_id"],
            "worker_id": assignment["worker_id"],
            "dataset_id": assignment["dataset_id"],
            "dataset_sha256": assignment["dataset_sha256"],
            "range_start": assignment["range_start"],
            "range_end": assignment["range_end"],
            "task_count": assignment["task_count"],
            "dimension_count": assignment["dimension_count"],
            "categories": assignment["categories"],
        },
        "files": dict(sorted(files.items())),
    }
    write_json(out_dir / "package_manifest.json", manifest)


def write_worker_readme(out_dir: Path) -> None:
    readme = """# MatrAIx Persona Attribution Assignment

You received a self-contained assignment package. Work inside this directory.
Requires Python 3.10+; no Python packages need to be installed.

Files:

- `assignment.json`: assignment metadata.
- `tasks.jsonl`: Wikipedia person profiles to process.
- `dimensions.json`: persona dimensions and allowed values to fill.
- `package_manifest.json`: checksums for files that should not change.
- `run_assignment.sh`: the main entrypoint.
- `collab_kit/solver.py`: the starter code you may edit.
- `results.jsonl`: the file you send back after a passing run.

Quickstart:

```bash
./run_assignment.sh
./run_assignment.sh --status
./run_assignment.sh --validate
```

Use the menu to choose Codex or Claude Code, effort, parallelism, smoke test,
environment/CLI health check, real run, and validation. Codex uses `gpt-5.5`;
Claude Code uses `claude-opus-4-8`.

The runner verifies checksums before every action, saves settings in
`.wiki_collab_settings.yaml`, and resumes from `results.jsonl.progress.jsonl` if
quota runs out. Repeated backend failures stop the run so you can fix auth/quota
and resume later. You can switch backend/model/effort before resuming; completed
units keep their original provenance, and mixed-backend results are marked in
`results.jsonl`. The code is the same for everyone — only your credentials
differ. `solver.py` ships with the owner's default extraction method and works
as-is. You may improve `solver.py` to get better results; just keep the output
contract unchanged and return only `results.jsonl` unless the owner asks for
logs.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")


def build_archive(out_dir: Path) -> Path:
    archive_path = out_dir.with_suffix(".tar.gz")
    if archive_path.exists():
        archive_path.unlink()
    # Nest everything under a top-level folder named after the package so a
    # collaborator who extracts the archive gets a single clean `<name>/` dir
    # instead of loose files scattered into their current directory.
    top = out_dir.name
    with tarfile.open(archive_path, "w:gz") as tar:
        for path in sorted(out_dir.rglob("*")):
            if path.is_file():
                arcname = str(Path(top) / path.relative_to(out_dir))
                tar.add(path, arcname=arcname, recursive=False)
    return archive_path


def prepare_out_dir(out_dir: Path, *, force: bool) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        if not force:
            raise FileExistsError(f"{out_dir} already exists and is not empty; use --force")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)


def build_collab_package(
    *,
    db_path: Path,
    dimensions_path: Path,
    out_dir: Path,
    assignment_id: str,
    worker_id: str,
    dataset_id: str,
    dataset_sha256: str,
    range_start: int,
    range_end: int,
    categories: list[str] | None,
    create_archive: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    prepare_out_dir(out_dir, force=force)
    tasks = load_tasks(db_path, range_start, range_end)
    dimensions = filter_dimensions(load_dimensions(dimensions_path), categories)

    tasks_path = out_dir / "tasks.jsonl"
    dimensions_out_path = out_dir / "dimensions.json"
    write_jsonl(tasks_path, tasks)
    dimensions_out_path.write_text(
        json.dumps(dimensions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    copy_collab_kit(out_dir)
    copy_root_launcher(out_dir)
    write_worker_readme(out_dir)

    assignment = {
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256,
        "range_start": range_start,
        "range_end": range_end,
        "task_count": len(tasks),
        "dimension_count": len(dimensions),
        "categories": categories or "all",
        "tasks_file": "tasks.jsonl",
        "tasks_sha256": sha256_file(tasks_path),
        "dimensions_file": "dimensions.json",
        "dimensions_sha256": sha256_file(dimensions_out_path),
        "kit": "collab_kit",
        "return_file": "results.jsonl",
    }
    write_json(out_dir / "assignment.json", assignment)
    write_package_manifest(out_dir, assignment)

    archive_path = build_archive(out_dir) if create_archive else None
    return {
        "package_dir": str(out_dir),
        "archive_path": str(archive_path) if archive_path else None,
        "assignment_id": assignment_id,
        "worker_id": worker_id,
        "task_count": len(tasks),
        "dimension_count": len(dimensions),
    }


def parse_range(raw: str) -> tuple[int, int]:
    start_s, end_s = raw.split(":", 1)
    start = int(start_s)
    end = int(end_s)
    if start < 0 or end <= start:
        raise ValueError(f"range must satisfy 0 <= start < end, got {raw!r}")
    return start, end


def parse_categories(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--dimensions", type=Path, default=DEFAULT_DIMENSIONS)
    parser.add_argument("--range", required=True, dest="range_spec")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--assignment-id", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument(
        "--categories",
        help="Comma-separated category names or slugs. Omit to send all dimensions.",
    )
    parser.add_argument("--no-archive", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    range_start, range_end = parse_range(args.range_spec)
    summary = build_collab_package(
        db_path=args.db,
        dimensions_path=args.dimensions,
        out_dir=args.out_dir,
        assignment_id=args.assignment_id,
        worker_id=args.worker_id,
        dataset_id=args.dataset_id,
        dataset_sha256=args.dataset_sha256,
        range_start=range_start,
        range_end=range_end,
        categories=parse_categories(args.categories),
        create_archive=not args.no_archive,
        force=args.force,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
