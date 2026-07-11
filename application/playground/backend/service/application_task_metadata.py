"""Read Harbor-standard task metadata from ``application/tasks/*/task.toml``."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from backend.service.application_types import normalize_metadata_type
from backend.service.playground_task_registry import (
    PlaygroundTaskEntry,
    get_playground_entry,
    resolve_task_kind,
)


@dataclass(frozen=True)
class ApplicationTaskRecord:
    folder_name: str
    task_path: str
    task_name: str
    title: str
    description: str
    meta_type: str
    os: str
    domain: str
    difficulty: str
    tags: List[str] = field(default_factory=list)
    playground: PlaygroundTaskEntry | None = None
    task_kind: str = "task"


def _as_str_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def parse_task_toml(task_dir: Path) -> Dict[str, object]:
    toml_path = task_dir / "task.toml"
    if not toml_path.is_file():
        return {}
    return tomllib.loads(toml_path.read_text(encoding="utf-8"))


def read_instruction_meta(instruction_path: Path) -> tuple[str, str]:
    if not instruction_path.is_file():
        return "", ""
    title = ""
    description = ""
    for line in instruction_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not title:
            title = stripped.lstrip("# ").strip()
            continue
        if title and not description and stripped and not stripped.startswith("#"):
            description = stripped
            break
    return title, description


def humanize_folder(folder_name: str) -> str:
    import re

    stem = folder_name
    for prefix in ("example-survey_", "survey_", "example-"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    stem = re.sub(r"^(web|computer-use)-", "", stem)
    stem = stem.replace("_", " ").replace("-", " ")
    return stem.strip().title() or folder_name


def slug_from_harbor_task_name(task_name: str) -> str:
    """Return the slug portion of ``[task].name``."""
    raw = task_name.strip()
    if not raw:
        return ""
    lowered = raw.lower()
    if lowered.startswith("application/"):
        return raw.split("/", 1)[1]
    legacy = "personabench/application-"
    if lowered.startswith(legacy):
        return raw[len(legacy) :]
    if "/" in raw:
        return raw.rsplit("/", 1)[-1]
    return raw


def title_from_harbor_task_name(task_name: str) -> str:
    """Derive UI title from ``[task].name`` (``application/<slug>``)."""
    slug = slug_from_harbor_task_name(task_name)
    words = [word for word in slug.replace("_", "-").split("-") if word]
    if not words:
        return ""
    return " ".join(word.capitalize() for word in words)


def parse_application_task(task_dir: Path) -> ApplicationTaskRecord | None:
    raw = parse_task_toml(task_dir)
    if not raw:
        return None

    folder_name = task_dir.name
    playground = get_playground_entry(folder_name)
    if playground is None:
        return None

    meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    meta_type = normalize_metadata_type(str(meta.get("type") or ""))
    os = str(meta.get("os") or "").strip().lower()
    domain = str(meta.get("domain") or "").strip()
    difficulty = str(meta.get("difficulty") or "easy").strip()
    tags = _as_str_list(meta.get("tags"))

    task_block = raw.get("task") if isinstance(raw.get("task"), dict) else {}
    task_name = str(task_block.get("name") or "").strip() or f"application/{folder_name.replace('_', '-')}"
    _, instruction_description = read_instruction_meta(task_dir / "instruction.md")
    # Display title always comes from ``[task].name``, not instruction H1.
    title = title_from_harbor_task_name(task_name) or humanize_folder(folder_name)
    description = instruction_description or f"Harbor task ({folder_name})."

    return ApplicationTaskRecord(
        folder_name=folder_name,
        task_path="application/tasks/{}".format(folder_name),
        task_name=task_name,
        title=title,
        description=description,
        meta_type=meta_type,
        os=os,
        domain=domain,
        difficulty=difficulty,
        tags=tags,
        playground=playground,
        task_kind=resolve_task_kind(folder_name, playground),
    )
