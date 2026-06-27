#!/usr/bin/env python3
"""Validate a returned offline wiki extraction result archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from persona.curation.existing_data.wiki_collab.core import Assignment
from persona.curation.existing_data.wiki_collab.results import validate_archive


def validate_result_archive(
    *,
    archive_path: Path,
    db_path: Path,
    assignment: Assignment,
    expected_prompt_sha256: str,
):
    return validate_archive(
        archive_path=archive_path,
        db_path=db_path,
        assignment=assignment,
        expected_prompt_sha256=expected_prompt_sha256,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--assignment-json", type=Path, required=True)
    parser.add_argument("--prompt-sha256", required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assignment = Assignment.from_dict(json.loads(args.assignment_json.read_text(encoding="utf-8")))
    report = validate_result_archive(
        archive_path=args.archive,
        db_path=args.db,
        assignment=assignment,
        expected_prompt_sha256=args.prompt_sha256,
    )
    payload = report.to_dict()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())

