#!/usr/bin/env python3
"""Filter Stack Overflow survey rows by answer completeness."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


MISSING_TOKENS = {"", "na", "n/a", "none", "nan", "null", "<na>"}


def is_present(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() not in MISSING_TOKENS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Keep survey rows whose non-missing field ratio is at least the "
            "given threshold. By default, ResponseId is ignored so the score "
            "matches Excel-style scoring from B through the last data column."
        )
    )
    parser.add_argument("input", type=Path, help="Input CSV file")
    parser.add_argument("output", type=Path, help="Output filtered CSV file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Minimum completeness score to keep a row, between 0 and 1",
    )
    parser.add_argument(
        "--ignore-column",
        action="append",
        default=["ResponseId"],
        help="Column to exclude from completeness scoring; may be repeated",
    )
    parser.add_argument(
        "--require-equals",
        action="append",
        default=[],
        metavar="COLUMN=VALUE",
        help=(
            "Keep only rows where COLUMN exactly equals VALUE after trimming "
            "whitespace; may be repeated"
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output if it already exists",
    )
    return parser.parse_args()


def parse_required_equals(specs: list[str]) -> dict[str, str]:
    required: dict[str, str] = {}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"Invalid --require-equals value: {spec!r}")
        column, expected = spec.split("=", 1)
        column = column.strip()
        expected = expected.strip()
        if not column:
            raise ValueError(f"Invalid --require-equals value: {spec!r}")
        required[column] = expected
    return required


def filter_file(
    input_path: Path,
    output_path: Path,
    threshold: float,
    ignore_columns: set[str],
    required_equals: dict[str, str],
) -> None:
    csv.field_size_limit(10_000_000)

    total_rows = 0
    kept_rows = 0
    required_failed_rows = 0
    completeness_failed_rows = 0
    score_sum = 0.0

    with input_path.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames is None:
            raise ValueError(f"Input file has no header row: {input_path}")
        missing_required_columns = [
            column for column in required_equals if column not in reader.fieldnames
        ]
        if missing_required_columns:
            missing = ", ".join(missing_required_columns)
            raise ValueError(f"Required filter column not found: {missing}")

        scored_columns = [
            column for column in reader.fieldnames if column not in ignore_columns
        ]
        if not scored_columns:
            raise ValueError("No columns left to score after applying ignored columns")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_fieldnames = [*reader.fieldnames, "completeness"]

        with output_path.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=output_fieldnames,
                lineterminator="\n",
            )
            writer.writeheader()

            for row in reader:
                total_rows += 1
                present_fields = sum(
                    1 for column in scored_columns if is_present(row.get(column))
                )
                completeness = present_fields / len(scored_columns)
                score_sum += completeness

                passes_required = all(
                    (row.get(column) or "").strip() == expected
                    for column, expected in required_equals.items()
                )
                passes_completeness = completeness >= threshold

                if not passes_required:
                    required_failed_rows += 1
                    continue
                if not passes_completeness:
                    completeness_failed_rows += 1
                    continue

                kept_rows += 1
                row["completeness"] = f"{completeness:.6f}"
                writer.writerow(row)

    dropped_rows = total_rows - kept_rows
    average_score = score_sum / total_rows if total_rows else 0.0
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Scored columns: {len(scored_columns)}")
    print(f"Threshold: {threshold:.2f}")
    if required_equals:
        filters = ", ".join(
            f"{column}={expected}" for column, expected in required_equals.items()
        )
        print(f"Required filters: {filters}")
    print(f"Total rows: {total_rows}")
    print(f"Kept rows: {kept_rows}")
    print(f"Dropped rows: {dropped_rows}")
    print(f"Failed required filters: {required_failed_rows}")
    print(f"Failed completeness after required filters: {completeness_failed_rows}")
    print(f"Average completeness: {average_score:.4f}")


def main() -> int:
    args = parse_args()
    if not 0 <= args.threshold <= 1:
        print("--threshold must be between 0 and 1", file=sys.stderr)
        return 2
    if not args.input.is_file():
        print(f"Input file does not exist: {args.input}", file=sys.stderr)
        return 2
    if args.output.exists() and not args.overwrite:
        print(
            f"Output already exists: {args.output}\n"
            "Use --overwrite or choose a different output path.",
            file=sys.stderr,
        )
        return 2
    try:
        required_equals = parse_required_equals(args.require_equals)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    filter_file(
        input_path=args.input,
        output_path=args.output,
        threshold=args.threshold,
        ignore_columns=set(args.ignore_column),
        required_equals=required_equals,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())