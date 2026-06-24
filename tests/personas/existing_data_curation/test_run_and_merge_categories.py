import gzip
import json
import sqlite3
import tarfile
from pathlib import Path

from personas.existing_data_curation.scripts.run_all_categories import (
    discover_categories,
    run_all_categories,
)
from personas.existing_data_curation.scripts.merge_persona_records import (
    merge_persona_records,
)
from personas.existing_data_curation.wiki_collab.core import (
    compute_input_sha256,
    profile_input_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PROTOCOLS_DIR = (
    REPO_ROOT
    / "personas/existing_data_curation/protocols/persona_attribution_by_category"
)
DIMENSIONS = REPO_ROOT / "personas" / "dimensions+new.json"


def _make_db(path: Path) -> str:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        create table profiles (
          global_idx integer primary key,
          task_id text not null,
          page_id integer not null,
          qid text not null,
          title text not null,
          source_url text not null,
          profile_text text not null,
          input_sha256 text not null
        )
        """
    )
    row = {
        "global_idx": 0,
        "task_id": "wiki_profile:0000000000",
        "page_id": 307,
        "qid": "Q91",
        "title": "Abraham Lincoln",
        "source_url": "https://en.wikipedia.org/wiki/Abraham_Lincoln",
        "profile_text": "Abraham Lincoln was the 16th president of the United States.",
    }
    sha = compute_input_sha256(profile_input_payload(row))
    conn.execute(
        "insert into profiles values (?,?,?,?,?,?,?,?)",
        (
            row["global_idx"],
            row["task_id"],
            row["page_id"],
            row["qid"],
            row["title"],
            row["source_url"],
            row["profile_text"],
            sha,
        ),
    )
    conn.commit()
    conn.close()
    return sha


def _write_fake_archive(
    path: Path, *, global_idx: int, qid: str, protocol_id: str, fields: list[dict]
) -> None:
    """Build a minimal results archive (results.jsonl.gz + run_manifest.json)."""
    work = path.parent / (path.name.removesuffix(".tar.gz") + "_work")
    work.mkdir(parents=True, exist_ok=True)
    row = {"global_idx": global_idx, "qid": qid, "title": "X", "fields": fields}
    with gzip.open(work / "results.jsonl.gz", "wt", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    (work / "run_manifest.json").write_text(
        json.dumps({"protocol_id": protocol_id}), encoding="utf-8"
    )
    with tarfile.open(path, "w:gz") as tar:
        tar.add(work / "results.jsonl.gz", arcname="results.jsonl.gz")
        tar.add(work / "run_manifest.json", arcname="run_manifest.json")


def test_discover_categories_finds_all_39():
    slugs = discover_categories(PROTOCOLS_DIR)
    assert len(slugs) == 39
    assert "demographic_core" in slugs


def test_discover_categories_subset():
    slugs = discover_categories(PROTOCOLS_DIR, ["demographic_core", "missing_x"])
    assert slugs == ["demographic_core"]


def test_run_all_categories_subset_produces_one_archive_per_category(tmp_path):
    db = tmp_path / "profiles.sqlite"
    sha = _make_db(db)
    out = tmp_path / "runs"
    produced = run_all_categories(
        db_path=db,
        protocols_dir=PROTOCOLS_DIR,
        range_start=0,
        range_end=1,
        backend_name="mock",
        model=None,
        effort="high",
        concurrency=1,
        worker_id="alice",
        out_dir=out,
        dataset_id="ds",
        dataset_sha256=sha,
        categories=["demographic_core", "interests_media"],
        jobs=2,  # exercise the parallel-over-categories path
    )
    assert len(produced) == 2
    assert all("archive" in p for p in produced)
    archives = list(out.glob("*.tar.gz"))
    assert len(archives) == 2


def test_merge_unions_fields_across_archives_with_coverage(tmp_path):
    # Two archives, SAME global_idx, DIFFERENT catalog dims -> union, not dedup.
    a1 = tmp_path / "a1.tar.gz"
    a2 = tmp_path / "a2.tar.gz"
    _write_fake_archive(
        a1,
        global_idx=0,
        qid="Q91",
        protocol_id="persona_attribution_demographic_core",
        fields=[
            {"field_id": "age_bracket", "value": "55–64", "confidence": 0.8,
             "evidence": "born 1809", "assignment_type": "summary_inference"},
            {"field_id": "gender_identity", "value": None, "confidence": 0.0,
             "evidence": "", "assignment_type": "unsupported"},
        ],
    )
    _write_fake_archive(
        a2,
        global_idx=0,
        qid="Q91",
        protocol_id="persona_attribution_expertise_core",
        fields=[
            {"field_id": "domain", "value": "Politics", "confidence": 0.95,
             "evidence": "16th president", "assignment_type": "direct"},
            # an id not in the catalog -> flagged as drift, never silently mapped
            {"field_id": "source_entity_type", "value": "wiki_person", "confidence": 1.0,
             "evidence": "X", "assignment_type": "direct"},
        ],
    )

    records = merge_persona_records([a1, a2], DIMENSIONS)
    assert len(records) == 1
    rec = records[0]

    # Union: all 4 field ids present on one record (NOT deduped to one archive).
    assert set(rec["dimensions"]) == {
        "age_bracket",
        "gender_identity",
        "domain",
        "source_entity_type",
    }
    cov = rec["coverage"]
    assert cov["total_dimensions"] == 1339
    # attributed = age_bracket + domain (gender unsupported, source_entity_type unmapped)
    assert cov["attributed"] == 2
    assert cov["in_catalog_fields"] == 3  # age_bracket, gender_identity, domain
    assert cov["unmapped_fields"] == 1  # source_entity_type
    assert "Demographic: Core" in cov["by_category"]
    # protocol_id is carried per dimension for traceability
    assert rec["dimensions"]["domain"]["protocol_id"] == "persona_attribution_expertise_core"
    assert rec["dimensions"]["domain"]["in_catalog"] is True
    assert rec["dimensions"]["source_entity_type"]["in_catalog"] is False
