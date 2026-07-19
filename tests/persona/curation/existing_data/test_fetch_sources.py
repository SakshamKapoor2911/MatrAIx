import json
from argparse import Namespace
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_literature_reference_registry_uses_manifests(tmp_path: Path, monkeypatch):
    from persona.curation.existing_data.scripts import fetch_sources

    base_dir = tmp_path / "existing_data"
    manifests_dir = base_dir / "manifests"
    manifests_dir.mkdir(parents=True)
    monkeypatch.setattr(fetch_sources, "BASE_DIR", base_dir)

    (manifests_dir / "scale.json").write_text(
        json.dumps(
            {
                "id": "scale",
                "source": {"type": "psychometric_reference", "url": "https://example.test"},
                "dimensions_claimed": 3,
                "format": "html",
                "license": "unknown",
                "notes": "sample",
            }
        ),
        encoding="utf-8",
    )
    (manifests_dir / "dataset.json").write_text(
        json.dumps(
            {
                "id": "dataset",
                "source": {"type": "behavior_dataset", "url": "https://example.test"},
            }
        ),
        encoding="utf-8",
    )

    target_root = tmp_path / "raw"
    fetch_sources.fetch_literature_references(
        Namespace(mode="sample", force=False),
        target_root,
    )

    registry = json.loads(
        (target_root / "literature_references" / "reference_registry.json").read_text(
            encoding="utf-8"
        )
    )
    registry_rows = _read_jsonl(
        target_root / "literature_references" / "reference_registry.jsonl"
    )

    assert registry == registry_rows
    assert registry == [
        {
            "id": "scale",
            "source_type": "psychometric_reference",
            "repo_id": None,
            "url": "https://example.test",
            "dimensions_claimed": 3,
            "format": "html",
            "license": "unknown",
            "gated": False,
            "notes": "sample",
            "manifest": "manifests/scale.json",
        }
    ]


def test_dimension_fetch_script_paths_point_to_clean_fetcher():
    dimensions = Path("persona/schema/dimensions.json").read_text(encoding="utf-8")

    assert "personas/existing_data_curation/scripts/fetch_sources.py" not in dimensions
    assert "persona/curation/existing_data/scripts/fetch_sources.py" in dimensions
