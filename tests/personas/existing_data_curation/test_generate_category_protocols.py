import json
from pathlib import Path

from personas.existing_data_curation.scripts.generate_category_protocols import (
    LEGACY_FIELDS,
    build_reconciliation,
    generate,
    slugify,
)
from personas.existing_data_curation.wiki_collab.core import load_protocol_manifest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _catalog(path: Path) -> None:
    payload = {
        "schemaVersion": "2.0",
        "dimensions": [
            {
                "id": "age_bracket",
                "label": "Age bracket",
                "category": "Demographic: Core",
                "description": "Life-age band.",
                "values": ["18-24", "25-34"],
            },
            {
                "id": "gender_identity",
                "label": "Gender identity",
                "category": "Demographic: Core",
                "description": "Self-identified gender.",
                "values": ["woman", "man", "nonbinary"],
            },
            {
                "id": "domain",
                "label": "Domain",
                "category": "Expertise: Core",
                "description": "Primary domain.",
                "values": ["Politics", "Science"],
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_slugify():
    assert slugify("Expertise: Domains") == "expertise_domains"
    assert slugify("  Demographic: Core  ") == "demographic_core"


def test_generate_one_protocol_per_category(tmp_path):
    cat_path = tmp_path / "dims.json"
    _catalog(cat_path)
    out = tmp_path / "out"
    legacy = tmp_path / "legacy.json"

    result = generate(cat_path, out, legacy)

    # 2 categories -> 2 protocol dirs, 3 dims total.
    assert result["category_count"] == 2
    assert result["total_dimensions"] == 3
    assert (out / "demographic_core").is_dir()
    assert (out / "expertise_core").is_dir()


def test_generated_protocol_is_loadable_and_aligned(tmp_path):
    cat_path = tmp_path / "dims.json"
    _catalog(cat_path)
    out = tmp_path / "out"
    generate(cat_path, out, tmp_path / "legacy.json")

    proto_dir = out / "demographic_core"
    manifest = load_protocol_manifest(proto_dir)
    assert manifest.protocol_id == "persona_attribution_demographic_core"

    # Prompt is a render_prompt template and lists every dim id by construction.
    prompt = (proto_dir / "prompt.md").read_text(encoding="utf-8")
    assert "{{input_json}}" in prompt
    assert "age_bracket" in prompt and "gender_identity" in prompt
    # Closed-enum values are surfaced for the picker.
    assert "nonbinary" in prompt

    # field_id == catalog id by construction: output schema enum-locks the ids.
    schema = json.loads((proto_dir / "output.schema.json").read_text())
    enum = schema["properties"]["fields"]["items"]["properties"]["field_id"]["enum"]
    assert set(enum) == {"age_bracket", "gender_identity"}

    cat_manifest = json.loads((proto_dir / "category_manifest.json").read_text())
    assert {d["id"] for d in cat_manifest["dimensions"]} == {
        "age_bracket",
        "gender_identity",
    }


def test_index_lists_token_estimates(tmp_path):
    cat_path = tmp_path / "dims.json"
    _catalog(cat_path)
    out = tmp_path / "out"
    generate(cat_path, out, tmp_path / "legacy.json")
    index = json.loads((out / "index.json").read_text())
    assert index["total_dimensions"] == 3
    assert all(e["est_prompt_tokens"] > 0 for e in index["categories"])


def test_reconciliation_against_real_catalog():
    real = REPO_ROOT / "personas" / "dimensions+new.json"
    catalog_ids = {d["id"] for d in json.loads(real.read_text())["dimensions"]}
    recon = build_reconciliation(catalog_ids)

    fields = recon["fields"]
    assert set(fields) == set(LEGACY_FIELDS)

    # The 5 fields that genuinely exist in the catalog map 1:1.
    for fid in ["domain", "subject_specialty", "role_function", "highest_education", "intent"]:
        assert fields[fid]["status"] == "catalog_direct"
        assert fields[fid]["catalog_id"] == fid

    # The 4 drifted fields are flagged, never silently mapped.
    assert fields["source_entity_type"]["status"] == "meta"
    assert fields["creator"]["status"] == "meta"
    assert fields["known_for_or_source_work"]["status"] == "unmapped_freeform"
    assert fields["personality_big5_openness"]["status"] == "domain_level_split"
    # Openness facets are real catalog ids.
    assert fields["personality_big5_openness"]["facet_ids"]
    assert all(f in catalog_ids for f in fields["personality_big5_openness"]["facet_ids"])
