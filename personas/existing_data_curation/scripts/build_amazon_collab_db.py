#!/usr/bin/env python3
"""Build a canonical SQLite user database for Amazon review collaboration runs."""

from __future__ import annotations

import argparse

from personas.existing_data_curation.wiki_collab.amazon_collab import (
    build_amazon_profile_database,
)
from personas.existing_data_curation.wiki_collab.core import canonical_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-histories", required=True, type=str)
    parser.add_argument("--out-db", required=True, type=str)
    parser.add_argument("--manifest", required=True, type=str)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--product-metadata-sidecar", type=str)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> int:
    from pathlib import Path

    args = parse_args()
    manifest = build_amazon_profile_database(
        user_histories=Path(args.user_histories),
        out_db=Path(args.out_db),
        manifest_path=Path(args.manifest),
        dataset_id=args.dataset_id,
        product_metadata_sidecar=Path(args.product_metadata_sidecar)
        if args.product_metadata_sidecar
        else None,
        limit=args.limit,
    )
    print(canonical_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
