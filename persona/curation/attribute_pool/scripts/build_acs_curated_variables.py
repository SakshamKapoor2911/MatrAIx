import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACS_SOURCE_DIR = ROOT / "sources" / "acs_pums"
ACS_OUTPUT_DIR = ROOT / "outputs" / "acs_pums"
DATA_DICTIONARY = ACS_SOURCE_DIR / "PUMS_Data_Dictionary_2024.csv"
OUT = ACS_OUTPUT_DIR / "acs_pums_curated_variables.csv"

SOURCE_URL = "https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMS_Data_Dictionary_2024.csv"


VARIABLE_GROUPS = [
    (
        "person_or_geography",
        "Demographics & Population Grounding",
        "geographic anchoring",
        ["REGION", "DIVISION", "STATE", "PUMA"],
    ),
    (
        "person",
        "Demographics & Population Grounding",
        "core demographics race ethnicity citizenship nativity and ancestry",
        [
            "AGEP",
            "SEX",
            "HISP",
            "RAC1P",
            "RAC2P",
            "RAC3P",
            "RACAIAN",
            "RACASN",
            "RACBLK",
            "RACNH",
            "RACPI",
            "RACSOR",
            "RACWHT",
            "CIT",
            "NATIVITY",
            "POBP",
            "ANC",
            "ANC1P",
            "ANC2P",
        ],
    ),
    (
        "person",
        "Cognitive & Capability Profile",
        "education language and field of training",
        [
            "LANX",
            "ENG",
            "SCH",
            "SCHL",
            "SCHG",
            "FOD1P",
            "FOD2P",
            "SCIENGP",
            "SCIENGRLP",
        ],
    ),
    (
        "person",
        "Life Context & Constraints",
        "employment work hours occupation industry and income",
        [
            "ESR",
            "WRK",
            "WKL",
            "WKWN",
            "WKHP",
            "COW",
            "OCCP",
            "INDP",
            "SOCP",
            "WAGP",
            "SEMP",
            "PERNP",
            "PINCP",
        ],
    ),
    (
        "person",
        "Life Context & Constraints",
        "poverty public assistance and retirement income",
        ["POVPIP", "PAP", "RETP", "SSP", "SSIP", "OIP"],
    ),
    (
        "person",
        "Life Context & Constraints",
        "health insurance disability and functional difficulty",
        [
            "HINS1",
            "HINS2",
            "HINS3",
            "HINS4",
            "HINS5",
            "HINS6",
            "HINS7",
            "PRIVCOV",
            "PUBCOV",
            "HICOV",
            "DIS",
            "DEAR",
            "DEYE",
            "DREM",
            "DPHY",
            "DOUT",
            "DRAT",
        ],
    ),
    (
        "person",
        "Social Identity, Relationships & Community",
        "family relationship marital status fertility and caregiving",
        [
            "MAR",
            "MARHM",
            "MARHW",
            "MARHD",
            "MARHT",
            "RELSHIPP",
            "FER",
            "GCL",
            "GCM",
            "GCR",
        ],
    ),
    (
        "person",
        "Life Context & Constraints",
        "migration military and place of work",
        ["MIL", "MIG", "MIGSP", "MIGPUMA", "POWSP", "POWPUMA"],
    ),
    (
        "person",
        "Life Context & Constraints",
        "commute and labor-force access",
        ["JWTRNS", "JWMNP", "JWAP", "JWDP", "NWAB", "NWAV", "NWLA", "NWLK", "NWRE"],
    ),
    (
        "housing",
        "Demographics & Population Grounding",
        "household composition and household language",
        [
            "NP",
            "NOC",
            "R18",
            "R60",
            "R65",
            "HHT",
            "HHT2",
            "HHL",
            "LNGI",
            "WIF",
            "WORKSTAT",
        ],
    ),
    (
        "housing",
        "Life Context & Constraints",
        "housing tenure quality costs and material resources",
        [
            "TEN",
            "HINCP",
            "FINCP",
            "VEH",
            "BLD",
            "BDSP",
            "RMSP",
            "ACR",
            "AGS",
            "BATH",
            "KIT",
            "RWAT",
            "HOTWAT",
            "REFR",
            "FS",
            "GRPIP",
            "RNTP",
            "GRNTP",
            "MRGP",
            "MRGT",
            "MRGX",
            "TAXAMT",
            "VALP",
        ],
    ),
    (
        "housing",
        "Life Context & Constraints",
        "technology and communication access",
        [
            "BROADBND",
            "COMPOTHX",
            "DIALUP",
            "LAPTOP",
            "SMARTPHONE",
            "TABLET",
            "TEL",
            "SATELLITE",
        ],
    ),
]


ORDINAL_VARIABLES = {
    "ENG",
    "SCH",
    "SCHL",
    "SCHG",
    "ESR",
    "WKL",
    "DRAT",
    "GCM",
    "MARHT",
    "TEN",
    "GRPIP",
    "POVPIP",
}

NUMERIC_VARIABLES = {
    "AGEP",
    "WKWN",
    "WKHP",
    "WAGP",
    "SEMP",
    "PERNP",
    "PINCP",
    "PAP",
    "RETP",
    "SSP",
    "SSIP",
    "OIP",
    "JWMNP",
    "HINCP",
    "FINCP",
    "NP",
    "NOC",
    "BDSP",
    "RMSP",
    "RNTP",
    "GRNTP",
    "MRGP",
    "TAXAMT",
    "VALP",
}


def read_data_dictionary():
    if not DATA_DICTIONARY.exists():
        raise FileNotFoundError(
            f"Missing {DATA_DICTIONARY}. Download it from {SOURCE_URL} before building ACS curated variables."
        )

    names = {}
    values = {}
    with DATA_DICTIONARY.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            if row[0] == "NAME" and len(row) >= 5:
                names[row[1]] = {
                    "official_type": row[2],
                    "official_length": row[3],
                    "label": row[4],
                }
            elif row[0] == "VAL" and len(row) >= 6:
                var = row[1]
                low = row[4]
                high = row[5] if len(row) > 6 else row[4]
                desc = row[-1]
                code = low if low == high else f"{low}..{high}"
                values.setdefault(var, []).append(f"{code}={desc}")
    return names, values


def curated_variable_metadata():
    seen = set()
    for record_type, category, subcategory, variables in VARIABLE_GROUPS:
        for variable in variables:
            if variable in seen:
                raise ValueError(f"Duplicate curated ACS variable: {variable}")
            seen.add(variable)
            yield {
                "acs_variable": variable,
                "record_type": record_type,
                "primary_category": category,
                "subcategory": subcategory,
            }


def infer_type(variable, official_type, values):
    if variable in NUMERIC_VARIABLES:
        return "numeric", "ratio_or_interval"
    if variable in ORDINAL_VARIABLES:
        return "ordinal", "ordinal"
    if len(values) == 2:
        lowered = " ".join(values).lower()
        if "yes" in lowered and "no" in lowered:
            return "boolean_or_binary", "nominal"
    if official_type == "N" and not values:
        return "numeric", "ratio_or_interval"
    return "categorical", "nominal"


def main():
    ACS_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    ACS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    names, values_by_var = read_data_dictionary()
    rows = []
    missing = []

    for item in curated_variable_metadata():
        variable = item["acs_variable"]
        official = names.get(variable)
        if not official:
            missing.append(variable)
            continue

        values = values_by_var.get(variable, [])
        data_type, measurement_level = infer_type(
            variable, official["official_type"], values
        )
        if len(values) <= 25:
            values_json = json.dumps(values, ensure_ascii=False)
        else:
            values_json = "[]"
        value_notes = "; ".join(values[:12])
        if len(values) > 12:
            value_notes += f"; ... ({len(values)} codebook values; see official ACS data dictionary/code lists)"

        rows.append(
            {
                **item,
                "label": official["label"],
                "definition": official["label"],
                "data_type": data_type,
                "measurement_level": measurement_level,
                "values_json": values_json,
                "value_notes": value_notes,
                "official_type": official["official_type"],
                "official_length": official["official_length"],
                "source_url": SOURCE_URL,
                "notes": "Curated official ACS PUMS population-grounding variable; include as grounding/context, not as a behavioral determinant.",
                "quality_score": "96",
            }
        )

    if missing:
        raise ValueError(
            f"Curated variables missing from ACS data dictionary: {missing}"
        )

    fieldnames = [
        "acs_variable",
        "record_type",
        "label",
        "definition",
        "primary_category",
        "subcategory",
        "data_type",
        "measurement_level",
        "values_json",
        "value_notes",
        "official_type",
        "official_length",
        "source_url",
        "notes",
        "quality_score",
    ]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(
        json.dumps({"curated_acs_variables": len(rows), "output": str(OUT)}, indent=2)
    )


if __name__ == "__main__":
    main()
