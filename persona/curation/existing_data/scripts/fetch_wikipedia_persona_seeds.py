#!/usr/bin/env python3
"""Fetch Wikipedia/Wikidata-backed persona seed records.

The script creates evidence-grounded seed personas from public real or
fictional entities. It intentionally leaves template fields empty when
Wikipedia/Wikidata does not provide direct evidence.

Input JSONL rows can include:

  {"qid": "Q937", "entity_type": "real_person", "name": "Albert Einstein"}
  {"name": "Sherlock Holmes", "entity_type": "fictional_character"}

Output records follow the persona YAML shape used by
personas/Jun20_1k_persona_description, but are written as JSONL for curation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT = BASE_DIR / "outputs" / "wiki_persona_seeds.jsonl"
DEFAULT_LANGUAGE = "en"
DEFAULT_USER_AGENT = (
    "MatrAIxWikipediaPersonaSeeds/0.1 "
    "(research curation; https://github.com/MatrAIx-ai/MatrAIx)"
)

VALID_ENTITY_TYPES = {"real_person", "fictional_character"}
HUMAN_QID = "Q5"

REGION_BY_COUNTRY = {
    "Germany": "Western Europe",
    "German Empire": "Western Europe",
    "United States of America": "North America",
    "Switzerland": "Western Europe",
    "France": "Western Europe",
    "Poland": "Eastern Europe",
    "United Kingdom": "Western Europe",
    "United Kingdom of Great Britain and Ireland": "Western Europe",
    "Mexico": "Latin America",
    "South Africa": "Sub-Saharan Africa",
    "Kingdom of Italy": "Western Europe",
    "Republic of Florence": "Western Europe",
    "Italy": "Western Europe",
}

GENDER_MAP = {
    "male": "Man",
    "female": "Woman",
}

CLAIMS = {
    "instance_of": "P31",
    "sex_or_gender": "P21",
    "occupation": "P106",
    "country_of_citizenship": "P27",
    "date_of_birth": "P569",
    "date_of_death": "P570",
    "languages": "P1412",
    "field_of_work": "P101",
    "notable_work": "P800",
    "creator": "P170",
    "present_in_work": "P1441",
    "fictional_universe": "P1080",
}


@dataclass(frozen=True)
class SeedInput:
    qid: str | None
    name: str | None
    entity_type: str | None


def log(message: str) -> None:
    print(f"[fetch_wikipedia_persona_seeds] {message}", file=sys.stderr)


def request_json(url: str, *, user_agent: str, retries: int, sleep_seconds: float) -> Any:
    delay = max(sleep_seconds, 0.5)
    last_error: Exception | None = None
    for _ in range(retries):
        request = urllib.request.Request(url, headers={"User-Agent": user_agent})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as err:
            last_error = err
            if err.code == 429:
                retry_after = err.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    time.sleep(float(retry_after))
                else:
                    time.sleep(delay)
                    delay *= 2
                continue
            raise
        except urllib.error.URLError as err:
            last_error = err
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"request failed after {retries} retries: {last_error}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no} is not a JSON object")
            rows.append(value)
    return rows


def parse_entity_arg(value: str) -> SeedInput:
    parts = value.split(":", 1)
    qid_or_name = parts[0].strip()
    entity_type = parts[1].strip() if len(parts) == 2 else None
    if entity_type and entity_type not in VALID_ENTITY_TYPES:
        raise ValueError(f"invalid entity type for --entity: {entity_type}")
    if re.fullmatch(r"Q\d+", qid_or_name):
        return SeedInput(qid=qid_or_name, name=None, entity_type=entity_type)
    return SeedInput(qid=None, name=qid_or_name, entity_type=entity_type)


def parse_input_row(row: dict[str, Any]) -> SeedInput:
    qid = str(row["qid"]).strip() if row.get("qid") else None
    name = str(row["name"]).strip() if row.get("name") else None
    entity_type = str(row["entity_type"]).strip() if row.get("entity_type") else None
    if qid and not re.fullmatch(r"Q\d+", qid):
        raise ValueError(f"invalid qid: {qid}")
    if entity_type and entity_type not in VALID_ENTITY_TYPES:
        raise ValueError(f"invalid entity_type: {entity_type}")
    if not qid and not name:
        raise ValueError("input row must include qid or name")
    return SeedInput(qid=qid, name=name, entity_type=entity_type)


def load_seed_inputs(args: argparse.Namespace) -> list[SeedInput]:
    seeds: list[SeedInput] = []
    if args.input:
        seeds.extend(parse_input_row(row) for row in read_jsonl(args.input))
    if args.entity:
        seeds.extend(parse_entity_arg(value) for value in args.entity)
    if not seeds:
        raise ValueError("provide --input or at least one --entity")
    if args.limit is not None:
        return seeds[: args.limit]
    return seeds


def wikidata_entity(qid: str, *, args: argparse.Namespace) -> dict[str, Any]:
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    data = request_json(
        url,
        user_agent=args.user_agent,
        retries=args.retries,
        sleep_seconds=args.sleep_seconds,
    )
    return data["entities"][qid]


def search_wikidata(name: str, *, expected_type: str | None, args: argparse.Namespace) -> str:
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "wbsearchentities",
            "search": name,
            "language": "en",
            "format": "json",
            "limit": "8",
        }
    )
    data = request_json(
        url,
        user_agent=args.user_agent,
        retries=args.retries,
        sleep_seconds=args.sleep_seconds,
    )
    candidates = data.get("search", [])
    if not candidates:
        raise ValueError(f"no Wikidata search results for {name!r}")

    best_qid = candidates[0]["id"]
    for candidate in candidates:
        qid = candidate.get("id")
        if not qid:
            continue
        entity = wikidata_entity(qid, args=args)
        labels = collect_labels_for_entity(entity, args=args)
        validation = validate_entity_type(
            expected_type or infer_entity_type(entity, labels), entity, labels
        )
        if validation["passes"]:
            return qid
    return best_qid


def item_ids(entity: dict[str, Any], prop: str) -> list[str]:
    ids: list[str] = []
    for claim in entity.get("claims", {}).get(prop, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("entity-type") == "item":
            ids.append("Q" + str(value.get("numeric-id")))
    return ids


def time_values(entity: dict[str, Any], prop: str) -> list[str]:
    values: list[str] = []
    for claim in entity.get("claims", {}).get(prop, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("time"):
            values.append(value["time"])
    return values


def chunked(items: Iterable[str], size: int) -> Iterable[list[str]]:
    batch: list[str] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def label_items(ids: Iterable[str], *, args: argparse.Namespace) -> dict[str, str]:
    ids_set = sorted(set(ids))
    labels: dict[str, str] = {}
    for batch in chunked(ids_set, 45):
        url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
            {
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "labels|descriptions",
                "languages": "en|zh",
                "languagefallback": "1",
                "format": "json",
            }
        )
        data = request_json(
            url,
            user_agent=args.user_agent,
            retries=args.retries,
            sleep_seconds=args.sleep_seconds,
        )
        for qid, entity in data.get("entities", {}).items():
            labels[qid] = (
                entity.get("labels", {}).get("en", {}).get("value")
                or entity.get("labels", {}).get("zh", {}).get("value")
                or qid
            )
        time.sleep(args.sleep_seconds)
    return labels


def collect_labels_for_entity(entity: dict[str, Any], *, args: argparse.Namespace) -> dict[str, str]:
    ids = set()
    for prop in CLAIMS.values():
        ids.update(item_ids(entity, prop))
    return label_items(ids, args=args)


def year_from_wikidata_time(value: str | None) -> int | None:
    match = re.match(r"^[+-]?(\d{1,6})", value or "")
    return int(match.group(1)) if match else None


def page_summary(title: str, *, args: argparse.Namespace) -> dict[str, Any]:
    encoded = urllib.parse.quote(title.replace(" ", "_"))
    url = f"https://{args.wikipedia_language}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    data = request_json(
        url,
        user_agent=args.user_agent,
        retries=args.retries,
        sleep_seconds=args.sleep_seconds,
    )
    return {
        "title": data.get("title"),
        "description": data.get("description"),
        "extract": data.get("extract"),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
        "thumbnail": data.get("thumbnail", {}).get("source"),
    }


def first(values: list[Any]) -> Any:
    return values[0] if values else None


def compact(values: Iterable[Any], n: int = 5) -> list[str]:
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            result.append(text)
        if len(result) >= n:
            break
    return result


def age_bracket(age: int | None) -> str | None:
    if age is None:
        return None
    if age < 18:
        return "<18"
    if age <= 24:
        return "18-24"
    if age <= 34:
        return "25-34"
    if age <= 44:
        return "35-44"
    if age <= 54:
        return "45-54"
    if age <= 64:
        return "55-64"
    return "65+"


def infer_entity_type(entity: dict[str, Any], labels: dict[str, str]) -> str | None:
    instance_qids = item_ids(entity, CLAIMS["instance_of"])
    if HUMAN_QID in instance_qids:
        return "real_person"
    instance_labels = " ".join(labels.get(qid, qid).lower() for qid in instance_qids)
    description = entity.get("descriptions", {}).get("en", {}).get("value", "").lower()
    combined = f"{instance_labels} {description}"
    if "fictional" in combined or "character" in combined or "wizard" in combined:
        return "fictional_character"
    return None


def validate_entity_type(
    expected_type: str | None,
    entity: dict[str, Any],
    labels: dict[str, str],
) -> dict[str, Any]:
    inferred = infer_entity_type(entity, labels)
    if expected_type is None:
        return {
            "expected_entity_type": None,
            "inferred_entity_type": inferred,
            "passes": inferred in VALID_ENTITY_TYPES,
            "notes": [],
        }
    notes: list[str] = []
    passes = expected_type == inferred
    if not passes:
        notes.append(
            "entity_type did not match direct Wikidata evidence; inspect before using at scale"
        )
    return {
        "expected_entity_type": expected_type,
        "inferred_entity_type": inferred,
        "passes": passes,
        "notes": notes,
    }


def mapped_labels(entity: dict[str, Any], labels: dict[str, str]) -> dict[str, list[str]]:
    return {
        key: [labels.get(qid, qid) for qid in item_ids(entity, prop)]
        for key, prop in CLAIMS.items()
    }


def entity_name(qid: str, entity: dict[str, Any], labels: dict[str, str]) -> str:
    return (
        labels.get(qid)
        or entity.get("labels", {}).get("en", {}).get("value")
        or entity.get("labels", {}).get("zh", {}).get("value")
        or qid
    )


def choose_title(entity: dict[str, Any], name: str, language: str) -> str:
    sitelink = entity.get("sitelinks", {}).get(f"{language}wiki", {})
    return sitelink.get("title") or name


def make_record(
    *,
    index: int,
    seed: SeedInput,
    qid: str,
    entity: dict[str, Any],
    labels: dict[str, str],
    summary: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    linked = mapped_labels(entity, labels)
    validation = validate_entity_type(seed.entity_type, entity, labels)
    entity_type = seed.entity_type or validation["inferred_entity_type"] or "unknown"
    name = entity_name(qid, entity, labels)

    birth_year = first(
        [year_from_wikidata_time(value) for value in time_values(entity, CLAIMS["date_of_birth"])]
    )
    death_year = first(
        [year_from_wikidata_time(value) for value in time_values(entity, CLAIMS["date_of_death"])]
    )
    current_age = None
    if entity_type == "real_person" and birth_year and not death_year:
        current_age = date.today().year - birth_year
    age_at_death = None
    if entity_type == "real_person" and birth_year and death_year:
        age_at_death = death_year - birth_year

    occupations = linked["occupation"]
    fields = linked["field_of_work"]
    countries = linked["country_of_citizenship"]
    languages = linked["languages"]
    instances = linked["instance_of"]
    present_in = linked["present_in_work"]
    universes = linked["fictional_universe"]
    creators = linked["creator"]
    gender_label = first(linked["sex_or_gender"])

    if entity_type == "real_person":
        domain = first(fields) or first(occupations) or "Public biography"
        role = first(occupations) or first(fields) or "public figure"
        subject_specialty = ", ".join(compact(fields or occupations, 3)) or None
        region = first(
            [REGION_BY_COUNTRY.get(country) for country in countries if REGION_BY_COUNTRY.get(country)]
        )
    elif entity_type == "fictional_character":
        domain = "Fictional character"
        role = first(instances) or "fictional character"
        subject_specialty = ", ".join(compact(present_in or universes or instances, 3)) or None
        region = None
    else:
        domain = "Unknown"
        role = first(occupations) or first(instances) or "unknown"
        subject_specialty = ", ".join(compact(fields or occupations or instances, 3)) or None
        region = None

    return {
        "metadata": {
            "id": f"WIKI{index:04d}",
            "source": "wikidata_wikipedia",
            "entity_type": entity_type,
            "wikidata_qid": qid,
            "wikipedia_language": args.wikipedia_language,
            "wikipedia_title": summary.get("title"),
            "generation_date": args.retrieved_date,
            "license_note": (
                "Wikipedia summary text is CC BY-SA; Wikidata content is CC0. "
                "Preserve page URL/QID attribution before redistribution."
            ),
        },
        "persona": {
            "id": f"wiki_persona_{index:04d}",
            "name": name,
            "title": f"{name} - {role}",
            "age": current_age,
            "description": summary.get("extract"),
            "dimensions": {
                "source_entity_type": entity_type,
                "region": region,
                "gender_identity": GENDER_MAP.get(str(gender_label).lower(), gender_label),
                "age_bracket": age_bracket(current_age),
                "age": current_age,
                "birth_year": birth_year,
                "death_year": death_year,
                "age_at_death": age_at_death,
                "domain": domain,
                "subject_specialty": subject_specialty,
                "role_function": role,
                "primary_language": first(languages),
                "known_for_or_source_work": ", ".join(
                    compact(linked["notable_work"] or present_in or universes, 4)
                )
                or None,
                "creator": ", ".join(compact(creators, 3)) or None,
                "highest_education": None,
                "years_experience": None,
                "company_size": None,
                "marital_status": None,
                "children": None,
                "emotional_state": None,
                "intent": None,
                "personality_big5_openness": None,
                "personality_big5_conscientiousness": None,
                "personality_big5_extraversion": None,
                "personality_big5_agreeableness": None,
                "personality_big5_neuroticism": None,
            },
            "source_evidence": {
                "wikipedia_url": summary.get("url"),
                "summary_description": summary.get("description"),
                "wikidata_instance_of": compact(instances, 8),
                "wikidata_occupations": compact(occupations, 8),
                "wikidata_fields": compact(fields, 8),
                "wikidata_countries": compact(countries, 8),
                "wikidata_languages": compact(languages, 8),
                "wikidata_present_in_work": compact(present_in, 8),
                "wikidata_fictional_universe": compact(universes, 8),
                "wikidata_creator": compact(creators, 8),
            },
            "validation": validation,
            "unsupported_template_fields": [
                "urbanicity",
                "socioeconomic_band",
                "seniority",
                "highest_education",
                "years_experience",
                "company_size",
                "english_proficiency",
                "marital_status",
                "children",
                "emotional_state",
                "intent",
                "big5_traits",
            ],
        },
    }


def fetch_records(seeds: list[SeedInput], args: argparse.Namespace) -> list[dict[str, Any]]:
    qids: list[str] = []
    resolved_seeds: list[SeedInput] = []
    for seed in seeds:
        if seed.qid:
            qid = seed.qid
        else:
            if not seed.name:
                raise ValueError("seed without qid must include name")
            qid = search_wikidata(seed.name, expected_type=seed.entity_type, args=args)
        qids.append(qid)
        resolved_seeds.append(SeedInput(qid=qid, name=seed.name, entity_type=seed.entity_type))
        time.sleep(args.sleep_seconds)

    entities = {qid: wikidata_entity(qid, args=args) for qid in qids}
    all_ids = set(qids)
    for entity in entities.values():
        for prop in CLAIMS.values():
            all_ids.update(item_ids(entity, prop))
    labels = label_items(all_ids, args=args)

    records: list[dict[str, Any]] = []
    for index, seed in enumerate(resolved_seeds, start=1):
        if not seed.qid:
            raise ValueError("resolved seed missing qid")
        entity = entities[seed.qid]
        name = entity_name(seed.qid, entity, labels)
        title = choose_title(entity, name, args.wikipedia_language)
        summary = page_summary(title, args=args)
        records.append(
            make_record(
                index=index,
                seed=seed,
                qid=seed.qid,
                entity=entity,
                labels=labels,
                summary=summary,
                args=args,
            )
        )
        time.sleep(args.sleep_seconds)
    return records


def write_jsonl(records: list[dict[str, Any]], path: Path, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} exists; use --overwrite")
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Input JSONL with qid/name/entity_type rows.")
    parser.add_argument(
        "--entity",
        action="append",
        help="Entity spec as QID[:real_person|fictional_character] or name[:type].",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--wikipedia-language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--retrieved-date", default=str(date.today()))
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    if args.retries <= 0:
        raise ValueError("--retries must be positive")
    if args.sleep_seconds < 0:
        raise ValueError("--sleep-seconds cannot be negative")

    seeds = load_seed_inputs(args)
    log(f"Fetching {len(seeds)} Wikipedia/Wikidata persona seed(s)")
    records = fetch_records(seeds, args)
    write_jsonl(records, args.output, args.overwrite)
    log(f"Wrote {len(records)} record(s) to {args.output}")

    failed = [
        record
        for record in records
        if not record["persona"]["validation"].get("passes")
    ]
    if failed:
        log(f"Warning: {len(failed)} record(s) need entity-type review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
