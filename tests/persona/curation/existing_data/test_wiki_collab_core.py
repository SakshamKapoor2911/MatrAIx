import json
from pathlib import Path

from persona.curation.existing_data.wiki_collab.core import (
    Assignment,
    build_result_archive_name,
    load_protocol_manifest,
    parse_range,
    sha256_text,
)


def test_assignment_uses_half_open_range():
    assignment = Assignment(
        assignment_id="A0001",
        worker_id="alice",
        dataset_id="dataset-v1",
        dataset_sha256="d" * 64,
        protocol_id="persona_attribution_v1",
        protocol_sha256="p" * 64,
        range_start=10,
        range_end=20,
        status="assigned",
    )

    assert assignment.contains(10)
    assert assignment.contains(19)
    assert not assignment.contains(20)
    assert not assignment.contains(9)
    assert assignment.count == 10


def test_parse_range_requires_half_open_positive_order():
    assert parse_range("0:50000") == (0, 50000)

    for raw in ["5:5", "7:3", "-1:10", "abc"]:
        try:
            parse_range(raw)
        except ValueError:
            pass
        else:
            raise AssertionError(f"range {raw!r} should be invalid")


def test_protocol_manifest_computes_hashes(tmp_path: Path):
    protocol_dir = tmp_path / "persona_attribution_v1"
    protocol_dir.mkdir()
    prompt = "Extract fields from {{input_json}}."
    output_schema = {"type": "object", "required": ["fields"]}
    (protocol_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    (protocol_dir / "output.schema.json").write_text(
        json.dumps(output_schema, sort_keys=True), encoding="utf-8"
    )
    (protocol_dir / "protocol_manifest.json").write_text(
        json.dumps(
            {
                "protocol_id": "persona_attribution_v1",
                "protocol_version": "1.0.0",
                "prompt_file": "prompt.md",
                "output_schema_file": "output.schema.json",
            }
        ),
        encoding="utf-8",
    )

    manifest = load_protocol_manifest(protocol_dir)

    assert manifest.protocol_id == "persona_attribution_v1"
    assert manifest.prompt_sha256 == sha256_text(prompt)
    assert manifest.output_schema_sha256 == sha256_text(
        json.dumps(output_schema, sort_keys=True)
    )
    assert len(manifest.protocol_sha256) == 64


def test_result_archive_name_is_stable_and_sortable():
    assert (
        build_result_archive_name("alice", "persona_attribution_v1", 0, 50000)
        == "results_alice_persona_attribution_v1_0000000000_0000050000.tar.gz"
    )

