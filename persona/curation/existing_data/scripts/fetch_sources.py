#!/usr/bin/env python3
"""Fetch external persona datasets used for MatrAIx curation.

Default behavior is sample-first for large HuggingFace datasets. Use
`--mode full` only when you intentionally want full source artifacts under the
ignored local `raw/` tree.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_TARGET_DIR = BASE_DIR / "raw"

NEMOTRON_REPO = "nvidia/Nemotron-Personas-USA"
PERSONAHUB_REPO = "proj-persona/PersonaHub"
PANDORA_REPO = "jingjietan/pandora-big5"
SYNTHPERSONA_REPO = "SynthLabsAI/PERSONA"
PERSONACHAT_REPO = "facebook/persona-chat"
HORIZONBENCH_REPO = "stellalisy/HorizonBench"
HORIZONBENCH_CONFIG = "mental_state_graphs"
WILDCHAT_REPO = "allenai/WildChat-1M"
SYNTHETIC_PERSONA_CHAT_REPO = "google/Synthetic-Persona-Chat"

SYNTHETIC_PERSONA_CHAT_CSV_FILES = [
    "data/Synthetic-Persona-Chat_train.csv",
    "data/Synthetic-Persona-Chat_valid.csv",
    "data/Synthetic-Persona-Chat_test.csv",
    "data/New-Persona-New-Conversations.csv",
]
SYNTHETIC_PERSONA_CHAT_COLUMNS = (
    "user 1 personas",
    "user 2 personas",
    "Best Generated Conversation",
)

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

REFERENCE_SOURCE_TYPES = {
    "psychometric_reference",
    "theory_reference",
    "official_survey_reference",
    "official_population_survey_reference",
    "huggingface_dataset_reference",
    "persona_taxonomy_reference",
}

MANIFEST_REFERENCE_SOURCE_IDS = [
    "acs_pums_curated_variables",
    "attachment_style",
    "bfi2_big_five_inventory_2",
    "bis_bas_scales",
    "dospert_risk_attitudes",
    "deep_persona",
    "facet_map_70_facets",
    "grit_perseverance",
    "growth_mindset",
    "gss_cumulative_codebook",
    "hexaco_pi_r",
    "interpersonal_circumplex",
    "ipip_constructs_and_items",
    "mcadams_three_levels_personality",
    "moral_foundations_theory",
    "need_for_closure",
    "need_for_cognition",
    "primal_world_beliefs",
    "schwartz_basic_values",
    "scope_persona_salesforce",
    "self_determination_theory",
    "world_values_survey_wave7",
]


def log(message: str) -> None:
    print(f"[fetch_sources] {message}", flush=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def import_hf() -> tuple[Callable[..., Any], Callable[..., Any], Callable[..., Any]]:
    try:
        from datasets import load_dataset
        from huggingface_hub import hf_hub_download, snapshot_download
    except ImportError as err:
        raise RuntimeError(
            "Fetching HuggingFace sources requires optional data dependencies. "
            "Install the project dependencies, or install `datasets` and "
            "`huggingface_hub` directly."
        ) from err
    return load_dataset, hf_hub_download, snapshot_download


def stream_download(url: str, dest: Path, force: bool = False) -> Path:
    ensure_dir(dest.parent)
    if dest.exists() and not force:
        log(f"Skip existing file: {dest}")
        return dest

    tmp_dest = dest.with_suffix(dest.suffix + ".part")
    if tmp_dest.exists():
        tmp_dest.unlink()

    log(f"Downloading {url}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "MatrAIx-data-curation/0.1"},
    )
    try:
        with urllib.request.urlopen(request) as response, open(tmp_dest, "wb") as fh:
            shutil.copyfileobj(response, fh)
    except urllib.error.URLError as err:
        if tmp_dest.exists():
            tmp_dest.unlink()
        raise RuntimeError(f"Failed to download {url}: {err}") from err

    tmp_dest.replace(dest)
    log(f"Saved {dest}")
    return dest


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def iter_reference_manifests() -> Iterable[dict[str, Any]]:
    manifests_dir = BASE_DIR / "manifests"
    for path in sorted(manifests_dir.glob("*.json")):
        manifest = load_json(path)
        source_type = manifest.get("source", {}).get("type")
        if source_type in REFERENCE_SOURCE_TYPES:
            manifest["_manifest_path"] = str(path.relative_to(BASE_DIR))
            yield manifest


def reference_registry_row(manifest: dict[str, Any]) -> dict[str, Any]:
    source = manifest.get("source", {})
    return {
        "id": manifest.get("id"),
        "source_type": source.get("type"),
        "repo_id": source.get("repo_id"),
        "url": source.get("url"),
        "dimensions_claimed": manifest.get("dimensions_claimed"),
        "format": manifest.get("format"),
        "license": manifest.get("license"),
        "gated": manifest.get("gated", False),
        "notes": manifest.get("notes", ""),
        "manifest": manifest.get("_manifest_path"),
    }


def write_jsonl(rows: Iterable[dict[str, Any]], path: Path) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def snapshot_suffix(reference: dict[str, Any]) -> str:
    return ".pdf" if reference.get("format") == "pdf" else ".html"


def fetch_manifest_reference_source(
    source_id: str,
    args: argparse.Namespace,
    target_root: Path,
) -> None:
    """Download small reference/instrument pages declared in a manifest."""
    manifest_path = BASE_DIR / "manifests" / f"{source_id}.json"
    manifest = load_json(manifest_path)
    download_spec = manifest.get("download", {})

    references: list[dict[str, Any]] = list(download_spec.get("sample_urls", []))
    if args.mode == "full":
        references.extend(download_spec.get("full_urls", []))

    if not references:
        url = manifest.get("source", {}).get("url")
        if not url:
            raise RuntimeError(f"No download URLs found for {source_id}.")
        references = [{"id": "source_url", "url": url, "format": "html"}]

    out_dir = target_root / source_id
    ensure_dir(out_dir)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    index: list[dict[str, Any]] = []
    for reference in references:
        ref_id = reference.get("id")
        url = reference.get("url")
        if not ref_id or not url:
            raise RuntimeError(f"Invalid download reference in {manifest_path}: {reference}")

        dest = out_dir / f"{ref_id}{snapshot_suffix(reference)}"
        row = {
            "id": ref_id,
            "url": url,
            "path": str(dest.relative_to(target_root)),
            "status": "pending",
            "notes": reference.get("notes", ""),
        }
        try:
            stream_download(url, dest, force=args.force)
            row["status"] = "downloaded"
        except RuntimeError as exc:
            row["status"] = "failed"
            row["error"] = str(exc)
            log(f"WARNING: could not download {source_id}/{ref_id}: {exc}")
        index.append(row)

    (out_dir / "download_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    downloaded = sum(1 for row in index if row["status"] == "downloaded")
    log(f"Saved {downloaded}/{len(index)} reference snapshots for {source_id}")


def save_jsonl_sample(
    repo_id: str,
    output_path: Path,
    sample_rows: int,
    token: str | None = None,
    config_name: str | None = None,
) -> Path:
    load_dataset, _hf_hub_download, _snapshot_download = import_hf()
    ensure_dir(output_path.parent)
    if output_path.exists():
        output_path.unlink()

    kwargs: dict[str, Any] = {"split": "train", "streaming": True}
    if token:
        kwargs["token"] = token
    dataset_iterable = (
        load_dataset(repo_id, config_name, **kwargs)
        if config_name
        else load_dataset(repo_id, **kwargs)
    )

    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for row in dataset_iterable:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
            if count >= sample_rows:
                break
    log(f"Saved {count} sampled rows to {output_path}")
    return output_path


def fetch_nemotron(args: argparse.Namespace, target_root: Path) -> None:
    _load_dataset, _hf_hub_download, snapshot_download = import_hf()
    out_dir = target_root / "nemotron_personas_usa"
    ensure_dir(out_dir)
    if args.mode == "full":
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
    save_jsonl_sample(NEMOTRON_REPO, out_dir / f"nemotron_sample_{args.sample_rows}.jsonl", args.sample_rows, args.hf_token)


def resolve_personahub_elite_patterns(part: str) -> list[str]:
    if part == "all":
        return ["README.md", "ElitePersonas/elite_personas.part*.jsonl"]
    if not part.isdigit():
        raise ValueError("elite part must be an integer string or 'all'")
    idx = int(part)
    if idx < 1 or idx > 19:
        raise ValueError("elite part must be in [1, 19] or 'all'")
    return [f"ElitePersonas/elite_personas.part{idx}.jsonl", "README.md"]


def fetch_personahub(args: argparse.Namespace, target_root: Path) -> None:
    _load_dataset, hf_hub_download, snapshot_download = import_hf()
    out_dir = target_root / "tencent_personahub"
    ensure_dir(out_dir)
    if args.mode == "full":
        config = args.personahub_config
        if config == "elite_persona":
            if not args.personahub_elite_part:
                raise RuntimeError(
                    "--personahub-elite-part is required for full elite_persona download."
                )
            snapshot_download(
                repo_id=PERSONAHUB_REPO,
                repo_type="dataset",
                local_dir=str(out_dir),
                allow_patterns=resolve_personahub_elite_patterns(args.personahub_elite_part),
                token=args.hf_token,
                resume_download=True,
                max_workers=args.max_workers,
            )
            return
        hf_hub_download(
            repo_id=PERSONAHUB_REPO,
            repo_type="dataset",
            filename=PERSONAHUB_SMALL_FILES[config],
            local_dir=str(out_dir),
            token=args.hf_token,
            resume_download=True,
            force_download=args.force,
        )
        return
    save_jsonl_sample(
        PERSONAHUB_REPO,
        out_dir / f"personahub_{args.personahub_config}_sample_{args.sample_rows}.jsonl",
        args.sample_rows,
        args.hf_token,
        args.personahub_config,
    )


def fetch_oasis(args: argparse.Namespace, target_root: Path) -> None:
    stream_download(OASIS_URL, target_root / "oasis" / "user_data_36.json", args.force)


def fetch_ml_primex(args: argparse.Namespace, target_root: Path) -> None:
    stream_download(PRIMEX_URL, target_root / "apple_ml_primex" / "primexdata.csv", args.force)


def check_synthetic_persona_chat_columns(columns: tuple[str, ...]) -> None:
    if columns != SYNTHETIC_PERSONA_CHAT_COLUMNS:
        raise RuntimeError(
            "Synthetic-Persona-Chat column mismatch: "
            f"expected {SYNTHETIC_PERSONA_CHAT_COLUMNS}, got {columns}"
        )


def fetch_synthetic_persona_chat(args: argparse.Namespace, target_root: Path) -> None:
    _load_dataset, _hf_hub_download, snapshot_download = import_hf()
    out_dir = target_root / "google_synthetic_persona_chat"
    ensure_dir(out_dir)
    if args.mode == "full":
        snapshot_download(
            repo_id=SYNTHETIC_PERSONA_CHAT_REPO,
            repo_type="dataset",
            local_dir=str(out_dir),
            allow_patterns=["README.md", *SYNTHETIC_PERSONA_CHAT_CSV_FILES],
            token=args.hf_token,
            resume_download=True,
            max_workers=args.max_workers,
        )
        for relative_path in SYNTHETIC_PERSONA_CHAT_CSV_FILES:
            csv_path = out_dir / relative_path
            if not csv_path.exists():
                raise RuntimeError(f"Missing expected file: {csv_path}")
            with csv_path.open(newline="", encoding="utf-8") as handle:
                columns = tuple(csv.DictReader(handle).fieldnames or ())
            check_synthetic_persona_chat_columns(columns)
        return
    save_jsonl_sample(
        SYNTHETIC_PERSONA_CHAT_REPO,
        out_dir / f"synthetic_persona_chat_sample_{args.sample_rows}.jsonl",
        args.sample_rows,
        args.hf_token,
    )


def fetch_pandora(args: argparse.Namespace, target_root: Path) -> None:
    _load_dataset, _hf_hub_download, snapshot_download = import_hf()
    out_dir = target_root / "pandora_big5"
    ensure_dir(out_dir)
    if args.mode == "full":
        snapshot_download(
            repo_id=PANDORA_REPO,
            repo_type="dataset",
            local_dir=str(out_dir),
            allow_patterns=["README.md", "data/*.parquet"],
            token=args.hf_token,
            resume_download=True,
            max_workers=args.max_workers,
        )
        return
    save_jsonl_sample(PANDORA_REPO, out_dir / f"pandora_big5_sample_{args.sample_rows}.jsonl", args.sample_rows, args.hf_token)


def fetch_synthpersona(args: argparse.Namespace, target_root: Path) -> None:
    _load_dataset, _hf_hub_download, snapshot_download = import_hf()
    if not args.hf_token:
        log("WARNING: SynthLabsAI/PERSONA is gated; set HF_TOKEN after accepting terms.")
    out_dir = target_root / "synthlabs_persona"
    ensure_dir(out_dir)
    if args.mode == "full":
        snapshot_download(
            repo_id=SYNTHPERSONA_REPO,
            repo_type="dataset",
            local_dir=str(out_dir),
            allow_patterns=["README.md", "data/*.parquet"],
            token=args.hf_token,
            resume_download=True,
            max_workers=args.max_workers,
        )
        return
    save_jsonl_sample(SYNTHPERSONA_REPO, out_dir / f"synthlabs_persona_sample_{args.sample_rows}.jsonl", args.sample_rows, args.hf_token)


def fetch_personachat(args: argparse.Namespace, target_root: Path) -> None:
    _load_dataset, _hf_hub_download, snapshot_download = import_hf()
    out_dir = target_root / "personachat_facebook"
    ensure_dir(out_dir)
    if args.mode == "full":
        snapshot_download(
            repo_id=PERSONACHAT_REPO,
            repo_type="dataset",
            local_dir=str(out_dir),
            allow_patterns=["README.md", "data/*.parquet"],
            token=args.hf_token,
            resume_download=True,
            max_workers=args.max_workers,
        )
        return
    save_jsonl_sample(PERSONACHAT_REPO, out_dir / f"personachat_facebook_sample_{args.sample_rows}.jsonl", args.sample_rows, args.hf_token)


def fetch_horizonbench(args: argparse.Namespace, target_root: Path) -> None:
    _load_dataset, _hf_hub_download, snapshot_download = import_hf()
    out_dir = target_root / "horizonbench_mental_state_graphs"
    ensure_dir(out_dir)
    if args.mode == "full":
        snapshot_download(
            repo_id=HORIZONBENCH_REPO,
            repo_type="dataset",
            local_dir=str(out_dir),
            allow_patterns=["README.md", "data/*.parquet"],
            token=args.hf_token,
            resume_download=True,
            max_workers=args.max_workers,
        )
        return
    save_jsonl_sample(
        HORIZONBENCH_REPO,
        out_dir / f"horizonbench_mental_state_graphs_sample_{args.sample_rows}.jsonl",
        args.sample_rows,
        args.hf_token,
        HORIZONBENCH_CONFIG,
    )


def fetch_wildchat(args: argparse.Namespace, target_root: Path) -> None:
    _load_dataset, _hf_hub_download, snapshot_download = import_hf()
    out_dir = target_root / "wildchat_allenai"
    ensure_dir(out_dir)
    if args.mode == "full":
        snapshot_download(
            repo_id=WILDCHAT_REPO,
            repo_type="dataset",
            local_dir=str(out_dir),
            allow_patterns=["README.md", "data/*.parquet"],
            token=args.hf_token,
            resume_download=True,
            max_workers=args.max_workers,
        )
        return
    save_jsonl_sample(WILDCHAT_REPO, out_dir / f"wildchat_allenai_sample_{args.sample_rows}.jsonl", args.sample_rows, args.hf_token)


def fetch_literature_references(args: argparse.Namespace, target_root: Path) -> None:
    """Create a registry for reference-only theory, scale, and survey sources."""
    out_dir = target_root / "literature_references"
    ensure_dir(out_dir)
    registry = [reference_registry_row(manifest) for manifest in iter_reference_manifests()]
    if not registry:
        raise RuntimeError("No reference manifests found.")

    (out_dir / "reference_registry.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_jsonl(registry, out_dir / "reference_registry.jsonl")
    log(f"Saved {len(registry)} reference manifest rows to {out_dir}")

    if args.mode != "full":
        return
    snapshot_dir = out_dir / "source_snapshots"
    for row in registry:
        url = row.get("url")
        source_id = row.get("id")
        if url and source_id:
            dest = snapshot_dir / str(source_id) / "source_snapshot.html"
            try:
                stream_download(url, dest, force=args.force)
            except RuntimeError as exc:
                log(f"WARNING: could not snapshot {source_id}: {exc}")


def source_to_runner() -> dict[str, Callable[[argparse.Namespace, Path], None]]:
    runners: dict[str, Callable[[argparse.Namespace, Path], None]] = {
        "nemotron": fetch_nemotron,
        "personahub": fetch_personahub,
        "oasis": fetch_oasis,
        "ml_primex": fetch_ml_primex,
        "synthetic_persona_chat": fetch_synthetic_persona_chat,
        "pandora": fetch_pandora,
        "synthpersona": fetch_synthpersona,
        "personachat": fetch_personachat,
        "horizonbench": fetch_horizonbench,
        "wildchat": fetch_wildchat,
        "literature_references": fetch_literature_references,
        "nemotron_personas_usa": fetch_nemotron,
        "tencent_personahub": fetch_personahub,
        "oasis_reddit_36d": fetch_oasis,
        "apple_ml_primex": fetch_ml_primex,
        "google_synthetic_persona_chat": fetch_synthetic_persona_chat,
        "pandora_big5": fetch_pandora,
        "synthlabs_persona": fetch_synthpersona,
        "personachat_facebook": fetch_personachat,
        "horizonbench_mental_state_graphs": fetch_horizonbench,
        "wildchat_allenai": fetch_wildchat,
    }
    for source_id in MANIFEST_REFERENCE_SOURCE_IDS:
        runners[source_id] = (
            lambda parsed_args, target_root, source_id=source_id: fetch_manifest_reference_source(
                source_id,
                parsed_args,
                target_root,
            )
        )
    return runners


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    sources = ["all", *sorted(source_to_runner())]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=sources, default="all")
    parser.add_argument("--mode", choices=["sample", "full"], default="sample")
    parser.add_argument("--sample-rows", type=int, default=1000)
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
    )
    parser.add_argument("--personahub-elite-part", default=None)
    parser.add_argument("--target-dir", type=Path, default=DEFAULT_TARGET_DIR)
    parser.add_argument("--hf-token", default=os.getenv("HF_TOKEN"))
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(list(argv) if argv is not None else None)


def selected_sources(source: str) -> list[str]:
    if source != "all":
        return [source]
    return [
        "nemotron",
        "personahub",
        "oasis",
        "ml_primex",
        "synthetic_persona_chat",
        "pandora",
        "personachat",
        "horizonbench",
        "wildchat",
        "literature_references",
    ]


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_dir(args.target_dir)
    runners = source_to_runner()
    for source_name in selected_sources(args.source):
        log(f"Starting source: {source_name}")
        runners[source_name](args, args.target_dir)
        log(f"Finished source: {source_name}")
    log("All requested sources completed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise
