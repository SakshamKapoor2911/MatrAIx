#!/usr/bin/env python3
"""Prototype ACS PUMS demographic skeleton sampler.

This script is intentionally small and conservative. It reads local ACS PUMS
person records, optionally joins local housing records by SERIALNO, samples
person records with PWGTP, and emits draft MatrAIx persona skeleton records.

Raw Census files and generated outputs should stay under gitignored raw/ paths.
The mappings below are draft rules for review, not final schema policy.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


PERSONAS_DIR = Path(__file__).resolve().parents[2]
EXISTING_DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = PERSONAS_DIR / "dimensions+new.json"
DEFAULT_OUTPUT_DIR = EXISTING_DATA_DIR / "raw" / "acs_pums_skeleton"

AGE_BRACKETS = [
    (13, 17, "13-17"),
    (18, 24, "18-24"),
    (25, 34, "25-34"),
    (35, 44, "35-44"),
    (45, 54, "45-54"),
    (55, 64, "55-64"),
    (65, 200, "65+"),
]

LANGUAGE_CODE_TO_MATRAIX = {
    "1110": "German",
    "1170": "French",
    "1200": "Spanish",
    "1210": "Portuguese",
    "1970": "Mandarin",
    "2000": "Mandarin",
    "2560": "Japanese",
}

PERSON_FIELD_KEYS = [
    "SERIALNO",
    "SPORDER",
    "AGEP",
    "SEX",
    "SCHL",
    "OCCP",
    "INDP",
    "ESR",
    "PINCP",
    "WAGP",
    "MAR",
    "RELSHIPP",
    "ST",
    "PUMA",
    "LANX",
    "LANP",
    "ENG",
    "NATIVITY",
    "CIT",
    "HISP",
    "RAC1P",
    "PWGTP",
]

HOUSING_FIELD_KEYS = ["SERIALNO", "NP", "NOC", "HHL", "TYPEHUGQ"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--person-csv", required=True, type=Path, help="Local ACS PUMS person CSV, e.g. psam_p56.csv.")
    parser.add_argument("--housing-csv", type=Path, help="Optional local ACS PUMS housing CSV, e.g. psam_h56.csv.")
    parser.add_argument("--schema-path", type=Path, default=DEFAULT_SCHEMA, help="MatrAIx dimensions+new.json path.")
    parser.add_argument("--output-jsonl", type=Path, help="Output skeleton JSONL path. Defaults under raw/.")
    parser.add_argument("--summary-json", type=Path, help="Output summary JSON path. Defaults next to output JSONL.")
    parser.add_argument("--sample-size", type=int, default=100, help="Number of skeleton records to sample.")
    parser.add_argument("--min-age", type=int, default=13, help="Minimum AGEP to include in the sample frame.")
    parser.add_argument("--seed", type=int, default=20260622, help="Random seed for weighted sampling.")
    parser.add_argument("--source-id", default="acs_pums_2024_1yr", help="Source id to put in source_origin.")
    parser.add_argument("--source-name", default="ACS PUMS 2024 1-Year person records", help="Source name for source_origin.")
    parser.add_argument("--source-url", default="https://www.census.gov/programs-surveys/acs/microdata/access.html")
    parser.add_argument("--reference-year", default="2024")
    return parser.parse_args()


def to_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def normalize_value(value: str) -> str:
    return value.replace("\u2013", "-").replace("\u2014", "-").casefold()


class SchemaValues:
    def __init__(self, schema_path: Path) -> None:
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        self.values_by_id: dict[str, list[str]] = {
            dim["id"]: dim.get("values", []) for dim in data.get("dimensions", []) if isinstance(dim, dict) and "id" in dim
        }

    def canonical(self, dimension_id: str, draft_value: str | None) -> str | None:
        if draft_value is None:
            return None
        values = self.values_by_id.get(dimension_id, [])
        if draft_value in values:
            return draft_value
        normalized = normalize_value(draft_value)
        for value in values:
            if normalize_value(value) == normalized:
                return value
        return None

    def canonical_or_none(self, dimension_id: str, draft_value: str | None) -> str | None:
        return self.canonical(dimension_id, draft_value)


def age_bracket(age: Any) -> str | None:
    age_int = to_int(age)
    if age_int is None:
        return None
    for lower, upper, label in AGE_BRACKETS:
        if lower <= age_int <= upper:
            return label
    return None


def gender_identity(sex: Any) -> str | None:
    return {"1": "Man", "2": "Woman"}.get(str(sex).strip())


def education(schl: Any) -> str | None:
    code = str(schl).strip().zfill(2)
    if code in {"00", "01", "02", "03", "04", "05", "06", "07", "08"}:
        return "Primary"
    if code in {"09", "10", "11", "12", "13", "14", "15", "16", "17"}:
        return "Secondary"
    if code in {"18", "19", "20"}:
        return "Vocational / cert"
    if code == "21":
        return "Bachelor's"
    if code in {"22", "23"}:
        return "Master's"
    if code == "24":
        return "Doctorate"
    return None


def income_band(value: Any) -> str | None:
    income = to_int(value)
    if income is None:
        return None
    if income < 25_000:
        return "Low income"
    if income < 50_000:
        return "Lower-middle"
    if income < 100_000:
        return "Middle"
    if income < 200_000:
        return "Upper-middle"
    return "High income"


def marital(mar: Any) -> str | None:
    return {"1": "Married", "2": "Widowed", "3": "Divorced", "4": "Separated", "5": "Single"}.get(str(mar).strip())


def employment(esr: Any, age: Any) -> str | None:
    code = str(esr).strip()
    age_int = to_int(age)
    if code in {"1", "2", "4", "5"}:
        return "Full-time"
    if code == "3":
        return "Unemployed"
    if code == "6" and age_int is not None and age_int >= 65:
        return "Retired"
    return None


def english_proficiency(row: dict[str, str], housing_row: dict[str, str] | None) -> str | None:
    eng = str(row.get("ENG", "")).strip().lower()
    mapped = {
        "b": "Native",
        "1": "Fluent (C1-C2)",
        "2": "Intermediate (B1-B2)",
        "3": "Basic (A1-A2)",
        "4": "None",
    }.get(eng)
    if mapped:
        return mapped
    # In ACS PUMS, ENG can be blank/not applicable for people who speak only English.
    if str(row.get("LANX", "")).strip() == "2" or str((housing_row or {}).get("HHL", "")).strip() == "1":
        return "Native"
    return None


def citizenship(cit: Any) -> str | None:
    code = str(cit).strip()
    if code in {"1", "2", "3"}:
        return "Citizen by birth"
    if code == "4":
        return "Naturalized citizen"
    return None


def ethnicity(hisp: Any, rac1p: Any) -> str | None:
    # ACS HISP code 01 means not Spanish/Hispanic/Latino. Codes greater than 01 indicate Hispanic origin.
    hisp_code = to_int(hisp)
    race_code = str(rac1p).strip()
    if hisp_code is not None and hisp_code > 1:
        return "Hispanic / Latino"
    return {
        "1": "White / European",
        "2": "Black / African",
        "3": "Indigenous",
        "4": "Indigenous",
        "5": "Indigenous",
        "6": "East Asian",
        "7": "Pacific Islander",
        "8": "Multiracial",
        "9": "Multiracial",
    }.get(race_code)


def primary_language(row: dict[str, str], housing_row: dict[str, str] | None) -> str | None:
    lanx = str(row.get("LANX", "")).strip()
    lanp = str(row.get("LANP", "")).strip()
    household_language = str((housing_row or {}).get("HHL", "")).strip()
    if lanp in LANGUAGE_CODE_TO_MATRAIX:
        return LANGUAGE_CODE_TO_MATRAIX[lanp]
    if lanx == "2" or household_language == "1":
        return "English"
    if household_language == "2":
        return "Spanish"
    return None


def household_size(housing_row: dict[str, str] | None) -> str | None:
    if not housing_row:
        return None
    group_quarters_type = str(housing_row.get("TYPEHUGQ", "")).strip()
    if group_quarters_type and group_quarters_type != "1":
        return "Communal"
    people = to_int(housing_row.get("NP"))
    if people is None:
        return None
    if people == 1:
        return "Lives alone"
    if people == 2:
        return "2 people"
    if 3 <= people <= 4:
        return "3-4 people"
    if people >= 5:
        return "5+ people"
    return None


def children_count(housing_row: dict[str, str] | None) -> str | None:
    if not housing_row:
        return None
    own_children = to_int(housing_row.get("NOC"))
    if own_children is None:
        return None
    if own_children == 0:
        return "None"
    if own_children == 1:
        return "1 child"
    if own_children == 2:
        return "2 children"
    if own_children >= 3:
        return "3+ children"
    return None


def domain_from_industry(indp: Any) -> str | None:
    code = to_int(indp)
    if code is None:
        return None
    if 170 <= code <= 490:
        return "Agriculture"
    if code == 770:
        return "Skilled Trades"
    if 1070 <= code <= 3990:
        return "Manufacturing"
    if 4070 <= code <= 5791:
        return "Business & Management"
    if 6070 <= code <= 6390:
        return "Engineering"
    if 6471 <= code <= 6781:
        return "Media & Journalism"
    if 6871 <= code <= 7190:
        return "Finance & Economics"
    if 7270 <= code <= 7790:
        return "Business & Management"
    if 7860 <= code <= 7890:
        return "Education"
    if 7970 <= code <= 8470:
        return "Healthcare & Medicine"
    if 8561 <= code <= 8690:
        return "Hospitality"
    if 8770 <= code <= 9290:
        return "Business & Management"
    if 9370 <= code <= 9870:
        return "Public Sector"
    return None


def role_from_occupation(occp: Any) -> str | None:
    code = to_int(occp)
    if code is None:
        return None
    if 10 <= code <= 440:
        return "Executive"
    if 500 <= code <= 960:
        return "Finance"
    if 1005 <= code <= 1560:
        return "Engineering"
    if 1600 <= code <= 1980:
        return "Research"
    if 2001 <= code <= 2060:
        return "Operations"
    if 2100 <= code <= 2180:
        return "Legal"
    if 2205 <= code <= 2555:
        return "Teaching"
    if 2600 <= code <= 2920:
        return "Design"
    if 3000 <= code <= 3550:
        return "Clinical"
    if 3601 <= code <= 4655:
        return "Operations"
    if 4700 <= code <= 4965:
        return "Sales / GTM"
    if 5000 <= code <= 9760:
        return "Operations"
    return None


def row_hash(row: dict[str, str]) -> str:
    stable = "|".join(str(row.get(key, "")) for key in ["SERIALNO", "SPORDER", "ST", "PUMA", "PWGTP", "AGEP", "SEX"])
    return "sha256:" + hashlib.sha256(stable.encode("utf-8")).hexdigest()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_housing_rows(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    return {row["SERIALNO"]: row for row in read_csv_rows(path) if row.get("SERIALNO")}


def add_if_valid(dimensions: dict[str, str], schema: SchemaValues, dimension_id: str, draft_value: str | None) -> bool:
    value = schema.canonical_or_none(dimension_id, draft_value)
    if value is None:
        return False
    dimensions[dimension_id] = value
    return True


def build_dimensions(row: dict[str, str], housing_row: dict[str, str] | None, schema: SchemaValues) -> tuple[dict[str, str], list[dict[str, str]]]:
    dimensions: dict[str, str] = {}
    unsupported: list[dict[str, str]] = []

    draft_mappings = {
        "age_bracket": age_bracket(row.get("AGEP")),
        "region": "North America",
        "gender_identity": gender_identity(row.get("SEX")),
        "highest_education": education(row.get("SCHL")),
        "socioeconomic_band": income_band(row.get("PINCP")),
        "demo_marital_status": marital(row.get("MAR")),
        "demo_employment_status": employment(row.get("ESR"), row.get("AGEP")),
        "english_proficiency": english_proficiency(row, housing_row),
        "demo_citizenship_status": citizenship(row.get("CIT")),
        "demo_ethnicity_broad": ethnicity(row.get("HISP"), row.get("RAC1P")),
        "primary_language": primary_language(row, housing_row),
        "lstyle_household_size": household_size(housing_row),
        "demo_children_count": children_count(housing_row),
        "domain": domain_from_industry(row.get("INDP")),
        "role_function": role_from_occupation(row.get("OCCP")),
    }

    for dimension_id, draft_value in draft_mappings.items():
        if draft_value is None:
            unsupported.append(
                {
                    "dimension_id": dimension_id,
                    "reason": "No conservative mapping was available from the local PUMS fields used in this prototype.",
                }
            )
            continue
        if not add_if_valid(dimensions, schema, dimension_id, draft_value):
            unsupported.append(
                {
                    "dimension_id": dimension_id,
                    "reason": f"Draft value {draft_value!r} is not an allowed MatrAIx value for this dimension.",
                }
            )

    unsupported.append(
        {
            "dimension_id": "urbanicity",
            "reason": "PUMA alone is not mapped to MatrAIx urbanicity in this prototype; needs a reviewed PUMA-to-urbanicity crosswalk.",
        }
    )
    return dimensions, unsupported


def default_output_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.output_jsonl:
        output_jsonl = args.output_jsonl
    else:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_jsonl = DEFAULT_OUTPUT_DIR / f"acs_pums_skeleton_n{args.sample_size}.jsonl"
    if args.summary_json:
        summary_json = args.summary_json
    else:
        summary_json = output_jsonl.with_suffix(".summary.json")
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    return output_jsonl, summary_json


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    schema = SchemaValues(args.schema_path)
    housing_rows = load_housing_rows(args.housing_csv)
    person_rows = []

    for row in read_csv_rows(args.person_csv):
        age = to_int(row.get("AGEP"))
        weight = to_int(row.get("PWGTP")) or 0
        if age is None or age < args.min_age or weight <= 0:
            continue
        person_rows.append(row)

    if len(person_rows) < args.sample_size:
        raise SystemExit(f"Only {len(person_rows)} eligible rows available for sample size {args.sample_size}.")

    sampled = random.choices(person_rows, weights=[int(row["PWGTP"]) for row in person_rows], k=args.sample_size)
    output_jsonl, summary_json = default_output_paths(args)
    dimension_counts: dict[str, Counter[str]] = {}
    unsupported_counts: Counter[str] = Counter()

    with output_jsonl.open("w", encoding="utf-8", newline="\n") as output:
        for index, row in enumerate(sampled, start=1):
            housing_row = housing_rows.get(row.get("SERIALNO", ""))
            dimensions, unsupported = build_dimensions(row, housing_row, schema)
            for dimension_id, value in dimensions.items():
                dimension_counts.setdefault(dimension_id, Counter())[value] += 1
            for item in unsupported:
                unsupported_counts[item["dimension_id"]] += 1

            record = {
                "record_id": f"{args.source_id}_{index:04d}",
                "source_origin": {
                    "source_id": args.source_id,
                    "source_name": args.source_name,
                    "source_type": "official_population_microdata",
                    "source_url": args.source_url,
                    "reference_year": args.reference_year,
                    "source_record_hash": row_hash(row),
                    "sampling_weight": to_int(row.get("PWGTP")),
                },
                "raw_pums_fields": {key: row.get(key) for key in PERSON_FIELD_KEYS if key in row},
                "dimensions": dimensions,
                "unsupported_fields": unsupported,
            }
            if housing_row:
                record["raw_housing_fields"] = {key: housing_row.get(key) for key in HOUSING_FIELD_KEYS if key in housing_row}
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = {
        "source": args.source_name,
        "source_url": args.source_url,
        "sample_mode": "weighted_with_replacement",
        "random_seed": args.seed,
        "eligible_rows": len(person_rows),
        "sampled_rows": len(sampled),
        "person_csv": str(args.person_csv),
        "housing_csv": str(args.housing_csv) if args.housing_csv else None,
        "output_jsonl": str(output_jsonl),
        "summary_json": str(summary_json),
        "mapping_status": "draft prototype; mappings need review before reuse",
        "counts": {dimension_id: dict(counter) for dimension_id, counter in sorted(dimension_counts.items())},
        "unsupported_counts": dict(unsupported_counts),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()