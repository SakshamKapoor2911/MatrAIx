from __future__ import annotations

import json
from pathlib import Path

from persona.post_process.quality_filter.scan_shard import scan_shard


def test_scans_jsonl_and_writes_rejection_bitmap(tmp_path: Path) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_text(
        "\n".join(
            json.dumps({"fields": fields})
            for fields in [
                [
                    {"field_id": "age_bracket", "value": "5-12"},
                    {"field_id": "demo_marital_status", "value": "Married"},
                ],
                [
                    {"field_id": "age_bracket", "value": "25-34"},
                    {"field_id": "demo_marital_status", "value": "Married"},
                ],
                [
                    {"field_id": "age_bracket", "value": None},
                    {"field_id": "demo_marital_status", "value": "Married"},
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = scan_shard(
        dataset="fixture",
        mode="jsonl",
        source=source,
        output_prefix=tmp_path / "result",
    )

    assert report["rows"] == 3
    assert report["rejected_rows"] == 1
    assert report["rule_violation_counts"] == {"qf_under13_single_only": 1}
    assert (tmp_path / "result.reject.bits").read_bytes() == b"\x01"