from __future__ import annotations

import json
from pathlib import Path

from persona.synthesis.sampler import sample_to_file_parallel


def _write_tiny_graph(path: Path) -> None:
    graph = {
        "nodes": [
            {
                "id": "age_bracket",
                "label": "Age",
                "values": ["13-17", "18-24"],
                "prior": {"13-17": 0.4, "18-24": 0.6},
            },
            {
                "id": "tool_python",
                "label": "Python",
                "values": ["Never used", "Power user"],
                "prior": {"Never used": 0.5, "Power user": 0.5},
            },
            {
                "id": "hidden_signal",
                "label": "Hidden signal",
                "values": ["off", "on"],
                "prior": {"off": 0.5, "on": 0.5},
                "emit": False,
            },
        ],
        "directed_proposal_edges": [],
        "full_cpts": [],
        "conditional_masks": [
            {
                "mask_id": "minor_no_power_python",
                "target": "tool_python",
                "condition": {"age_bracket": ["13-17"]},
                "bad_values": ["Power user"],
                "bad_value_multiplier": 0.0,
                "downweight_values": {},
                "preferred_values": ["Never used"],
                "penalize_values_outside_preferred_set": False,
                "outside_preferred_multiplier": 1.0,
            }
        ],
        "proposal_view": {
            "topological_order": ["age_bracket", "tool_python", "hidden_signal"]
        },
    }
    path.write_text(json.dumps(graph), encoding="utf-8")


def test_parallel_jsonl_writes_requested_count_and_metadata(tmp_path: Path) -> None:
    graph_path = tmp_path / "tiny_graph.json"
    out = tmp_path / "personas.jsonl"
    _write_tiny_graph(graph_path)

    meta = sample_to_file_parallel(
        graph_path,
        n=9,
        out=out,
        fmt="jsonl",
        seed=123,
        emit_only=True,
        workers=2,
        batch_size=4,
    )

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 9
    assert all("age_bracket" in row and "tool_python" in row for row in rows)
    assert all("hidden_signal" not in row for row in rows)
    assert meta["samples"] == 9
    assert meta["workers"] == 2
    assert meta["batch_size"] == 4
    assert meta["batches"] == 3
    assert meta["format"] == "jsonl"


def test_parallel_csv_merges_single_header(tmp_path: Path) -> None:
    graph_path = tmp_path / "tiny_graph.json"
    out = tmp_path / "personas.csv"
    _write_tiny_graph(graph_path)

    sample_to_file_parallel(
        graph_path,
        n=5,
        out=out,
        fmt="csv",
        seed=456,
        emit_only=True,
        workers=2,
        batch_size=2,
    )

    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 6
    assert lines[0] == "age_bracket,tool_python"
    assert lines.count("age_bracket,tool_python") == 1


def test_parallel_jsonl_is_deterministic_for_same_seed(tmp_path: Path) -> None:
    graph_path = tmp_path / "tiny_graph.json"
    out_a = tmp_path / "a.jsonl"
    out_b = tmp_path / "b.jsonl"
    _write_tiny_graph(graph_path)

    kwargs = {
        "n": 8,
        "fmt": "jsonl",
        "seed": 789,
        "emit_only": True,
        "workers": 2,
        "batch_size": 3,
    }
    sample_to_file_parallel(graph_path, out=out_a, **kwargs)
    sample_to_file_parallel(graph_path, out=out_b, **kwargs)

    assert out_a.read_bytes() == out_b.read_bytes()
