#!/usr/bin/env python3
"""Build canonical synthetic and human quality-filter task manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PERSONA_ROOT = REPO_ROOT / "persona"
DATA_ROOT = PERSONA_ROOT / "human_extraction/data"
SYNTHETIC_ROOT = PERSONA_ROOT / "synthesis/generated/full_dag_10b_20260703/shards"


def _stem(path: Path) -> str:
    name = path.name
    for suffix in (".codes.gz", ".jsonl.gz", ".jsonl"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _task(dataset: str, mode: str, source: Path, output_root: Path) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "mode": mode,
        "source": str(source),
        "output_prefix": str(output_root / dataset / _stem(source)),
    }


def synthetic_tasks(output_root: Path) -> list[dict[str, Any]]:
    paths = sorted(SYNTHETIC_ROOT.glob("full_dag_100000000_shard_*.codes.gz"))
    if len(paths) != 100:
        raise ValueError(f"expected 100 synthetic shards, found {len(paths)}")
    return [_task("synthetic", "codes", path, output_root) for path in paths]


def amazon_paths() -> list[Path]:
    amazon = DATA_ROOT / "amazon"
    completion = json.loads(
        (amazon / "extraction_resume_20260717/EXTRACTION_COMPLETE.json").read_text()
    )
    continuation_buckets = set(completion["buckets"])
    paths = []
    for value in range(256):
        bucket = f"{value:02x}"
        if bucket in continuation_buckets:
            path = amazon / f"extraction_resume_20260717/shard_{bucket}.jsonl"
        else:
            path = amazon / f"hf_snapshot_20260719/data/shard_{bucket}.jsonl.gz"
        if not path.is_file():
            raise FileNotFoundError(path)
        paths.append(path)
    return paths


def human_tasks(output_root: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []

    wiki_paths = sorted((DATA_ROOT / "wiki/extraction_v1").glob("shard_*.jsonl"))
    if len(wiki_paths) != 200:
        raise ValueError(f"expected 200 Wiki shards, found {len(wiki_paths)}")
    tasks.extend(_task("wiki", "jsonl", path, output_root) for path in wiki_paths)
    tasks.extend(_task("amazon", "jsonl", path, output_root) for path in amazon_paths())

    stackoverflow = (
        DATA_ROOT
        / "stackoverflow/hf_pr55/StackExchange_Persona/extraction_v1/qwen36"
        / "stackoverflow_vllm_v2_pr53_compatible"
    )
    for year in range(2023, 2026):
        path = stackoverflow / str(year) / f"merged_{year}_hf_pr53.jsonl"
        if not path.is_file():
            raise FileNotFoundError(path)
        tasks.append(_task("stackoverflow", "jsonl", path, output_root))

    prism = DATA_ROOT / "prism/hf_main/extraction_v1/shard_00.jsonl.gz"
    if not prism.is_file():
        raise FileNotFoundError(prism)
    tasks.append(_task("prism", "jsonl", prism, output_root))

    gss_paths = sorted((DATA_ROOT / "gss/hf_main/extraction_v1").glob("shard_*.jsonl.gz"))
    if len(gss_paths) != 5:
        raise ValueError(f"expected 5 GSS shards, found {len(gss_paths)}")
    tasks.extend(_task("gss", "jsonl", path, output_root) for path in gss_paths)
    return tasks


def _write_manifest(path: Path, tasks: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(task, sort_keys=True) + "\n" for task in tasks),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest-dir", type=Path, required=True)
    args = parser.parse_args()

    synthetic = synthetic_tasks(args.output_root)
    human = human_tasks(args.output_root)
    synthetic_manifest = args.manifest_dir / "synthetic_tasks.jsonl"
    human_manifest = args.manifest_dir / "human_tasks.jsonl"
    _write_manifest(synthetic_manifest, synthetic)
    _write_manifest(human_manifest, human)
    print(
        json.dumps(
            {
                "synthetic_manifest": str(synthetic_manifest),
                "synthetic_tasks": len(synthetic),
                "human_manifest": str(human_manifest),
                "human_tasks": len(human),
                "total_tasks": len(synthetic) + len(human),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()