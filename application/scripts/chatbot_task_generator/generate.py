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


def _parse_capabilities(text: str) -> str:
    """Convert comma-separated capability names to indented YAML list."""
    items = [c.strip() for c in text.split(",") if c.strip()]
    if not items:
        return "  - text_chat"
    return "\n".join(f"  - {item}" for item in items)


def _parse_rules(rules_text: str) -> list[dict]:
    """Parse rules column into knowledge_base.json rule entries.

    Format: one JSON object per line, each with keys:
      pattern (str, required), response (str, required), priority (int, optional, defaults to 0).
    """
    rules = []
    for line in rules_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            rule = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rule, dict):
            continue
        pattern = rule.get("pattern", "").strip()
        response = rule.get("response", "").strip()
        if not pattern or not response:
            continue
        try:
            priority = int(rule.get("priority", 0)) if "priority" in rule else 0
        except (ValueError, TypeError):
            priority = 0
        rules.append({"pattern": pattern, "response": response, "priority": priority})
    return rules


def _parse_dimension_filters(text: str) -> dict:
    """Parse JSON string into dimensionFilters dict."""
    if not text or not text.strip():
        return {}
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {}


def _default_dimension_filters(domain: str) -> dict:
    """Return sensible dimension filters per domain for the CI cohort gate."""
    domain = domain.lower()
    intent_map = {
        "education": ["Learn / explain", "Brainstorm", "Get task done"],
        "legal": ["Get task done", "Vent / support", "Decide"],
        "travel": ["Get task done", "Decide"],
        "real-estate": ["Get task done", "Decide"],
        "telecom": ["Vent / support", "Get task done"],
        "insurance": ["Get task done", "Decide"],
        "healthcare": ["Vent / support", "Get task done", "Learn / explain"],
        "customer-support": ["Vent / support", "Get task done"],
    }
    intent = intent_map.get(domain, ["Get task done"])
    return {
        "age_bracket": ["18-24", "25-34", "35-44", "45-54", "55-64"],
        "intent": intent,
    }


def _build_persona_strategy(row: dict) -> dict:
    """Build persona_strategy.json content from CSV row data."""
    filters = _parse_dimension_filters(row.get("ps_dimensionFilters", ""))
    sample_size_text = row.get("ps_sampleSize", "").strip()
    if not filters:
        filters = _default_dimension_filters(row.get("domain", ""))
    strategy = {
        "schemaVersion": "1.0",
        "sources": [],
        "defaultMode": row.get("ps_defaultMode", "").strip() or "random",
        "dimensionFilters": filters,
    }
    stratify_raw = _v(row, "ps_stratifyFields", "").strip()
    if stratify_raw:
        strategy["stratifyFields"] = [s.strip() for s in stratify_raw.split(",") if s.strip()]
    if sample_size_text:
        try:
            strategy["sampleSize"] = int(sample_size_text)
        except ValueError:
            pass
    return strategy


def substitute_file(template: Path, output: Path, variables: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    content = template.read_text(encoding="utf-8")
    for key, value in variables.items():
        content = content.replace(f"{{{key}}}", str(value))
    output.write_text(content, encoding="utf-8")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _v(row: dict, key: str, default: str = "") -> str:
    """Get a CSV cell value, returning default for None/missing."""
    val = row.get(key, default)
    return val if val is not None else default


def write_knowledge_base(task_dir: Path, row: dict) -> None:
    """Create input/knowledge_base.json from CSV row data."""
    input_dir = task_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    rules_text = _v(row, "rules").strip()
    rules = _parse_rules(rules_text) if rules_text else []

    kb = {
        "bot_name": _v(row, "bot_name", row["domain"].title() + " Assistant"),
        "greeting": row["greeting"],
        "fallback": row["fallback"],
        "rules": rules,
        "context": {},
    }

    (input_dir / "knowledge_base.json").write_text(
        json.dumps(kb, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def write_persona_strategy(task_dir: Path, row: dict) -> None:
    """Create persona_strategy.json at task root from CSV row data."""
    strategy = _build_persona_strategy(row)
    out_path = task_dir / "persona_strategy.json"
    out_path.write_text(
        json.dumps(strategy, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _auto_context(domain: str) -> str:
    """Generate a sensible context.md description from domain name."""
    domain_lower = domain.lower()
    if domain_lower == "education":
        return (
            "An AI tutoring chatbot that helps learners understand academic "
            "concepts through adaptive dialogue.\n\n"
            "It asks about your current knowledge level and learning goals, "
            "then tailors explanations to your needs.\n\n"
            "What it is good for: getting step-by-step explanations, breaking "
            "down complex topics, and filling knowledge gaps.\n\n"
            "What it is not: a homework solver, a grading tool, or a "
            "substitute for a human teacher.\n\n"
            "## What you can do in this product\n\n"
            "- Ask questions about a topic and get explanations at your level.\n"
            "- Answer the chatbot's clarifying questions about what you "
            "already know."
        )
    if domain_lower in ("legal", "tenant-rights"):
        return (
            "A legal information assistant focused on tenant rights and "
            "landlord-tenant law.\n\n"
            "It asks about your housing situation and explains relevant "
            "rules for your jurisdiction.\n\n"
            "What it is good for: understanding your rights as a tenant, "
            "learning about eviction rules, security deposits, and repair "
            "obligations.\n\n"
            "What it is not: a licensed attorney, legal representation, or "
            "a substitute for professional legal advice.\n\n"
            "## What you can do in this product\n\n"
            "- Describe your housing situation and get information about "
            "relevant laws.\n"
            "- Ask follow-up questions about specific tenant rights."
        )
    if domain_lower in ("travel", "hospitality"):
        return (
            "A travel booking support chatbot that helps with changing or "
            "canceling trip itineraries.\n\n"
            "It looks up your booking details and explains available "
            "options, fees, and policies.\n\n"
            "What it is good for: changing flight dates, canceling hotel "
            "reservations, modifying car rentals, and understanding change "
            "fees or refund amounts.\n\n"
            "What it is not: a travel agent who can book new trips or handle "
            "emergencies.\n\n"
            "## What you can do in this product\n\n"
            "- Provide your booking reference and request a change to your "
            "itinerary.\n"
            "- Ask about cancellation policies and fees."
        )
    if domain_lower in ("real-estate", "rental"):
        return (
            "A rental application screening chatbot that helps prospective "
            "tenants understand whether they qualify for a property.\n\n"
            "It asks about your income, rental history, and other criteria "
            "that landlords typically evaluate.\n\n"
            "What it is good for: getting a preliminary eligibility check "
            "before submitting a full rental application.\n\n"
            "What it is not: a guarantee of approval, a credit check, or a "
            "substitute for the landlord's formal screening process.\n\n"
            "## What you can do in this product\n\n"
            "- Tell the assistant which property you are interested in.\n"
            "- Answer questions about your finances and rental history "
            "honestly."
        )
    if domain_lower in ("telecom", "telecommunications"):
        return (
            "A mobile carrier support chatbot that helps with billing "
            "issues and plan changes.\n\n"
            "It can look up your account, explain charges, and describe "
            "available plan options with correct proration.\n\n"
            "What it is good for: disputing charges, changing your mobile "
            "plan, understanding fees, and getting account help.\n\n"
            "What it is not: a guarantee that a charge will be removed or a "
            "plan change will be effective immediately.\n\n"
            "## What you can do in this product\n\n"
            "- Provide your account or phone number for verification.\n"
            "- Describe the billing issue or plan change you need."
        )
    if domain_lower in ("insurance", "claims"):
        return (
            "An insurance claims assistant that helps policyholders file "
            "claims and understand their coverage.\n\n"
            "It asks about the incident, your policy details, and guides "
            "you through the initial filing steps.\n\n"
            "What it is good for: starting a new claim, understanding your "
            "deductible and coverage limits, and learning what documentation "
            "you will need.\n\n"
            "What it is not: an adjuster who can approve or deny claims, "
            "or a guarantee of payout.\n\n"
            "## What you can do in this product\n\n"
            "- Describe what happened and provide your policy number when "
            "asked.\n"
            "- Answer questions about the incident and your coverage."
        )
    return (
        f"A conversational {domain} chatbot. It asks relevant questions "
        f"and provides information about {domain} topics. It is designed "
        f"for {domain} discussions and is not a general-purpose assistant."
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
        print(f"SKIP {_v(row, 'name', '?')}: {'; '.join(errors)}")
        return None

    name = row["name"].strip()
    slug = _slugify(name)
    full_name = _v(row, "full_name", "").strip() or f"application/{slug}"
    domain = row["domain"].strip()
    difficulty = _v(row, "difficulty", "medium").strip()
    tags_raw = _v(row, "tags", "").strip()
    if tags_raw:
        tag_list = [f'"{t.strip()}"' for t in tags_raw.split(",") if t.strip()]
        tags = ", ".join(tag_list)
    else:
        tags = f'"{domain}"'

    app_id = _v(row, "application_id", "").strip() or f"{_slugify(domain)}_chat"
    app_ctx = _v(row, "application_context", "").strip() or f"{domain}_support"
    sidecar_host = _slugify(_v(row, "sidecar_host", "").strip() or name)

    capabilities_raw = _v(row, "capabilities", "").strip() or "text_chat"
    capabilities = _parse_capabilities(capabilities_raw)

    persona_role = _v(row, "persona_role", "").strip() or "customer"
    chatbot_role = _v(row, "chatbot_role", "").strip() or "assistant"

    base_url_env = _v(row, "base_url_env", "").strip() or "CHATBOT_API_URL"
    persona_exposure_fields = _v(row, "persona_exposure_fields", "").strip() or "[]"
    context_description = _v(row, "context_description", "").strip() or _auto_context(domain)

    local_compose = _v(row, "local_compose", "").strip() or f"application/chatbot-api-sidecar_{slug}"

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
        "persona_background_header": _v(row, "persona_background_header", "").strip()
            or f"Your {domain} scenario",
        "task_goal_label": row["task_goal_label"].strip(),
        "task_title": _v(row, "task_title", "").strip()
            or f"{domain.title()} Chatbot",
        "local_compose": local_compose,
        "capabilities": capabilities,
        "base_url_env": base_url_env,
        "sidecar_host": sidecar_host,
        "persona_role": persona_role,
        "chatbot_role": chatbot_role,
        "persona_exposure_fields": persona_exposure_fields,
        "context_description": context_description,
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
    write_persona_strategy(task_dir, row)

    print(f"  -> {task_dir}")
    print(f"  -> {task_dir / 'input' / 'knowledge_base.json'}")
    print(f"  -> {task_dir / 'persona_strategy.json'}")
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
            if task_name and _slugify(_v(row, "name", "")) != _slugify(task_name):
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
