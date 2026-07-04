"""``python -m persona_eval`` — run one headless persona persona-eval end to end.

The CLI ties the whole engine together:

1. resolve the persona fixture and the per-domain SUT description,
2. build a real :class:`~backend.service.session.RecBotSession` (native RecAI,
   ``recai_resources`` mode) through the local chatbot runtime helper,
3. drive a single multi-turn conversation with an OpenAI user-simulator (which
   also gives its own post-use feedback) through :func:`persona_eval.runner.run_persona_eval`,
4. print a readable transcript + questionnaire and write the JSON artifact under
   ``data/cache/persona_eval/persona_eval_runs/<persona-id>.json``
   (gitignored).

Only :func:`format_transcript` is exercised by the unit test (it is pure /
offline); :func:`run_from_args` and :func:`main` touch the real RecAI session and
OpenAI and so run only in the genuine end-to-end invocation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, List

from persona_eval.persona_catalog import get_persona
from persona_eval.runner import run_persona_eval
from persona_eval.types import PersonaEvalConfig, PersonaEvalResult

__all__ = ["format_transcript", "run_from_args", "main"]


def format_transcript(result: PersonaEvalResult) -> str:
    """Render a :class:`PersonaEvalResult` as a human-readable CLI transcript."""
    context_label = (
        result.config.application_context
        or result.config.domain
        or result.config.application_id
        or "chatbot"
    )
    lines = ["=== Persona eval: {} ({}) ===".format(result.persona.name, context_label),
             "Persona goal: {}".format(result.persona.goal), ""]
    for t in result.transcript:
        lines.append("USER:  {}".format(t.user_message))
        lines.append("AGENT: {}".format(t.assistant_message))
        for item in t.persona_exposure:
            label = item.get("label") or item.get("key") or "detail"
            value = item.get("value")
            if value not in (None, "", []):
                lines.append("       {}: {}".format(label, value))
        lines.append("")
    q = result.questionnaire
    lines += ["--- Evaluation ---",
              "Constraint satisfaction: {}/5 — {}".format(q.constraint_satisfaction, q.constraint_rationale),
              "Preference satisfaction: {}/5 — {}".format(q.preference_satisfaction, q.preference_rationale),
              "Overall: {}/10 — {}".format(q.overall_rating, q.rating_reason),
              "Useful clarifying questions: {} — {}".format(q.asked_useful_clarifying_questions, q.clarifying_notes),
              "num turns: {}".format(result.metric_scores.num_turns)]
    return "\n".join(lines)


def _artifact_dir() -> Path:
    """``<repo>/data/cache/persona_eval/persona_eval_runs`` (gitignored)."""
    from recbot.paths import APP_ROOT

    return APP_ROOT.parents[4] / "data" / "cache" / "persona_eval" / "persona_eval_runs"


def _fallback_sut_description(domain: str) -> str:
    label = str(domain or "").replace("_", " ").strip() or "chatbot"
    return "You are chatting with an interactive {} application.".format(label)


def run_from_args(argv: List[str], *, now: Callable[[], str]) -> PersonaEvalResult:
    """Parse ``argv``, run one real persona-eval, write the artifact, and print it."""
    parser = argparse.ArgumentParser(prog="persona_eval")
    parser.add_argument("--domain", required=True, choices=["movie", "beauty_product", "game"])
    parser.add_argument("--persona", required=True)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--engine", default="gpt-4o-mini")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    persona = get_persona(args.persona)
    config = PersonaEvalConfig(domain=args.domain, engine=args.engine,
                            ranker_mode="native", resource_mode="recai_resources",
                            max_turns=args.max_turns)

    # Build the real session the same way the backend does: resolve the catalog
    # path from INTERECAGENT_CATALOG_PATH or the canonical default (deps.
    # resolve_catalog_path), construct CatalogIndex(path), and mint the session
    # via the local chatbot runtime helper.
    from backend.api.deps import resolve_catalog_path
    from backend.service.catalog_index import CatalogIndex
    from backend.service.config import ConfigManager
    from environment.integrations.persona_eval.local.chatbot_eval import (
        build_local_chat_session,
    )
    config_manager = ConfigManager()
    catalog = CatalogIndex(resolve_catalog_path())
    session = build_local_chat_session(
        config,
        catalog_provider=lambda _domain: catalog,
        config_manager=config_manager,
    )

    result = run_persona_eval(
        session,
        persona,
        _fallback_sut_description(args.domain),
        config,
        created_at=now(),
        on_event=lambda e: None,
    )

    out_path = Path(args.out) if args.out else _artifact_dir() / "{}.json".format(persona.id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    payload["id"] = persona.id
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(format_transcript(result))
    print("\nArtifact: {}".format(out_path))
    return result


def main() -> int:
    """Entry point for ``python -m persona_eval`` (real RecAI + OpenAI run)."""
    import datetime  # only here; argless now() is fine at real runtime (not under the no-clock test)
    run_from_args(sys.argv[1:], now=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
