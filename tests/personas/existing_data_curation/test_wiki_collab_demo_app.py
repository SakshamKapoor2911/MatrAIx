import gzip
import json
import sqlite3
import tarfile
import tempfile
from pathlib import Path
import unittest

from personas.existing_data_curation.wiki_collab.claude_json_backend import _extract_payload
from personas.existing_data_curation.wiki_collab.demo_app import (
    FALLBACK_HTML,
    audit_returned_archives,
    create_assignment_package,
    dimension_catalog,
    ensure_demo_workspace,
    load_full_clean_page,
    merge_returned_archives,
    preview_result_archive,
    return_archive,
    run_demo_assignment,
    state_payload,
)
from personas.existing_data_curation.wiki_collab.core import sha256_text


def _write_jsonl_gz(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False))
            fh.write("\n")


class WikiCollabDemoAppTests(unittest.TestCase):
    def test_demo_workspace_creates_database_and_assignment_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = ensure_demo_workspace(Path(tmp))

            self.assertGreaterEqual(workspace.dataset_manifest["row_count"], 4)
            self.assertTrue(workspace.db_path.exists())
            self.assertTrue(workspace.assignments_path.exists())

            conn = sqlite3.connect(workspace.db_path)
            rows = conn.execute(
                "select global_idx, title, profile_text from profiles order by global_idx"
            ).fetchall()
            conn.close()

            self.assertEqual(rows[0][0], 0)
            self.assertTrue(any(row[1] == "Abraham Lincoln" for row in rows))
            self.assertTrue(all(row[2] for row in rows))

            assignment = workspace.assignments[0]
            package = create_assignment_package(workspace, assignment)

            with tarfile.open(package, "r:gz") as tar:
                names = {member.name for member in tar.getmembers()}

            self.assertTrue(
                {
                    "assignment.json",
                    "dataset_manifest.json",
                    "profiles.sqlite",
                    "protocol/protocol_manifest.json",
                    "protocol/prompt.md",
                }.issubset(names)
            )

    def test_demo_mock_run_return_audit_and_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = ensure_demo_workspace(Path(tmp))
            assignment = workspace.assignments[0]

            archive = run_demo_assignment(
                workspace,
                assignment,
                backend_name="mock",
                model=None,
                effort="high",
                concurrency=2,
            )
            returned = return_archive(workspace, archive)
            audit = audit_returned_archives(workspace)
            merge_summary = merge_returned_archives(workspace)

            self.assertTrue(returned.exists())
            self.assertEqual(audit["summary"]["accepted_archives"], 1)
            self.assertEqual(audit["summary"]["valid_rows"], assignment.count)
            self.assertEqual(audit["coverage"]["missing_assigned_rows"], 0)
            self.assertEqual(audit["summary"]["effort_counts"], {"high": assignment.count})
            self.assertEqual(merge_summary["written_rows"], assignment.count)

            with gzip.open(workspace.merged_results_path, "rt", encoding="utf-8") as fh:
                rows = [json.loads(line) for line in fh if line.strip()]

            self.assertEqual(len(rows), assignment.count)
            self.assertEqual(rows[0]["provenance"]["backend"], "mock")

    def test_result_preview_explains_latest_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = ensure_demo_workspace(Path(tmp))
            assignment = workspace.assignments[0]

            archive = run_demo_assignment(
                workspace,
                assignment,
                backend_name="mock",
                model=None,
                effort="high",
                concurrency=1,
            )
            returned = return_archive(workspace, archive)
            preview = preview_result_archive(returned)
            state = state_payload(workspace)

            self.assertEqual(preview["row_count"], assignment.count)
            self.assertEqual(preview["rows"][0]["title"], "Abraham Lincoln")
            self.assertEqual(preview["rows"][0]["fields"][0]["field_id"], "source_entity_type")
            self.assertEqual(preview["rows"][0]["fields"][0]["plain_meaning"], "source_entity_type = wiki_person")
            self.assertEqual(preview["rows"][0]["provenance"]["backend"], "mock")
            self.assertEqual(state["result_preview"]["rows"][0]["title"], "Abraham Lincoln")

    def test_demo_run_uses_edited_prompt_as_runtime_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = ensure_demo_workspace(Path(tmp))
            assignment = workspace.assignments[0]
            prompt = (
                "Custom live demo prompt.\n"
                "Return JSON only.\n"
                "INPUT:\n"
                "{{input_json}}\n"
            )

            archive = run_demo_assignment(
                workspace,
                assignment,
                backend_name="mock",
                model=None,
                effort="high",
                concurrency=1,
                prompt_text=prompt,
            )
            preview = preview_result_archive(archive)
            state = state_payload(workspace)

            self.assertEqual(
                preview["rows"][0]["provenance"]["prompt_sha256"],
                sha256_text(prompt),
            )
            self.assertIn("Custom live demo prompt.", state["prompt_template"])
            self.assertIn("Abraham Lincoln", state["rendered_prompt"])

    def test_fallback_html_guides_building_the_spa(self):
        # The hand-rolled vanilla-JS page was removed; when the React dist is
        # absent, _html() serves a small fallback that tells the operator how to
        # build it and notes the JSON API is already live.
        self.assertIn("npm run build", FALLBACK_HTML)
        self.assertIn("/api/state", FALLBACK_HTML)

    def test_dimension_catalog_covers_all_1339_dimensions(self):
        catalog = dimension_catalog()

        self.assertEqual(catalog["total_dimensions"], 1339)
        self.assertEqual(catalog["category_count"], 39)

        categories = catalog["categories"]
        self.assertEqual(sum(c["count"] for c in categories), 1339)
        for cat in categories:
            self.assertTrue(cat["protocol_id"].startswith("persona_attribution_"))
            self.assertEqual(len(cat["dimensions"]), cat["count"])

        # field_id == catalog id by construction: a known dimension is present.
        all_ids = {d["id"] for c in categories for d in c["dimensions"]}
        self.assertIn("age_bracket", all_ids)
        self.assertIn("domain", all_ids)

    def test_state_includes_full_lincoln_article_footprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = ensure_demo_workspace(Path(tmp))
            state = state_payload(workspace)

        footprint = state["lincoln_full_article"]

        self.assertEqual(footprint["title"], "Abraham Lincoln")
        self.assertEqual(footprint["revision_id"], 1357045394)
        self.assertEqual(footprint["source_dump"], "enwiki-20260601")
        self.assertEqual(footprint["wikitext_chars"], 159311)
        self.assertEqual(footprint["plain_text_chars"], 74335)
        self.assertEqual(footprint["section_count"], 34)
        self.assertEqual(footprint["chunk_count"], 56)
        self.assertEqual(footprint["sections"][0]["char_count"], 2415)
        self.assertEqual(footprint["chunk_preview"][0]["char_count"], 1939)

    def test_load_full_clean_page_from_derivative_shards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clean_row = {
                "page_id": 307,
                "qid": "Q91",
                "title": "Abraham Lincoln",
                "source_url": "https://en.wikipedia.org/wiki/Abraham_Lincoln",
                "revision_id": 1360681124,
                "revision_timestamp": "2026-06-22T23:45:48Z",
                "plain_text": "Full clean Lincoln text.\n\nSecond paragraph.",
                "plain_text_chars": 42,
                "section_count": 2,
                "chunk_count": 2,
            }
            section_rows = [
                {"page_id": 307, "qid": "Q91", "title": "Abraham Lincoln", "section_index": 0, "heading": "Lead", "level": 0, "text": "Full clean Lincoln text.", "char_count": 24},
                {"page_id": 307, "qid": "Q91", "title": "Abraham Lincoln", "section_index": 1, "heading": "Legacy", "level": 2, "text": "Second paragraph.", "char_count": 17},
            ]
            chunk_rows = [
                {"page_id": 307, "qid": "Q91", "title": "Abraham Lincoln", "chunk_id": "Q91::lead::000", "section_heading": "Lead", "chunk_index": 0, "text": "Full clean Lincoln text.", "char_count": 24},
                {"page_id": 307, "qid": "Q91", "title": "Abraham Lincoln", "chunk_id": "Q91::legacy::000", "section_heading": "Legacy", "chunk_index": 0, "text": "Second paragraph.", "char_count": 17},
            ]
            _write_jsonl_gz(root / "person_pages_clean/part-00000.jsonl.gz", [{"page_id": 1, "qid": "Q1", "title": "Other", "plain_text": "Other"}])
            _write_jsonl_gz(root / "person_pages_clean/part-00001.jsonl.gz", [clean_row])
            _write_jsonl_gz(root / "person_page_sections/part-00001.jsonl.gz", section_rows)
            _write_jsonl_gz(root / "person_page_chunks/part-00001.jsonl.gz", chunk_rows)

            loaded = load_full_clean_page(root, "abraham lincoln")

        self.assertTrue(loaded["found"])
        self.assertEqual(loaded["clean"]["title"], "Abraham Lincoln")
        self.assertEqual(loaded["clean"]["plain_text"], clean_row["plain_text"])
        self.assertEqual([row["heading"] for row in loaded["sections"]], ["Lead", "Legacy"])
        self.assertEqual([row["chunk_id"] for row in loaded["chunks"]], ["Q91::lead::000", "Q91::legacy::000"])
        self.assertEqual(loaded["source"]["clean_file"], "person_pages_clean/part-00001.jsonl.gz")

    def test_claude_wrapper_parses_markdown_table_fallback(self):
        stdout = json.dumps({
            "type": "result",
            "result": """| Field | Value | Type | Conf |
|---|---|---|---|
| source_entity_type | person | structured_claim | 0.98 |
| creator | null | unsupported | n/a |""",
        })

        payload = _extract_payload(stdout)

        self.assertEqual(payload["fields"][0]["field_id"], "source_entity_type")
        self.assertEqual(payload["fields"][0]["assignment_type"], "structured_claim")
        self.assertEqual(payload["fields"][1]["value"], None)
        self.assertEqual(payload["fields"][1]["confidence"], 0.0)

    def test_claude_wrapper_prefers_structured_output(self):
        stdout = json.dumps({
            "type": "result",
            "result": "Done.",
            "structured_output": {
                "fields": [
                    {
                        "field_id": "domain",
                        "value": "politics/government",
                        "confidence": 0.96,
                        "evidence": "16th president",
                        "assignment_type": "direct",
                    }
                ],
                "reported_model": "claude-opus-4-8",
            },
        })

        payload = _extract_payload(stdout)

        self.assertEqual(payload["fields"][0]["field_id"], "domain")
        self.assertEqual(payload["reported_model"], "claude-opus-4-8")


if __name__ == "__main__":
    unittest.main()
