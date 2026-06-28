#!/usr/bin/env python3
"""Synchronize shared Docker snippets into Harbor task build contexts."""

from __future__ import annotations

import argparse
import difflib
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SNIPPETS_DIR = REPO_ROOT / "environment" / "docker-snippets"
MANAGED_SNIPPETS = {
    "install-claude-code.sh": SNIPPETS_DIR / "install-claude-code.sh",
}
TASK_ROOTS = (
    REPO_ROOT / "application" / "tasks",
    REPO_ROOT / "persona" / "tasks",
)


@dataclass(frozen=True)
class ManagedCopy:
    snippet_name: str
    source: Path
    target: Path


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _dockerfile_uses_snippet(dockerfile: Path, snippet_name: str) -> bool:
    return snippet_name in dockerfile.read_text(encoding="utf-8")


def discover_managed_copies() -> list[ManagedCopy]:
    copies: list[ManagedCopy] = []
    for task_root in TASK_ROOTS:
        if not task_root.is_dir():
            continue
        for dockerfile in sorted(task_root.glob("*/environment/Dockerfile")):
            for snippet_name, source in MANAGED_SNIPPETS.items():
                if _dockerfile_uses_snippet(dockerfile, snippet_name):
                    copies.append(
                        ManagedCopy(
                            snippet_name=snippet_name,
                            source=source,
                            target=dockerfile.parent / snippet_name,
                        )
                    )
    return copies


def _diff(source: Path, target: Path) -> str:
    source_lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    target_lines = (
        target.read_text(encoding="utf-8").splitlines(keepends=True)
        if target.exists()
        else []
    )
    return "".join(
        difflib.unified_diff(
            target_lines,
            source_lines,
            fromfile=_relative(target),
            tofile=_relative(source),
        )
    )


def check_copies(copies: list[ManagedCopy]) -> int:
    failures: list[str] = []
    for copy in copies:
        if not copy.source.is_file():
            failures.append(f"Missing source snippet: {_relative(copy.source)}")
            continue
        if not copy.target.is_file():
            failures.append(f"Missing task-local copy: {_relative(copy.target)}")
            continue
        if copy.source.read_text(encoding="utf-8") != copy.target.read_text(
            encoding="utf-8"
        ):
            failures.append(
                f"Out-of-sync Docker snippet: {_relative(copy.target)}\n"
                f"{_diff(copy.source, copy.target)}"
            )

    if failures:
        print(
            "Docker snippet sync check failed. Run "
            "`python scripts/sync_docker_snippets.py --write`.\n",
            file=sys.stderr,
        )
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


def write_copies(copies: list[ManagedCopy]) -> None:
    for copy in copies:
        copy.target.write_text(copy.source.read_text(encoding="utf-8"), encoding="utf-8")
        copy.target.chmod(copy.source.stat().st_mode & 0o777)
        print(f"synced {_relative(copy.target)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail if any managed task-local copy differs from the canonical snippet.",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="Overwrite managed task-local copies with canonical snippets.",
    )
    args = parser.parse_args(argv)

    copies = discover_managed_copies()
    if not copies:
        print("No managed Docker snippet copies found.", file=sys.stderr)
        return 1

    if args.write:
        write_copies(copies)
        return 0
    return check_copies(copies)


if __name__ == "__main__":
    raise SystemExit(main())
