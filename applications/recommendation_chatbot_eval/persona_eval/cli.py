"""``python -m persona_eval`` — run one headless persona persona-eval end to end.

The CLI ties the whole engine together:

1. resolve the persona fixture and the per-domain SUT description,
2. build a real :class:`~backend.service.session.RecBotSession` (native RecAI,
   ``recai_resources`` mode) via :func:`persona_eval.session_factory.build_session`,
3. drive a single multi-turn conversation with an OpenAI user-simulator (which
   also gives its own post-use feedback) through :func:`persona_eval.runner.run_persona_eval`,
4. print a readable transcript + questionnaire and write the JSON artifact under
   ``data/cache/recommendation_chatbot_eval/persona_eval_runs/<persona-id>.json``
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

from persona_eval.goal_contexts import get_goal_context
from persona_eval.openai_client import OpenAIChatClient
from persona_eval.persona import get_persona
from persona_eval.runner import run_persona_eval
from persona_eval.sut_descriptions import sut_description_for
from persona_eval.types import PersonaEvalConfig, PersonaEvalResult
from persona_eval.user_simulator import UserSimulator

__all__ = ["format_transcript", "run_from_args", "main"]


def format_transcript(result: PersonaEvalResult) -> str:
    """Render a :class:`PersonaEvalResult` as a human-readable CLI transcript."""
    lines = ["=== Persona eval: {} ({}) ===".format(result.persona.name, result.config.domain),
             "Persona goal: {}".format(result.persona.goal), ""]
    for t in result.transcript:
        lines.append("USER:  {}".format(t.user_message))
        lines.append("AGENT: {}".format(t.assistant_message))
        if t.recommended_items:
            lines.append("       recs: {}".format(
                ", ".join("{} ({})".format(i.get("title") or "?", i["id"]) for i in t.recommended_items)))
        lines.append("")
    q = result.questionnaire
    lines += ["--- Evaluation ---",
              "Constraint satisfaction: {}/5 — {}".format(q.constraint_satisfaction, q.constraint_rationale),
              "Preference satisfaction: {}/5 — {}".format(q.preference_satisfaction, q.preference_rationale),
              "Overall: {}/10 — {}".format(q.overall_rating, q.rating_reason),
              "Useful clarifying questions: {} — {}".format(q.asked_useful_clarifying_questions, q.clarifying_notes),
              "turns-to-recommendation: {}".format(result.metric_scores.turns_to_recommendation),
              "num turns: {}".format(result.metric_scores.num_turns)]
    return "\n".join(lines)


def _artifact_dir() -> Path:
    """``<repo>/data/cache/recommendation_chatbot_eval/persona_eval_runs`` (gitignored)."""
    from recbot.paths import APP_ROOT

    return APP_ROOT.parents[1] / "data" / "cache" / "recommendation_chatbot_eval" / "persona_eval_runs"


def run_from_args(argv: List[str], *, now: Callable[[], str]) -> PersonaEvalResult:
    """Parse ``argv``, run one real persona-eval, write the artifact, and print it."""
    parser = argparse.ArgumentParser(prog="persona_eval")
    parser.add_argument("--domain", required=True, choices=["movie", "beauty_product", "game"])
    parser.add_argument("--persona", required=True)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--engine", default="gpt-4o-mini")
    parser.add_argument("--goal-context", default="scenario_default")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    persona = get_persona(args.persona)
    goal_context = get_goal_context(args.goal_context)
    config = PersonaEvalConfig(domain=args.domain, engine=args.engine,
                            ranker_mode="native", resource_mode="recai_resources",
                            max_turns=args.max_turns, goal_context_id=goal_context.id)

    # Build the real session the same way the backend does: resolve the catalog
    # path from INTERECAGENT_CATALOG_PATH or the canonical default (deps.
    # resolve_catalog_path), construct CatalogIndex(path), and mint the session
    # via session_factory (a direct RecBotSession(...) like SessionManager.create).
    from backend.api.deps import resolve_catalog_path
    from backend.service.catalog_index import CatalogIndex
    from backend.service.config import ConfigManager
    from persona_eval.session_factory import build_session
    config_manager = ConfigManager()
    catalog = CatalogIndex(resolve_catalog_path())
    session = build_session(config, catalog=catalog, config_manager=config_manager)

    client = OpenAIChatClient(model=args.engine)
    result = run_persona_eval(session, persona, sut_description_for(args.domain), config,
                           UserSimulator(client, goal_context, args.domain),
                           created_at=now(), on_event=lambda e: None)

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
