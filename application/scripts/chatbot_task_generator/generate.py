"""Chatbot Task Generator - CSV to task directory.

Usage:
    uv run python application/scripts/chatbot_task_generator/generate.py --csv domains.csv
    uv run python application/scripts/chatbot_task_generator/generate.py --csv domains.csv --task-name education-ai-tutoring_chatbot
"""

import argparse
import csv
import json
import shutil
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "task_templates" / "chatbot"
TASKS_DIR = Path(__file__).resolve().parent.parent.parent / "tasks"

REQUIRED_FIELDS = [
    "name",
    "domain",
    "summarized_goal",
    "persona_background",
    "task_goal_label",
    "greeting",
    "fallback",
]


def _slugify(name: str) -> str:
    return name.strip().lower().replace(" ", "-").replace("_", "-")


def substitute_file(template: Path, output: Path, variables: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    content = template.read_text(encoding="utf-8")
    for key, value in variables.items():
        content = content.replace(f"{{{key}}}", str(value))
    output.write_text(content, encoding="utf-8")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_knowledge_base(task_dir: Path, row: dict) -> None:
    """Create input/knowledge_base.json from CSV row data."""
    input_dir = task_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    kb = {
        "bot_name": row.get("bot_name", row["domain"].title() + " Assistant"),
        "greeting": row["greeting"],
        "fallback": row["fallback"],
        "rules": [],
        "context": {},
    }

    (input_dir / "knowledge_base.json").write_text(
        json.dumps(kb, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def validate_row(row: dict) -> list[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in row or not row[field].strip():
            errors.append(f"Missing required field: {field}")
    return errors


def generate_task(row: dict, dry_run: bool = False) -> Path | None:
    errors = validate_row(row)
    if errors:
        print(f"SKIP {row.get('name', '?')}: {'; '.join(errors)}")
        return None

    name = row["name"].strip()
    full_name = row.get("full_name", "").strip() or f"application/{_slugify(name)}"
    domain = row["domain"].strip()
    difficulty = row.get("difficulty", "medium").strip()
    tags_raw = row.get("tags", "").strip()
    if tags_raw:
        tag_list = [f'"{t.strip()}"' for t in tags_raw.split(",") if t.strip()]
        tags = ", ".join(tag_list)
    else:
        tags = f'"{domain}"'

    app_id = row.get("application_id", "").strip() or f"{_slugify(domain)}_chat"
    app_ctx = row.get("application_context", "").strip() or f"{domain}_support"

    variables = {
        "name": name,
        "full_name": full_name,
        "domain": domain,
        "difficulty": difficulty,
        "tags": tags,
        "application_id": app_id,
        "application_context": app_ctx,
        "summarized_goal": row["summarized_goal"].strip(),
        "persona_background": row["persona_background"].strip(),
        "persona_background_header": row.get("persona_background_header", "").strip()
            or f"Your {domain} scenario",
        "task_goal_label": row["task_goal_label"].strip(),
        "task_title": row.get("task_title", "").strip()
            or f"{domain.title()} Chatbot",
    }

    task_dir = TASKS_DIR / name
    if task_dir.exists() and not dry_run:
        print(f"WARN {name}: target directory already exists, skipping")
        return None

    if dry_run:
        print(f"DRY-RUN {name}: would create {task_dir}")
        return task_dir

    print(f"GEN {name}...")

    for template_file in TEMPLATES.rglob("*.j2"):
        rel = template_file.relative_to(TEMPLATES)
        out_file = task_dir / rel.with_suffix("")
        substitute_file(template_file, out_file, variables)

    for fixed_file in TEMPLATES.rglob("*"):
        if fixed_file.is_dir() or fixed_file.suffix == ".j2":
            continue
        rel = fixed_file.relative_to(TEMPLATES)
        out_file = task_dir / rel
        copy_file(fixed_file, out_file)

    write_knowledge_base(task_dir, row)

    print(f"  -> {task_dir}")
    print(f"  -> {task_dir / 'input' / 'knowledge_base.json'}")
    return task_dir


def generate_all(csv_path_str: str, task_name: str | None = None, dry_run: bool = False) -> list[Path]:
    csv_path = Path(csv_path_str)
    if not csv_path.is_file():
        print(f"ERROR: CSV file not found: {csv_path}")
        return []

    generated = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if task_name and _slugify(row.get("name", "")) != _slugify(task_name):
                continue
            result = generate_task(row, dry_run=dry_run)
            if result:
                generated.append(result)

    print(f"\nDone. Generated {len(generated)} task(s).")
    return generated


def main():
    parser = argparse.ArgumentParser(description="Generate chatbot tasks from CSV")
    parser.add_argument("--csv", required=True, help="Path to domain config CSV")
    parser.add_argument("--task-name", help="Generate a single task by name")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    generate_all(args.csv, task_name=args.task_name, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
