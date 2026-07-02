"""Read Harbor task docs for cockpit detail panels."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def _humanize_key(value: str) -> str:
    text = str(value).replace("_", " ").strip()
    if not text:
        return text
    return " ".join(word.capitalize() for word in text.split(" "))


def _read_instruction_meta(instruction_path: Path) -> tuple[str, str]:
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


def get_task_detail(task_path: str, *, repo_root: Path) -> dict[str, Any]:
    normalized = task_path.strip().replace("\\", "/").strip("/")
    if not normalized:
        raise ValueError("task_path must not be empty")
    task_dir = repo_root / normalized
    if not task_dir.is_dir():
        raise FileNotFoundError("task not found: {}".format(normalized))

    instruction_path = task_dir / "instruction.md"
    instruction_md = (
        instruction_path.read_text(encoding="utf-8").strip() if instruction_path.is_file() else ""
    )
    instruction_title, instruction_blurb = _read_instruction_meta(instruction_path)

    extra_docs: list[dict[str, str]] = []
    for name in ("user_scenario.yaml", "survey_questions.md", "README.md"):
        doc_path = task_dir / name
        if doc_path.is_file():
            extra_docs.append(
                {
                    "name": name,
                    "content": doc_path.read_text(encoding="utf-8").strip(),
                }
            )

    meta_type = ""
    task_name = task_dir.name
    toml_path = task_dir / "task.toml"
    if toml_path.is_file():
        raw = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        meta_type = str(meta.get("type") or "")
        task_block = raw.get("task") if isinstance(raw.get("task"), dict) else {}
        task_name = str(task_block.get("name") or task_name)

    title = instruction_title or _humanize_key(task_dir.name.replace("-", " "))
    description = instruction_blurb

    markdown_parts = [f"# {title}", ""]
    if description:
        markdown_parts.extend([description, ""])
    markdown_parts.append(f"**Harbor path:** `{normalized}`")
    if meta_type:
        markdown_parts.append(f"**Type:** `{meta_type}`")
    if task_name and task_name != task_dir.name:
        markdown_parts.append(f"**Task name:** `{task_name}`")
    markdown_parts.append("")
    if instruction_md:
        markdown_parts.extend(["---", "", instruction_md])
    for doc in extra_docs:
        if doc["name"] == "instruction.md":
            continue
        markdown_parts.extend(["", "---", "", f"## {doc['name']}", ""])
        if doc["name"].endswith(".md"):
            markdown_parts.append(doc["content"])
        else:
            markdown_parts.extend(["```yaml", doc["content"], "```"])

    return {
        "taskPath": normalized,
        "title": title,
        "description": description,
        "metaType": meta_type,
        "taskName": task_name,
        "instructionMarkdown": instruction_md,
        "profileMarkdown": "\n".join(markdown_parts).strip(),
        "extraDocs": extra_docs,
    }


def attach_task_profile_markdown(
    payload: dict[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    """Add ``profileMarkdown`` to a task dict when ``taskPath`` is known."""
    task_path = str(payload.get("taskPath") or payload.get("task_path") or "").strip()
    if not task_path:
        return payload
    try:
        detail = get_task_detail(task_path, repo_root=repo_root)
    except (FileNotFoundError, ValueError, OSError):
        return payload
    merged = dict(payload)
    merged["profileMarkdown"] = detail.get("profileMarkdown") or ""
    merged["instructionMarkdown"] = detail.get("instructionMarkdown") or ""
    return merged
