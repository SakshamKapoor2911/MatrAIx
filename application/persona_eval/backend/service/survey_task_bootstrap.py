"""Bootstrap ``application/tasks/example-survey_*`` folders from task-backed questionnaires."""

from __future__ import annotations

from pathlib import Path

from backend.service.example_task_catalog import repo_root
from backend.service.survey_instruction_builder import render_survey_task_instruction_markdown
from backend.service.survey_questionnaire_catalog import get_survey_questionnaire

from persona_eval.survey_task_content import (
    SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID,
)

_TASK_TOML_TEMPLATE = """version = "1.0"
artifacts = ["/app/output"]

[task]
name = "personabench/application-survey-{slug}"

[metadata]
difficulty = "easy"
type = "survey"
domain = "{domain}"
tags = [{tags}]

[verifier]
timeout_sec = 120.0

[agent]
timeout_sec = 600.0

[environment]
definition = "application/shared-survey-form"
build_timeout_sec = 1800.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
"""

_TEST_SH = """#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"

if python3 "${TESTS_DIR}/test_state.py"; then
  echo 1 > "${VERIFIER_DIR}/reward.txt"
else
  echo 0 > "${VERIFIER_DIR}/reward.txt"
  exit 1
fi
"""

_DOMAINS: dict[str, str] = {
    "product_attitudes_v1": "persona-research",
    "product_feedback_v1": "software",
    "software_claude_code_vscode_checkpoints_v1": "software",
    "finance_robinhood_cortex_digests_v1": "finance",
    "healthcare_cvs_app_prescription_ai_v1": "healthcare",
    "commerce_nike_air_max_dn_dynamic_air_v1": "commerce",
}


def _tags_for(questionnaire_id: str, title: str) -> str:
    words = [word.strip() for word in title.replace("Survey", "").split() if word.strip()]
    tags = words[:4] or [questionnaire_id]
    return ", ".join('"{}"'.format(tag) for tag in tags)


def write_survey_task(questionnaire_id: str, *, repo: Path | None = None) -> Path:
    """Write or refresh one example-survey task folder."""
    folder = SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID[questionnaire_id]
    root = repo or repo_root()
    task_dir = root / "application" / "tasks" / folder
    questionnaire = get_survey_questionnaire(questionnaire_id, repo_root=root)
    slug = folder.removeprefix("example-survey_").removeprefix("survey_").replace("_", "-")
    task_dir.mkdir(parents=True, exist_ok=True)
    preserve_content = questionnaire_id == "product_feedback_v1" and (task_dir / "instruction.md").is_file()
    if not preserve_content:
        (task_dir / "instruction.md").write_text(
            "# {}\n\n{}".format(
                questionnaire.title,
                render_survey_task_instruction_markdown(questionnaire),
            ),
            encoding="utf-8",
        )
    if questionnaire_id != "product_feedback_v1" or not (task_dir / "task.toml").is_file():
        (task_dir / "task.toml").write_text(
            _TASK_TOML_TEMPLATE.format(
                slug=slug,
                domain=_DOMAINS.get(questionnaire_id, "persona-research"),
                tags=_tags_for(questionnaire_id, questionnaire.title),
            ),
            encoding="utf-8",
        )
    tests_dir = task_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    persona_test_state = (
        root / "application" / "tasks" / "example-survey_product-feedback" / "tests" / "test_state.py"
    )
    persona_verifier_env = (
        root / "application" / "tasks" / "example-survey_product-feedback" / "tests" / "verifier_env.sh"
    )
    (tests_dir / "test_state.py").write_text(
        persona_test_state.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tests_dir / "verifier_env.sh").write_text(
        persona_verifier_env.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    test_sh = task_dir / "tests" / "test.sh"
    test_sh.write_text(_TEST_SH, encoding="utf-8")
    test_sh.chmod(0o755)
    readme = task_dir / "README.md"
    if not readme.is_file() or questionnaire_id != "product_feedback_v1":
        readme.write_text(
            "# {}\n\nHarbor survey task.\n\n"
            "- Task instruction: `instruction.md`\n"
            "- Supplementary docs: `input/context.md`, `input/questionnaire.yaml`, `input/output_schema.md`\n"
            "- Output: `/app/output/survey_result.json`\n"
            "- Questionnaire id: `{}`\n".format(questionnaire.title, questionnaire_id),
            encoding="utf-8",
        )
    return task_dir


def write_all_survey_tasks(*, repo: Path | None = None) -> list[Path]:
    return [write_survey_task(qid, repo=repo) for qid in SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID]
