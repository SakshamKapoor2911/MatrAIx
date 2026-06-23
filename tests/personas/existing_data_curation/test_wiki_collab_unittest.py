import gzip
import json
import sqlite3
import tarfile
import tempfile
import unittest
from pathlib import Path

from personas.existing_data_curation.scripts.build_wiki_profile_db import (
    build_profile_database,
)
from personas.existing_data_curation.scripts.make_wiki_assignments import (
    build_assignments,
)
from personas.existing_data_curation.scripts.merge_wiki_results import merge_archives
from personas.existing_data_curation.scripts.validate_wiki_results import (
    validate_result_archive,
)
from personas.existing_data_curation.scripts.audit_wiki_results import audit_archives
from personas.existing_data_curation.wiki_collab.core import (
    Assignment,
    build_result_archive_name,
    load_jsonl,
    load_protocol_manifest,
    parse_range,
    sha256_text,
)
from personas.existing_data_curation.wiki_collab.codex_json_backend import (
    _cli_effort,
    _extract_payload as extract_codex_payload,
    build_codex_command,
)
from personas.existing_data_curation.worker_kit.run_range import run_range
from personas.existing_data_curation.worker_kit.backends import create_backend


def _write_clean_pages(path: Path) -> None:
    rows = [
        {
            "page_id": 2,
            "qid": "Q2",
            "title": "Beta Person",
            "source_url": "https://en.wikipedia.org/wiki/Beta_Person",
            "plain_text": "Beta lead text.",
        },
        {
            "page_id": 1,
            "qid": "Q1",
            "title": "Alpha Person",
            "source_url": "https://en.wikipedia.org/wiki/Alpha_Person",
            "plain_text": "Alpha lead text.",
        },
    ]
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _make_protocol(path: Path) -> None:
    path.mkdir()
    (path / "prompt.md").write_text("Extract JSON for {{input_json}}", encoding="utf-8")
    (path / "output.schema.json").write_text(
        json.dumps({"type": "object"}), encoding="utf-8"
    )
    (path / "protocol_manifest.json").write_text(
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


def _make_dataset(path: Path, row_count: int = 1) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        create table profiles (
          global_idx integer primary key,
          task_id text not null,
          qid text not null,
          title text not null,
          source_url text not null,
          profile_text text not null,
          input_sha256 text not null
        )
        """
    )
    for idx in range(row_count):
        conn.execute(
            "insert into profiles values (?,?,?,?,?,?,?)",
            (
                idx,
                f"wiki_profile:{idx:010d}",
                f"Q{idx}",
                f"Person {idx}",
                f"https://example.test/{idx}",
                f"Profile text {idx}",
                f"{idx}" * 64,
            ),
        )
    conn.commit()
    conn.close()


def _assignment() -> Assignment:
    return Assignment(
        assignment_id="A0001",
        worker_id="alice",
        dataset_id="dataset-v1",
        dataset_sha256="d" * 64,
        protocol_id="persona_attribution_v1",
        protocol_sha256="r" * 64,
        range_start=0,
        range_end=1,
        status="assigned",
    )


def _write_archive(
    path: Path, *, global_idx: int = 0, input_sha256: str = "0" * 64, effort: str = "max"
) -> None:
    work = path.parent / "work"
    work.mkdir()
    result_row = {
        "global_idx": global_idx,
        "task_id": f"wiki_profile:{global_idx:010d}",
        "qid": f"Q{global_idx}",
        "status": "succeeded",
        "input_sha256": input_sha256,
        "provenance": {
            "worker_id": "alice",
            "backend": "mock",
            "provider": "mock",
            "requested_model": "mock-model",
            "reported_model": "mock-model",
            "model_source": "runner",
            "model_confidence": "exact",
            "prompt_sha256": "p" * 64,
            "protocol_sha256": "r" * 64,
            "runner_version": "0.1.0",
            "effort": effort,
        },
        "fields": [
            {
                "field_id": "domain",
                "value": "science",
                "confidence": 0.9,
                "evidence": "Profile text",
                "assignment_type": "summary_inference",
            }
        ],
    }
    manifest = {
        "worker_id": "alice",
        "dataset_id": "dataset-v1",
        "dataset_sha256": "d" * 64,
        "protocol_id": "persona_attribution_v1",
        "protocol_sha256": "r" * 64,
        "range_start": 0,
        "range_end": 1,
        "backend": "mock",
        "provider": "mock",
        "requested_model": "mock-model",
        "reported_models": {"mock-model": 1},
        "auth_mode": "none",
        "concurrency": 2,
        "effort": effort,
        "runner_version": "0.1.0",
        "succeeded": 1,
        "failed": 0,
    }
    with gzip.open(work / "results.jsonl.gz", "wt", encoding="utf-8") as fh:
        fh.write(json.dumps(result_row, ensure_ascii=False) + "\n")
    with gzip.open(work / "failures.jsonl.gz", "wt", encoding="utf-8"):
        pass
    (work / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with tarfile.open(path, "w:gz") as tar:
        tar.add(work / "results.jsonl.gz", arcname="results.jsonl.gz")
        tar.add(work / "failures.jsonl.gz", arcname="failures.jsonl.gz")
        tar.add(work / "run_manifest.json", arcname="run_manifest.json")


class WikiCollabTests(unittest.TestCase):
    def test_core_range_protocol_and_archive_helpers(self):
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
        self.assertTrue(assignment.contains(10))
        self.assertTrue(assignment.contains(19))
        self.assertFalse(assignment.contains(20))
        self.assertEqual(assignment.count, 10)
        self.assertEqual(parse_range("0:50000"), (0, 50000))
        with self.assertRaises(ValueError):
            parse_range("7:3")
        self.assertEqual(
            build_result_archive_name("alice", "persona_attribution_v1", 0, 50000),
            "results_alice_persona_attribution_v1_0000000000_0000050000.tar.gz",
        )

    def test_protocol_manifest_computes_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            protocol_dir = Path(tmp) / "persona_attribution_v1"
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
        self.assertEqual(manifest.prompt_sha256, sha256_text(prompt))
        self.assertEqual(len(manifest.protocol_sha256), 64)

    def test_build_profile_database_and_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "clean"
            source_dir.mkdir()
            _write_clean_pages(source_dir / "part-00000.jsonl.gz")
            out_db = tmp_path / "profiles.sqlite"
            manifest_path = tmp_path / "dataset_manifest.json"
            manifest = build_profile_database(
                clean_dir=source_dir,
                out_db=out_db,
                manifest_path=manifest_path,
                dataset_id="wiki-test-v1",
            )
            conn = sqlite3.connect(out_db)
            rows = conn.execute(
                "select global_idx, page_id, qid, title, task_id, input_sha256 from profiles order by global_idx"
            ).fetchall()
            conn.close()
        self.assertEqual(manifest["row_count"], 2)
        self.assertEqual(
            rows[0][0:5],
            (0, 1, "Q1", "Alpha Person", "wiki_profile:0000000000"),
        )
        self.assertEqual(len(rows[0][5]), 64)

        assignments = build_assignments(
            workers=["alice", "bob", "carol"],
            dataset_id="wiki-test-v1",
            dataset_sha256="d" * 64,
            protocol_id="persona_attribution_v1",
            protocol_sha256="p" * 64,
            row_count=7,
            chunk_size=3,
        )
        self.assertEqual(
            [(a.worker_id, a.range_start, a.range_end) for a in assignments],
            [("alice", 0, 3), ("bob", 3, 6), ("carol", 6, 7)],
        )
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "assignments.jsonl"
            with out_path.open("w", encoding="utf-8") as fh:
                for assignment in assignments:
                    fh.write(json.dumps(assignment.to_dict(), sort_keys=True) + "\n")
            rows = list(load_jsonl(out_path))
        self.assertEqual(rows[2]["assignment_id"], "A0003")

    def test_validate_and_merge_returned_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db = tmp_path / "profiles.sqlite"
            archive = tmp_path / "results.tar.gz"
            out = tmp_path / "merged.jsonl.gz"
            _make_dataset(db)
            _write_archive(archive)
            report = validate_result_archive(
                archive_path=archive,
                db_path=db,
                assignment=_assignment(),
                expected_prompt_sha256="p" * 64,
            )
            first = merge_archives([archive], out)
            second = merge_archives([archive], out)
            with gzip.open(out, "rt", encoding="utf-8") as fh:
                row_count = sum(1 for _ in fh)
        self.assertTrue(report.accepted)
        self.assertEqual(report.valid_rows, 1)
        self.assertEqual(first["written_rows"], 1)
        self.assertEqual(second["duplicate_rows"], 1)
        self.assertEqual(row_count, 1)

    def test_validate_result_archive_rejects_out_of_range_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db = tmp_path / "profiles.sqlite"
            archive = tmp_path / "results.tar.gz"
            _make_dataset(db)
            _write_archive(archive, global_idx=2, input_sha256="2" * 64)
            report = validate_result_archive(
                archive_path=archive,
                db_path=db,
                assignment=_assignment(),
                expected_prompt_sha256="p" * 64,
            )
        self.assertFalse(report.accepted)
        self.assertTrue(
            any("outside assignment range" in error for error in report.errors)
        )

    def test_mock_worker_runs_range_with_concurrency(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db = tmp_path / "profiles.sqlite"
            protocol = tmp_path / "protocol"
            out_dir = tmp_path / "out"
            _make_dataset(db, row_count=5)
            _make_protocol(protocol)
            archive = run_range(
                db_path=db,
                protocol_dir=protocol,
                range_start=1,
                range_end=4,
                backend_name="mock",
                model="mock-model",
                concurrency=3,
                worker_id="alice",
                out_dir=out_dir,
                dataset_id="dataset-v1",
                dataset_sha256="d" * 64,
            )
            with tarfile.open(archive, "r:gz") as tar:
                names = sorted(member.name for member in tar.getmembers())
                tar.extract("results.jsonl.gz", path=out_dir)
                tar.extract("run_manifest.json", path=out_dir)
            with gzip.open(out_dir / "results.jsonl.gz", "rt", encoding="utf-8") as fh:
                rows = [json.loads(line) for line in fh]
            manifest = json.loads(
                (out_dir / "run_manifest.json").read_text(encoding="utf-8")
            )
        self.assertEqual(
            names, ["failures.jsonl.gz", "results.jsonl.gz", "run_manifest.json"]
        )
        self.assertEqual([row["global_idx"] for row in rows], [1, 2, 3])
        self.assertEqual(manifest["succeeded"], 3)
        self.assertEqual(manifest["concurrency"], 3)

    def test_default_models_and_effort_are_recorded(self):
        codex = create_backend("codex-acp", None)
        claude = create_backend("claude-code-acp", None)
        self.assertEqual(codex.model, "gpt-5.5")
        self.assertEqual(claude.model, "claude-opus-4-8")
        self.assertEqual(codex.effort, "max")
        self.assertEqual(claude.effort, "max")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db = tmp_path / "profiles.sqlite"
            protocol = tmp_path / "protocol"
            out_dir = tmp_path / "out"
            _make_dataset(db, row_count=1)
            _make_protocol(protocol)
            archive = run_range(
                db_path=db,
                protocol_dir=protocol,
                range_start=0,
                range_end=1,
                backend_name="mock",
                model=None,
                concurrency=1,
                worker_id="alice",
                out_dir=out_dir,
                dataset_id="dataset-v1",
                dataset_sha256="d" * 64,
            )
            with tarfile.open(archive, "r:gz") as tar:
                tar.extract("results.jsonl.gz", path=out_dir)
                tar.extract("run_manifest.json", path=out_dir)
            with gzip.open(out_dir / "results.jsonl.gz", "rt", encoding="utf-8") as fh:
                rows = [json.loads(line) for line in fh]
            manifest = json.loads(
                (out_dir / "run_manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(manifest["requested_model"], "mock-model")
        self.assertEqual(manifest["effort"], "max")
        self.assertEqual(rows[0]["provenance"]["requested_model"], "mock-model")
        self.assertEqual(rows[0]["provenance"]["effort"], "max")

    def test_codex_cli_wrapper_parses_json_and_builds_command(self):
        payload = extract_codex_payload(
            '```json\n{"fields":[{"field_id":"domain","value":"science",'
            '"confidence":0.9,"evidence":"science","assignment_type":"direct"}],'
            '"reported_model":"gpt-5.5"}\n```'
        )
        cmd = build_codex_command(
            codex_bin="codex",
            requested_model="gpt-5.5",
            effort="max",
            schema_path=Path("/tmp/schema.json"),
            last_message_path=Path("/tmp/last-message.json"),
        )

        self.assertEqual(payload["fields"][0]["field_id"], "domain")
        self.assertEqual(payload["reported_model"], "gpt-5.5")
        self.assertEqual(_cli_effort("max"), "xhigh")
        self.assertEqual(cmd[:2], ["codex", "exec"])
        self.assertIn("--output-schema", cmd)
        self.assertIn("--output-last-message", cmd)
        self.assertIn("-m", cmd)
        self.assertIn("gpt-5.5", cmd)
        self.assertIn('model_reasoning_effort="xhigh"', cmd)

    def test_readme_documents_subscription_wrappers_and_adapter_scope(self):
        readme = Path("personas/existing_data_curation/wiki_collab/README.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("command-adapter integration", readme)
        self.assertIn("claude_json_backend.py", readme)
        self.assertIn("codex_json_backend.py", readme)
        self.assertIn("WIKI_COLLAB_CLAUDE_CMD", readme)
        self.assertIn("WIKI_COLLAB_CODEX_CMD", readme)

    def test_distribution_docs_are_channel_neutral(self):
        readme = Path("personas/existing_data_curation/wiki_collab/README.md").read_text(
            encoding="utf-8"
        )
        assignment_script = Path(
            "personas/existing_data_curation/scripts/make_wiki_assignments.py"
        ).read_text(encoding="utf-8")

        self.assertFalse(
            Path("personas/existing_data_curation/wiki_collab/EMAIL_TEMPLATES.md").exists()
        )
        self.assertNotIn("email", readme.lower())
        self.assertNotIn("email-friendly", assignment_script.lower())

    def test_validate_accepts_non_max_effort_and_audit_reports_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db = tmp_path / "profiles.sqlite"
            archive = tmp_path / "results_low.tar.gz"
            _make_dataset(db)
            _write_archive(archive, effort="low")
            assignment = _assignment()

            report = validate_result_archive(
                archive_path=archive,
                db_path=db,
                assignment=assignment,
                expected_prompt_sha256="p" * 64,
            )
            audit = audit_archives(
                archives=[archive],
                db_path=db,
                assignments=[assignment],
                expected_prompt_sha256="p" * 64,
            )

        self.assertTrue(report.accepted)
        self.assertEqual(audit["summary"]["effort_counts"], {"low": 1})
        self.assertEqual(audit["summary"]["requested_model_counts"], {"mock-model": 1})
        self.assertEqual(audit["summary"]["backend_counts"], {"mock": 1})
        self.assertEqual(audit["coverage"]["assigned_rows"], 1)
        self.assertEqual(audit["coverage"]["covered_rows"], 1)
        self.assertEqual(audit["coverage"]["missing_assigned_rows"], 0)


if __name__ == "__main__":
    unittest.main()
