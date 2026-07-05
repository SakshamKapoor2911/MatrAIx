"""PersonaEval task index — maintained by PersonaEval, not task contributors.

Contributors declare Harbor-standard metadata in ``task.toml`` (``metadata.type``,
``metadata.os`` for OS app tasks, ``domain``, ``difficulty``, ``tags``). This registry only
answers PersonaEval questions: which cockpit a task belongs in, example vs task, and
eval-runtime overrides that Harbor metadata does not cover.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class PersonaEvalTaskEntry:
    application_type: str
    task_kind: Optional[str] = None
    site_name: str = ""
    site_url: str = ""
    output_artifact: str = ""
    submission_profile: str = ""
    os_app_backend: str = ""
    os_app_platform: str = ""
    environment_label: str = ""
    os_app_submission_profile: Optional[str] = None


def default_task_kind(folder_name: str) -> str:
    return "example" if folder_name.startswith("example-") else "task"


def resolve_task_kind(folder_name: str, entry: PersonaEvalTaskEntry) -> str:
    return default_task_kind(folder_name)


# folder name → PersonaEval routing. Keys are repo paths under application/tasks/.
PERSONA_EVAL_TASK_INDEX: Dict[str, PersonaEvalTaskEntry] = {
    # OS app (computer-use)
    "example-computer-use-linux_note-to-csv": PersonaEvalTaskEntry(
        application_type="os-app",
        os_app_backend="docker",
        os_app_platform="linux",
        environment_label="Docker Xvfb · persona-computer-1",
    ),
    "example-computer-use-macos_calendar-reminder-handoff": PersonaEvalTaskEntry(
        application_type="os-app",
        os_app_backend="macos",
        os_app_platform="macos",
        environment_label="use.computer · persona-computer-1",
    ),
    "example-computer-use-ios_photo-access-review": PersonaEvalTaskEntry(
        application_type="os-app",
        os_app_backend="ios",
        os_app_platform="ios",
        environment_label="use.computer iOS · persona-computer-1",
    ),
    # Web
    "example-web-playwright_quote-choice": PersonaEvalTaskEntry(
        application_type="web",
        site_name="quotes.toscrape.com",
        site_url="https://quotes.toscrape.com/",
        output_artifact="quote_choice.json",
        submission_profile="quote_choice",
    ),
    "example-web-browser-use_laptop-choice": PersonaEvalTaskEntry(
        application_type="web",
        site_name="webscraper.io laptops",
        site_url="https://webscraper.io/test-sites/e-commerce/static/computers/laptops",
        output_artifact="laptop_choice.json",
        submission_profile="laptop_choice",
    ),
    "example-web-cocoa_plan-choice": PersonaEvalTaskEntry(
        application_type="web",
        site_name="PythonAnywhere pricing",
        site_url="https://www.pythonanywhere.com/pricing/",
        output_artifact="plan_choice.json",
        submission_profile="plan_choice",
    ),
    "example-web-cua_bookshop-choice": PersonaEvalTaskEntry(
        application_type="web",
        site_name="books.toscrape.com",
        site_url="https://books.toscrape.com/",
        output_artifact="book_interest.json",
        submission_profile="book_interest",
    ),
    # Chatbot
    "recommender-agent_chat_api": PersonaEvalTaskEntry(application_type="chatbot"),
    "finance-openbb_chatbot": PersonaEvalTaskEntry(application_type="chatbot"),
    "medical-assistant_chatbot": PersonaEvalTaskEntry(application_type="chatbot"),
    "example-chat-mcp_support_chatbot": PersonaEvalTaskEntry(
        application_type="chatbot"
    ),
    # Survey (questionnaire metadata mapping still lives in survey_task_content)
    "example-survey_product-feedback": PersonaEvalTaskEntry(application_type="survey"),
    "survey_product-attitudes": PersonaEvalTaskEntry(application_type="survey"),
    "survey_claude-code-vscode-checkpoints": PersonaEvalTaskEntry(application_type="survey"),
    "survey_robinhood-cortex-digests": PersonaEvalTaskEntry(application_type="survey"),
    "survey_cvs-prescription-ai": PersonaEvalTaskEntry(application_type="survey"),
    "survey_nike-air-max-dn": PersonaEvalTaskEntry(application_type="survey"),
}


def get_persona_eval_entry(folder_name: str) -> PersonaEvalTaskEntry | None:
    return PERSONA_EVAL_TASK_INDEX.get(folder_name)


def default_os_app_backend(meta_type: str, entry: PersonaEvalTaskEntry, os: str = "") -> str:
    if entry.os_app_backend:
        return entry.os_app_backend
    os_key = (os or "").strip().lower()
    if os_key == "macos":
        return "macos"
    if os_key == "ios":
        return "ios"
    if meta_type == "mobile":
        return "ios"
    return "docker"


def default_os_app_platform(meta_type: str, os_app_backend: str, os: str = "") -> str:
    os_key = (os or "").strip().lower()
    if os_key:
        return os_key
    if os_app_backend == "macos":
        return "macos"
    if os_app_backend == "ios":
        return "ios"
    if meta_type == "web":
        return "web"
    if meta_type == "mobile":
        return "ios"
    if meta_type == "desktop":
        return "linux"
    return "linux"


def default_environment_label(os_app_platform: str) -> str:
    if os_app_platform == "linux":
        return "Docker Xvfb · persona-computer-1"
    if os_app_platform == "macos":
        return "use.computer · persona-computer-1"
    if os_app_platform == "ios":
        return "use.computer iOS · persona-computer-1"
    if os_app_platform == "web":
        return "Docker web CUA · persona-computer-1"
    return "persona-computer-1"
