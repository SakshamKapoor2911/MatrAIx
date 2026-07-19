#!/usr/bin/env python3
"""Shared primitives for offline wiki extraction collaboration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterator


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> Iterator[dict[str, Any]]:
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


def parse_range(raw: str) -> tuple[int, int]:
    try:
        start_s, end_s = raw.split(":", 1)
        start = int(start_s)
        end = int(end_s)
    except Exception as exc:
        raise ValueError(f"range must be START:END, got {raw!r}") from exc
    if start < 0 or end <= start:
        raise ValueError(f"range must satisfy 0 <= start < end, got {raw!r}")
    return start, end


def safe_name(value: str) -> str:
    cleaned = SAFE_NAME_RE.sub("_", value.strip())
    return cleaned.strip("_") or "unknown"


def build_result_archive_name(
    worker_id: str, protocol_id: str, range_start: int, range_end: int
) -> str:
    return (
        f"results_{safe_name(worker_id)}_{safe_name(protocol_id)}_"
        f"{range_start:010d}_{range_end:010d}.tar.gz"
    )


@dataclass(frozen=True)
class Assignment:
    assignment_id: str
    worker_id: str
    dataset_id: str
    dataset_sha256: str
    protocol_id: str
    protocol_sha256: str
    range_start: int
    range_end: int
    status: str = "assigned"

    @property
    def count(self) -> int:
        return self.range_end - self.range_start

    def contains(self, global_idx: int) -> bool:
        return self.range_start <= global_idx < self.range_end

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Assignment":
        return cls(
            assignment_id=str(data["assignment_id"]),
            worker_id=str(data["worker_id"]),
            dataset_id=str(data["dataset_id"]),
            dataset_sha256=str(data["dataset_sha256"]),
            protocol_id=str(data["protocol_id"]),
            protocol_sha256=str(data["protocol_sha256"]),
            range_start=int(data["range_start"]),
            range_end=int(data["range_end"]),
            status=str(data.get("status", "assigned")),
        )


@dataclass(frozen=True)
class ProtocolManifest:
    protocol_id: str
    protocol_version: str
    prompt_file: str
    output_schema_file: str
    input_schema_file: str | None
    prompt_sha256: str
    output_schema_sha256: str
    input_schema_sha256: str | None
    protocol_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_protocol_manifest(protocol_dir: Path) -> ProtocolManifest:
    manifest_path = protocol_dir / "protocol_manifest.json"
    raw = load_json(manifest_path)
    prompt_file = str(raw.get("prompt_file", "prompt.md"))
    output_schema_file = str(raw.get("output_schema_file", "output.schema.json"))
    input_schema_file = raw.get("input_schema_file")
    prompt_text = (protocol_dir / prompt_file).read_text(encoding="utf-8")
    output_schema_text = (protocol_dir / output_schema_file).read_text(encoding="utf-8")
    input_schema_sha256 = None
    if input_schema_file:
        input_schema_sha256 = sha256_text(
            (protocol_dir / str(input_schema_file)).read_text(encoding="utf-8")
        )
    payload = {
        "protocol_id": raw["protocol_id"],
        "protocol_version": raw["protocol_version"],
        "prompt_sha256": sha256_text(prompt_text),
        "output_schema_sha256": sha256_text(output_schema_text),
        "input_schema_sha256": input_schema_sha256,
    }
    return ProtocolManifest(
        protocol_id=str(raw["protocol_id"]),
        protocol_version=str(raw["protocol_version"]),
        prompt_file=prompt_file,
        output_schema_file=output_schema_file,
        input_schema_file=str(input_schema_file) if input_schema_file else None,
        prompt_sha256=payload["prompt_sha256"],
        output_schema_sha256=payload["output_schema_sha256"],
        input_schema_sha256=input_schema_sha256,
        protocol_sha256=sha256_text(canonical_json(payload)),
    )


def profile_input_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "global_idx": int(row["global_idx"]),
        "task_id": row["task_id"],
        "qid": row["qid"],
        "title": row["title"],
        "source_url": row["source_url"],
        "profile_text": row["profile_text"],
    }


def compute_input_sha256(payload: dict[str, Any]) -> str:
    return sha256_text(canonical_json(payload))

