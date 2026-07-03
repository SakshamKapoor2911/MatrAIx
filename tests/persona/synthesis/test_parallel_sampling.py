from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from persona.synthesis.sampler import PersonaForwardSampler, SamplingConfig, sample_to_file_parallel
from persona.synthesis.sampler.sampler import _pack_nibbles, _unpack_nibbles

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_decode_module():
    path = REPO_ROOT / "persona" / "synthesis" / "scripts" / "decode_persona_codes.py"
    spec = importlib.util.spec_from_file_location("decode_persona_codes", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def test_parallel_codes_output_invariant_to_worker_count(tmp_path: Path) -> None:
    graph_path = tmp_path / "tiny_graph.json"
    _write_tiny_graph(graph_path)

    outputs = []
    for workers, name in [(1, "one.codes"), (3, "three.codes")]:
        out = tmp_path / name
        meta = sample_to_file_parallel(
            graph_path,
            n=11,
            out=out,
            fmt="codes",
            seed=321,
            emit_only=True,
            workers=workers,
            batch_size=4,
        )
        assert meta["packing"] == "nibble"
        assert meta["storage_bytes"] == out.stat().st_size
        outputs.append(out.read_bytes())

    assert outputs[0] == outputs[1]


def test_codes_nibble_roundtrip_matches_jsonl(tmp_path: Path) -> None:
    graph_path = tmp_path / "tiny_graph.json"
    _write_tiny_graph(graph_path)
    codes_out = tmp_path / "personas.codes"
    jsonl_out = tmp_path / "personas.jsonl"

    kwargs = {"n": 10, "seed": 654, "emit_only": True, "workers": 2, "batch_size": 4}
    sample_to_file_parallel(graph_path, out=codes_out, fmt="codes", **kwargs)
    sample_to_file_parallel(graph_path, out=jsonl_out, fmt="jsonl", **kwargs)

    decode = _load_decode_module()
    decoded_out = tmp_path / "decoded.jsonl"
    meta = decode.decode_codes_to_file(codes_out, decoded_out, fmt="jsonl")
    assert meta["samples"] == 10
    assert decoded_out.read_text(encoding="utf-8") == jsonl_out.read_text(encoding="utf-8")


def test_compressed_codes_roundtrip_and_determinism(tmp_path: Path) -> None:
    graph_path = tmp_path / "tiny_graph.json"
    _write_tiny_graph(graph_path)
    jsonl_out = tmp_path / "personas.jsonl"

    kwargs = {"n": 10, "seed": 654, "emit_only": True, "batch_size": 4}
    sample_to_file_parallel(graph_path, out=jsonl_out, fmt="jsonl", workers=2, **kwargs)

    blobs = []
    for workers, name in [(1, "a.codes.gz"), (2, "b.codes.gz")]:
        out = tmp_path / name
        meta = sample_to_file_parallel(
            graph_path, out=out, fmt="codes", workers=workers, compress="gzip", **kwargs
        )
        assert meta["compression"] == "gzip"
        assert meta["storage_bytes"] == out.stat().st_size
        blobs.append(out.read_bytes())
    assert blobs[0] == blobs[1]

    decode = _load_decode_module()
    decoded_out = tmp_path / "decoded.jsonl"
    decode.decode_codes_to_file(tmp_path / "a.codes.gz", decoded_out, fmt="jsonl")
    assert decoded_out.read_text(encoding="utf-8") == jsonl_out.read_text(encoding="utf-8")


def test_decode_supports_unpacked_format_version_1(tmp_path: Path) -> None:
    graph_path = tmp_path / "tiny_graph.json"
    _write_tiny_graph(graph_path)
    sampler = PersonaForwardSampler(graph_path, SamplingConfig(seed=99))
    idx = sampler.sample_indices(7)
    matrix = sampler.codes_matrix(idx)

    codes_out = tmp_path / "legacy.codes"
    matrix.tofile(codes_out)
    schema = sampler.codes_schema(7, codes_out)
    schema["format_version"] = 1
    schema.pop("packing", None)
    schema.pop("row_bytes", None)
    (tmp_path / "legacy.codes.schema.json").write_text(json.dumps(schema), encoding="utf-8")

    decode = _load_decode_module()
    decoded_out = tmp_path / "legacy.jsonl"
    decode.decode_codes_to_file(codes_out, decoded_out, fmt="jsonl")
    rows = [json.loads(line) for line in decoded_out.read_text(encoding="utf-8").splitlines()]
    assert rows == [sampler.decode_row(idx, i) for i in range(7)]


def test_pack_unpack_nibbles_roundtrip() -> None:
    rng = np.random.default_rng(0)
    for cols in (1, 2, 5, 8):
        matrix = rng.integers(0, 16, size=(13, cols)).astype(np.uint8)
        packed = _pack_nibbles(matrix)
        assert packed.shape == (13, (cols + 1) // 2)
        assert np.array_equal(_unpack_nibbles(packed, cols), matrix)


def test_conditional_hard_mask_is_enforced(tmp_path: Path) -> None:
    graph_path = tmp_path / "tiny_graph.json"
    _write_tiny_graph(graph_path)
    sampler = PersonaForwardSampler(graph_path, SamplingConfig(seed=5))
    idx = sampler.sample_indices(500)

    minors = idx["age_bracket"] == sampler.vtoi["age_bracket"]["13-17"]
    power = idx["tool_python"] == sampler.vtoi["tool_python"]["Power user"]
    assert minors.sum() > 0
    assert not (minors & power).any()
