# run.py — CLI entry point for generating OASIS simulation datasets.
# Generates profiles (Twitter or Reddit style), builds the follow network,
# and exports to OASIS-compatible CSV/JSON format.
#
# Usage:
#   python -m environments.oasis.data.generators.run twitter --n 100 --output data/generated
#   python -m environments.oasis.data.generators.run reddit --n 50 --output data/generated

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from environments.oasis.data.generators.twitter_profiles import generate_twitter_profiles
from environments.oasis.data.generators.reddit_profiles import generate_reddit_profiles
from environments.oasis.data.generators.network import generate_topic_network, generate_random_network
from environments.oasis.data.generators.export import export_twitter_csv, export_reddit_json


def run_twitter(args):
    print(f"Generating {args.n} Twitter profiles via {args.model}...")
    start = time.time()

    profiles = generate_twitter_profiles(
        n=args.n,
        llm_base_url=args.llm_url,
        llm_api_key=args.llm_key,
        llm_model=args.model,
        max_workers=args.workers,
        seed=args.seed,
    )
    print(f"  Generated {len(profiles)} profiles in {time.time()-start:.1f}s")

    print(f"Building follow network (mode={args.network})...")
    if args.network == "topic":
        following_lists = generate_topic_network(profiles, follow_probability=0.2, seed=args.seed)
    else:
        following_lists = generate_random_network(len(profiles), num_edges=len(profiles) * 7, seed=args.seed)

    total_edges = sum(len(f) for f in following_lists)
    print(f"  Network: {total_edges} edges")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = export_twitter_csv(profiles, following_lists, output_dir / "agents.csv")
    print(f"  CSV: {csv_path}")

    json_path = output_dir / "profiles.json"
    with open(json_path, "w") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
    print(f"  JSON: {json_path}")

    meta = {
        "platform": "twitter",
        "num_profiles": len(profiles),
        "num_edges": total_edges,
        "network_mode": args.network,
        "model": args.model,
        "seed": args.seed,
    }
    with open(output_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Done. Output in {output_dir}")


def run_reddit(args):
    print(f"Generating {args.n} Reddit profiles via {args.model}...")
    start = time.time()

    profiles = generate_reddit_profiles(
        n=args.n,
        llm_base_url=args.llm_url,
        llm_api_key=args.llm_key,
        llm_model=args.model,
        max_workers=args.workers,
        seed=args.seed,
    )
    print(f"  Generated {len(profiles)} profiles in {time.time()-start:.1f}s")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = export_reddit_json(profiles, output_dir / "reddit_users.json")
    print(f"  JSON: {json_path}")

    meta = {
        "platform": "reddit",
        "num_profiles": len(profiles),
        "model": args.model,
        "seed": args.seed,
    }
    with open(output_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Done. Output in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Generate OASIS simulation datasets")
    subparsers = parser.add_subparsers(dest="platform", required=True)

    twitter_parser = subparsers.add_parser("twitter", help="Generate Twitter-style profiles")
    twitter_parser.add_argument("--n", type=int, default=100, help="Number of profiles")
    twitter_parser.add_argument("--output", default="environments/oasis/data/generated/twitter", help="Output directory")
    twitter_parser.add_argument("--llm-url", default="http://localhost:8002/v1", help="LLM API base URL")
    twitter_parser.add_argument("--llm-key", default="no-key", help="LLM API key")
    twitter_parser.add_argument("--model", default="Qwen/Qwen3-4B", help="LLM model name")
    twitter_parser.add_argument("--workers", type=int, default=10, help="Parallel workers")
    twitter_parser.add_argument("--network", choices=["topic", "random"], default="topic", help="Network type")
    twitter_parser.add_argument("--seed", type=int, default=42, help="Random seed")

    reddit_parser = subparsers.add_parser("reddit", help="Generate Reddit-style profiles")
    reddit_parser.add_argument("--n", type=int, default=50, help="Number of profiles")
    reddit_parser.add_argument("--output", default="environments/oasis/data/generated/reddit", help="Output directory")
    reddit_parser.add_argument("--llm-url", default="http://localhost:8002/v1", help="LLM API base URL")
    reddit_parser.add_argument("--llm-key", default="no-key", help="LLM API key")
    reddit_parser.add_argument("--model", default="Qwen/Qwen3-4B", help="LLM model name")
    reddit_parser.add_argument("--workers", type=int, default=10, help="Parallel workers")
    reddit_parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()
    if args.platform == "twitter":
        run_twitter(args)
    elif args.platform == "reddit":
        run_reddit(args)


if __name__ == "__main__":
    main()
