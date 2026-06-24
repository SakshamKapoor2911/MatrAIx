#!/usr/bin/env python3
"""Build filterable Wikidata attributes for person-only Wikipedia pages."""

from __future__ import annotations

import argparse
import contextlib
import gzip
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ENTITY_PROPERTIES = {
    "P21": "gender_qids",
    "P27": "country_of_citizenship_qids",
    "P106": "occupation_qids",
    "P101": "field_of_work_qids",
    "P19": "place_of_birth_qids",
    "P20": "place_of_death_qids",
    "P69": "educated_at_qids",
    "P108": "employer_qids",
    "P39": "position_held_qids",
    "P166": "award_received_qids",
    "P800": "notable_work_qids",
    "P1412": "languages_spoken_qids",
    "P1441": "present_in_work_qids",
    "P1080": "from_fictional_universe_qids",
    "P170": "creator_qids",
    "P50": "author_qids",
}
DATE_PROPERTIES = {
    "P569": "dates_of_birth",
    "P570": "dates_of_death",
}
PROPERTY_TO_FIELD = {**ENTITY_PROPERTIES, **DATE_PROPERTIES}
FIELD_TO_PROPERTY = {field: prop for prop, field in PROPERTY_TO_FIELD.items()}
COVERAGE_KEYS = {
    "dates_of_birth": "date_of_birth",
    "dates_of_death": "date_of_death",
    **{
        field: field.removesuffix("_qids")
        for field in ENTITY_PROPERTIES.values()
    },
}


def property_pattern(properties: set[str] | list[str] | tuple[str, ...]) -> bytes:
    return b"|".join(
        prop.encode("ascii")
        for prop in sorted(properties, key=lambda item: (-len(item), item))
    )


ENTITY_RE = re.compile(
    rb"^<http://www\.wikidata\.org/entity/(Q\d+)>\s+"
    rb"<http://www\.wikidata\.org/prop/direct/("
    + property_pattern(ENTITY_PROPERTIES)
    + rb")>\s+"
    rb"<http://www\.wikidata\.org/entity/(Q\d+)>\s+\.\s*$"
)
DATE_RE = re.compile(
    rb"^<http://www\.wikidata\.org/entity/(Q\d+)>\s+"
    rb"<http://www\.wikidata\.org/prop/direct/("
    + property_pattern(DATE_PROPERTIES)
    + rb")>\s+"
    rb"\"([^\"]+)\"\^\^<http://www\.w3\.org/2001/XMLSchema#dateTime>\s+\.\s*$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract person filter attributes from Wikidata truthy dump."
    )
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--wikidata-truthy", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=250_000,
        help="Print progress every N matching attribute statements.",
    )
    return parser.parse_args()


def load_candidates(path: Path) -> tuple[dict[str, list[dict]], int]:
    by_qid: dict[str, list[dict]] = {}
    rows = 0
    with gzip.open(path, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            by_qid.setdefault(row["qid"], []).append(
                {
                    "page_id": row["page_id"],
                    "entity_type": row["entity_type"],
                    "tags": row["tags"],
                }
            )
            rows += 1
    return by_qid, rows


@contextlib.contextmanager
def open_attribute_statement_lines(wikidata_truthy: Path):
    decompressor_path = (
        shutil.which("lbzip2")
        or shutil.which("pbzip2")
        or shutil.which("bzip2")
    )
    rg_path = shutil.which("rg")
    if decompressor_path and rg_path:
        decompress = subprocess.Popen(
            [decompressor_path, "-dc", str(wikidata_truthy)],
            stdout=subprocess.PIPE,
        )
        assert decompress.stdout is not None
        rg_property_pattern = "|".join(
            sorted(PROPERTY_TO_FIELD, key=lambda item: (-len(item), item))
        )
        grep = subprocess.Popen(
            [
                rg_path,
                "--text",
                "--no-line-number",
                rf"/prop/direct/({rg_property_pattern})>",
            ],
            stdin=decompress.stdout,
            stdout=subprocess.PIPE,
        )
        decompress.stdout.close()
        assert grep.stdout is not None
        try:
            yield grep.stdout
        finally:
            grep.stdout.close()
            grep_return = grep.wait()
            decompress_return = decompress.wait()
            if grep_return not in (0, 1):
                raise RuntimeError(f"ripgrep failed with exit code {grep_return}")
            if decompress_return != 0:
                raise RuntimeError(
                    f"{Path(decompressor_path).name} failed with exit code {decompress_return}"
                )
        return

    import bz2

    with bz2.open(wikidata_truthy, "rb") as source:
        yield source


def year_from_wikidata_datetime(value: str) -> int | None:
    # Examples: 1809-02-12T00:00:00Z, -0043-03-15T00:00:00Z
    match = re.match(r"^(-?\d{1,})-\d{2}-\d{2}T", value)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def main() -> int:
    args = parse_args()
    start = time.time()

    candidates_by_qid, candidate_pages = load_candidates(args.candidates)
    candidate_qids = set(candidates_by_qid)
    attributes: dict[str, dict] = {
        qid: {field: set() for field in PROPERTY_TO_FIELD.values()}
        for qid in candidate_qids
    }

    statement_count = 0
    matched_subject_count = 0
    with open_attribute_statement_lines(args.wikidata_truthy) as source:
        for line in source:
            entity_match = ENTITY_RE.match(line)
            if entity_match:
                subject = entity_match.group(1).decode("ascii")
                if subject not in candidate_qids:
                    continue
                prop = entity_match.group(2).decode("ascii")
                obj = entity_match.group(3).decode("ascii")
                attributes[subject][ENTITY_PROPERTIES[prop]].add(obj)
                matched_subject_count += 1
            else:
                date_match = DATE_RE.match(line)
                if not date_match:
                    continue
                subject = date_match.group(1).decode("ascii")
                if subject not in candidate_qids:
                    continue
                prop = date_match.group(2).decode("ascii")
                value = date_match.group(3).decode("utf-8")
                attributes[subject][DATE_PROPERTIES[prop]].add(value)
                matched_subject_count += 1

            statement_count += 1
            if statement_count % args.progress_interval == 0:
                print(
                    f"attribute_scan statements={statement_count} "
                    f"matched_subject_statements={matched_subject_count}",
                    file=sys.stderr,
                )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = args.out.with_suffix(args.out.suffix + ".tmp")
    rows = 0
    coverage = {coverage_key: 0 for coverage_key in COVERAGE_KEYS.values()}
    with gzip.open(tmp_path, "wt", encoding="utf-8", compresslevel=3) as out:
        for qid in sorted(candidate_qids, key=lambda item: int(item[1:])):
            values = attributes[qid]
            birth_dates = sorted(values["dates_of_birth"])
            death_dates = sorted(values["dates_of_death"])
            row = {
                "qid": qid,
                "pages": sorted(
                    candidates_by_qid[qid],
                    key=lambda item: (item["page_id"], item["entity_type"]),
                ),
                "dates_of_birth": birth_dates,
                "dates_of_death": death_dates,
                "birth_years": sorted(
                    {
                        year
                        for year in (year_from_wikidata_datetime(value) for value in birth_dates)
                        if year is not None
                    }
                ),
                "death_years": sorted(
                    {
                        year
                        for year in (year_from_wikidata_datetime(value) for value in death_dates)
                        if year is not None
                    }
                ),
                "sources": {
                    field: f"wikidata:{FIELD_TO_PROPERTY[field]}"
                    for field in sorted(FIELD_TO_PROPERTY)
                },
            }
            for field in sorted(ENTITY_PROPERTIES.values()):
                row[field] = sorted(values[field], key=lambda item: int(item[1:]))

            for field, coverage_key in COVERAGE_KEYS.items():
                if row[field]:
                    coverage[coverage_key] += 1

            out.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            out.write("\n")
            rows += 1

    tmp_path.replace(args.out)
    summary = {
        "candidate_pages": candidate_pages,
        "candidate_qids": len(candidate_qids),
        "attribute_rows": rows,
        "coverage": coverage,
        "elapsed_seconds": round(time.time() - start, 3),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
