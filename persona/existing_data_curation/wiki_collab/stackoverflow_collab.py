#!/usr/bin/env python3
"""Stack Overflow posting-history helpers for the offline persona collaboration runner."""

from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from pathlib import Path
from typing import Any

from persona.existing_data_curation.wiki_collab.core import (
    canonical_json,
    compute_input_sha256,
    load_jsonl,
    sha256_file,
    write_json,
)


STACKOVERFLOW_SOURCE_TYPE = "stackoverflow_persona"
STACKOVERFLOW_PROTOCOL_ID = "stackoverflow_persona_inference_v1"


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        drop table if exists profiles;
        create table profiles (
          global_idx integer primary key,
          task_id text not null unique,
          qid text not null,
          title text not null,
          source_url text not null,
          source_type text not null,
          user_id text not null,
          profile_text text not null,
          payload_json text not null,
          source_payload_sha256 text not null
        );
        create index profiles_user_id_idx on profiles(user_id);
        """
    )


@dataclass(frozen=True)
class StackOverflowProfileRow:
    global_idx: int
    task_id: str
    qid: str
    title: str
    source_url: str
    user_id: str
    source_payload_sha256: str
    payload: dict[str, Any]


def stackoverflow_input_payload(global_idx: int, user_row: dict[str, Any]) -> dict[str, Any]:
    user_id = str(user_row.get("user_id") or "")
    return {
        "global_idx": global_idx,
        "task_id": f"{STACKOVERFLOW_SOURCE_TYPE}:{user_id}",
        "qid": f"so_user:{user_id}",
        "source_type": STACKOVERFLOW_SOURCE_TYPE,
        "user_id": user_id,
        "posts": user_row.get("posts") or [],
        "metadata": user_row.get("metadata") or {},
    }


def build_stackoverflow_profile_database(
    *,
    user_histories: Path,
    out_db: Path,
    manifest_path: Path,
    dataset_id: str,
    limit: int | None = None,
) -> dict[str, Any]:
    out_db.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if out_db.exists():
        out_db.unlink()
    conn = sqlite3.connect(out_db)
    create_schema(conn)
    row_count = 0
    source_index = 0
    for source_index, user_row in enumerate(load_jsonl(user_histories), start=1):
        if limit is not None and row_count >= limit:
            break
        payload = stackoverflow_input_payload(row_count, user_row)
        input_sha256 = compute_input_sha256(payload)
        user_id = str(payload["user_id"])
        title = (
            f"Stack Overflow user {user_id}"
            if user_id
            else f"Stack Overflow user {row_count}"
        )
        conn.execute(
            """
            insert into profiles (
              global_idx, task_id, qid, title, source_url, source_type, user_id,
              profile_text, payload_json, source_payload_sha256
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_count,
                payload["task_id"],
                payload["qid"],
                title,
                f"stackexchange://stackoverflow/user/{user_id}",
                STACKOVERFLOW_SOURCE_TYPE,
                user_id,
                _summary_text(payload),
                canonical_json(payload),
                input_sha256,
            ),
        )
        row_count += 1
    conn.commit()
    conn.close()
    manifest = {
        "dataset_id": dataset_id,
        "row_count": row_count,
        "db_file": out_db.name,
        "db_sha256": sha256_file(out_db),
        "source_type": STACKOVERFLOW_SOURCE_TYPE,
        "source_user_histories": str(user_histories),
        "source_row_count_read": source_index if row_count else 0,
        "format": "sqlite",
    }
    write_json(manifest_path, manifest)
    return manifest


def load_stackoverflow_profiles(
    db_path: Path, range_start: int, range_end: int
) -> list[StackOverflowProfileRow]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [
        _row_from_sqlite(dict(row))
        for row in conn.execute(
            """
            select global_idx, task_id, qid, title, source_url, user_id, payload_json, source_payload_sha256
            from profiles
            where global_idx >= ? and global_idx < ?
            order by global_idx
            """,
            (range_start, range_end),
        )
    ]
    conn.close()
    return rows


def _row_from_sqlite(row: dict[str, Any]) -> StackOverflowProfileRow:
    return StackOverflowProfileRow(
        global_idx=int(row["global_idx"]),
        task_id=str(row["task_id"]),
        qid=str(row["qid"]),
        title=str(row["title"]),
        source_url=str(row["source_url"]),
        user_id=str(row["user_id"]),
        source_payload_sha256=str(row["source_payload_sha256"]),
        payload=json.loads(row["payload_json"]),
    )


def _summary_text(payload: dict[str, Any]) -> str:
    post_count = len(payload.get("posts") or [])
    return (
        f"Stack Overflow posting-derived user profile for {payload.get('user_id')}; "
        f"{post_count} posts."
    )
