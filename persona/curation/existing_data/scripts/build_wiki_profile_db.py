#!/usr/bin/env python3
"""Build a canonical SQLite profile database for offline wiki collaboration."""

from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from persona.curation.existing_data.wiki_collab.core import (
    canonical_json,
    compute_input_sha256,
    profile_input_payload,
    sha256_file,
    write_json,
)


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc


def clean_page_files(clean_dir: Path) -> list[Path]:
    if clean_dir.is_file():
        return [clean_dir]
    files = sorted(
        path
        for path in clean_dir.rglob("*")
        if path.name.endswith(".jsonl") or path.name.endswith(".jsonl.gz")
    )
    if not files:
        raise FileNotFoundError(f"no JSONL files found under {clean_dir}")
    return files


def profile_text_from_row(row: dict[str, Any], max_chars: int | None = None) -> str:
    text = row.get("profile_text") or row.get("plain_text") or row.get("text") or ""
    text = str(text).strip()
    if max_chars and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        drop table if exists profiles;
        create table profiles (
          global_idx integer primary key,
          task_id text not null unique,
          page_id integer not null,
          qid text not null,
          title text not null,
          source_url text not null,
          profile_text text not null,
          input_sha256 text not null,
          source_file text not null,
          source_row integer not null
        );
        create index profiles_qid_idx on profiles(qid);
        create index profiles_title_idx on profiles(title);
        """
    )


def build_profile_database(
    *,
    clean_dir: Path,
    out_db: Path,
    manifest_path: Path,
    dataset_id: str,
    max_chars: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    out_db.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if out_db.exists():
        out_db.unlink()
    conn = sqlite3.connect(out_db)
    create_schema(conn)
    global_idx = 0
    for source_file in clean_page_files(clean_dir):
        shard_rows: list[tuple[int, dict[str, Any]]] = []
        for source_row, row in enumerate(iter_jsonl(source_file), 1):
            shard_rows.append((source_row, row))
        shard_rows.sort(key=lambda item: int(item[1].get("page_id") or 0))
        for source_row, row in shard_rows:
            if limit is not None and global_idx >= limit:
                break
            page_id = int(row["page_id"])
            qid = str(row.get("qid") or "")
            title = str(row.get("title") or "")
            source_url = str(row.get("source_url") or "")
            profile_text = profile_text_from_row(row, max_chars=max_chars)
            task_id = f"wiki_profile:{global_idx:010d}"
            payload = profile_input_payload(
                {
                    "global_idx": global_idx,
                    "task_id": task_id,
                    "qid": qid,
                    "title": title,
                    "source_url": source_url,
                    "profile_text": profile_text,
                }
            )
            input_sha256 = compute_input_sha256(payload)
            conn.execute(
                """
                insert into profiles (
                  global_idx, task_id, page_id, qid, title, source_url,
                  profile_text, input_sha256, source_file, source_row
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    global_idx,
                    task_id,
                    page_id,
                    qid,
                    title,
                    source_url,
                    profile_text,
                    input_sha256,
                    source_file.name,
                    source_row,
                ),
            )
            global_idx += 1
        if limit is not None and global_idx >= limit:
            break
    conn.commit()
    conn.close()
    db_sha256 = sha256_file(out_db)
    manifest = {
        "dataset_id": dataset_id,
        "row_count": global_idx,
        "db_file": out_db.name,
        "db_sha256": db_sha256,
        "source_dir": str(clean_dir),
        "index_rule": "files sorted by path; rows sorted by page_id within each source file",
        "profile_text_max_chars": max_chars,
        "format": "sqlite",
    }
    write_json(manifest_path, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-dir", type=Path, required=True)
    parser.add_argument("--out-db", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--max-chars", type=int)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_profile_database(
        clean_dir=args.clean_dir,
        out_db=args.out_db,
        manifest_path=args.manifest,
        dataset_id=args.dataset_id,
        max_chars=args.max_chars,
        limit=args.limit,
    )
    print(canonical_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

