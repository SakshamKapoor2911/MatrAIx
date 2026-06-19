#!/usr/bin/env python3
"""Fetch external persona datasets used for MatrAIx curation.

Default behavior is sample-first for large Hugging Face datasets.
Use --mode full for full artifact download.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from datasets import load_dataset
from huggingface_hub import hf_hub_download, snapshot_download


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_TARGET_DIR = BASE_DIR / "raw"

NEMOTRON_REPO = "nvidia/Nemotron-Personas-USA"
PERSONAHUB_REPO = "proj-persona/PersonaHub"

PERSONAHUB_SMALL_FILES = {
    "math": "math.jsonl",
    "instruction": "instruction.jsonl",
    "reasoning": "reasoning.jsonl",
    "knowledge": "knowledge.jsonl",
    "npc": "npc.jsonl",
    "tool": "tool.jsonl",
    "persona": "persona.jsonl",
}

OASIS_URL = "https://raw.githubusercontent.com/camel-ai/oasis/main/data/reddit/user_data_36.json"
PRIMEX_URL = "https://raw.githubusercontent.com/apple/ml-primex/main/primexdata.csv"


def log(message: str) -> None:
    print(f"[fetch_sources] {message}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def stream_download(url: str, dest: Path, force: bool = False) -> Path:
    ensure_dir(dest.parent)
    if dest.exists() and not force:
        log(f"Skip existing file: {dest}")
        return dest

    tmp_dest = dest.with_suffix(dest.suffix + ".part")
    if tmp_dest.exists():
        tmp_dest.unlink()

    log(f"Downloading {url}")
    try:
        with urllib.request.urlopen(url) as response, open(tmp_dest, "wb") as fh:
            shutil.copyfileobj(response, fh)
    except urllib.error.URLError as err:
        if tmp_dest.exists():
            tmp_dest.unlink()
        raise RuntimeError(f"Failed to download {url}: {err}") from err

    tmp_dest.replace(dest)
    log(f"Saved {dest}")
    return dest


def save_jsonl_sample(
    repo_id: str,
    output_path: Path,
    sample_rows: int,
    token: str | None = None,
    config_name: str | None = None,
) -> Path:
    ensure_dir(output_path.parent)
    if output_path.exists():
        output_path.unlink()

    kwargs: dict[str, Any] = {"split": "train", "streaming": True}
    if token:
        kwargs["token"] = token

    if config_name:
        dataset_iterable = load_dataset(repo_id, config_name, **kwargs)
    else:
        dataset_iterable = load_dataset(repo_id, **kwargs)

    count = 0
    with open(output_path, "w", encoding="utf-8") as fh:
        for row in dataset_iterable:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
            if count >= sample_rows:
                break

    log(f"Saved {count} sampled rows to {output_path}")
    return output_path


def fetch_nemotron(args: argparse.Namespace, target_root: Path) -> None:
    out_dir = target_root / "nemotron_personas_usa"
    ensure_dir(out_dir)

    if args.mode == "full":
        log("Fetching full Nemotron Persona dataset (all parquet shards).")
        snapshot_download(
            repo_id=NEMOTRON_REPO,
            repo_type="dataset",
            local_dir=str(out_dir),
            allow_patterns=["README.md", "data/*.parquet"],
            token=args.hf_token,
            resume_download=True,
            max_workers=args.max_workers,
        )
        return

    sample_out = out_dir / f"nemotron_sample_{args.sample_rows}.jsonl"
    save_jsonl_sample(
        repo_id=NEMOTRON_REPO,
        output_path=sample_out,
        sample_rows=args.sample_rows,
        token=args.hf_token,
        config_name=None,
    )


def _resolve_personahub_elite_patterns(part: str) -> list[str]:
    if part == "all":
        return ["README.md", "ElitePersonas/elite_personas.part*.jsonl"]

    if not part.isdigit():
        raise ValueError("elite part must be an integer string or 'all'")

    idx = int(part)
    if idx < 1 or idx > 19:
        raise ValueError("elite part must be in [1, 19] or 'all'")
    return [f"ElitePersonas/elite_personas.part{idx}.jsonl", "README.md"]


def fetch_personahub(args: argparse.Namespace, target_root: Path) -> None:
    out_dir = target_root / "tencent_personahub"
    ensure_dir(out_dir)

    if args.mode == "full":
        config = args.personahub_config
        if config == "elite_persona":
            if not args.personahub_elite_part:
                raise RuntimeError(
                    "--personahub-elite-part is required for full elite_persona download "
                    "(use 1..19 or 'all')."
                )
            allow_patterns = _resolve_personahub_elite_patterns(args.personahub_elite_part)
            log(
                "Fetching PersonaHub elite file(s): "
                + ", ".join(pattern for pattern in allow_patterns if pattern.endswith(".jsonl"))
            )
            snapshot_download(
                repo_id=PERSONAHUB_REPO,
                repo_type="dataset",
                local_dir=str(out_dir),
                allow_patterns=allow_patterns,
                token=args.hf_token,
                resume_download=True,
                max_workers=args.max_workers,
            )
            return

        filename = PERSONAHUB_SMALL_FILES[config]
        log(f"Fetching PersonaHub file: {filename}")
        hf_hub_download(
            repo_id=PERSONAHUB_REPO,
            repo_type="dataset",
            filename=filename,
            local_dir=str(out_dir),
            token=args.hf_token,
            resume_download=True,
            force_download=args.force,
        )
        return

    sample_out = out_dir / f"personahub_{args.personahub_config}_sample_{args.sample_rows}.jsonl"
    save_jsonl_sample(
        repo_id=PERSONAHUB_REPO,
        config_name=args.personahub_config,
        output_path=sample_out,
        sample_rows=args.sample_rows,
        token=args.hf_token,
    )


def fetch_oasis(_: argparse.Namespace, target_root: Path) -> None:
    out_path = target_root / "oasis" / "user_data_36.json"
    stream_download(OASIS_URL, out_path)


def fetch_ml_primex(_: argparse.Namespace, target_root: Path) -> None:
    out_path = target_root / "apple_ml_primex" / "primexdata.csv"
    stream_download(PRIMEX_URL, out_path)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=["all", "nemotron", "personahub", "oasis", "ml_primex"],
        default="all",
        help="Which source to fetch.",
    )
    parser.add_argument(
        "--mode",
        choices=["sample", "full"],
        default="sample",
        help="Sample mode for safer curation, full mode for full artifacts.",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=1000,
        help="Rows to keep when mode=sample for Hugging Face datasets.",
    )
    parser.add_argument(
        "--personahub-config",
        choices=[
            "math",
            "instruction",
            "reasoning",
            "knowledge",
            "npc",
            "tool",
            "persona",
            "elite_persona",
        ],
        default="elite_persona",
        help="PersonaHub config used in sample mode, or in full mode for non-elite files.",
    )
    parser.add_argument(
        "--personahub-elite-part",
        default=None,
        help="For full elite_persona download only: 1..19 or 'all'.",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=DEFAULT_TARGET_DIR,
        help=f"Output directory (default: {DEFAULT_TARGET_DIR}).",
    )
    parser.add_argument(
        "--hf-token",
        default=os.getenv("HF_TOKEN"),
        help="Hugging Face token. Defaults to environment variable HF_TOKEN.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Parallel workers for Hugging Face snapshot download.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download where supported.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    ensure_dir(args.target_dir)

    source_to_runner = {
        "nemotron": fetch_nemotron,
        "personahub": fetch_personahub,
        "oasis": fetch_oasis,
        "ml_primex": fetch_ml_primex,
    }

    selected_sources = (
        ["nemotron", "personahub", "oasis", "ml_primex"]
        if args.source == "all"
        else [args.source]
    )

    for source_name in selected_sources:
        log(f"Starting source: {source_name}")
        source_to_runner[source_name](args, args.target_dir)
        log(f"Finished source: {source_name}")

    log("All requested sources completed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise
