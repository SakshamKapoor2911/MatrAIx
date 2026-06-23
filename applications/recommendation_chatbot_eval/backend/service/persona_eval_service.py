"""Run a persona persona-eval as a background job with live progress.

Persona-eval execution is serialized process-globally (`_RUN_LOCK`): the in-process
RecAI agent and ``os.environ`` are shared across sessions, so only one persona-eval
may drive RecAI at a time.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from persona_eval.runner import run_persona_eval as _default_runner
from persona_eval.types import PersonaEvalConfig

_RUN_LOCK = threading.Lock()


def _new_persona_eval_id() -> str:
    import uuid
    return "wt_" + uuid.uuid4().hex[:12]


def _default_runs_dir() -> Path:
    """Canonical cache dir for persona-eval run artifacts (gitignored).

    ``data/cache/recommendation_chatbot_eval/persona_eval_runs`` relative to the repo
    root (mirrors :func:`backend.service.session_store._default_base_dir`).
    """
    here = os.path.abspath(__file__)
    # persona_eval_service.py -> service -> backend -> recommendation_chatbot_eval ->
    # applications -> <repo root>
    repo_root = here
    for _ in range(5):
        repo_root = os.path.dirname(repo_root)
    return Path(repo_root) / "data" / "cache" / "recommendation_chatbot_eval" / "persona_eval_runs"


@dataclass
class PersonaEvalProgress:
    job_id: str
    domain: str
    persona_id: str
    persona_name: str
    sut_description: str
    goal_context_id: str = "scenario_default"
    status: str = "building"  # building | running | done | error
    phase: Optional[str] = None
    turns: List[Dict[str, Any]] = field(default_factory=list)
    questionnaire: Optional[Dict[str, Any]] = None
    metric_scores: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_view(self) -> Dict[str, Any]:
        return {
            "jobId": self.job_id, "domain": self.domain, "personaId": self.persona_id,
            "personaName": self.persona_name, "sutDescription": self.sut_description,
            "goalContextId": self.goal_context_id,
            "status": self.status, "phase": self.phase, "turns": list(self.turns),
            "questionnaire": self.questionnaire, "metricScores": self.metric_scores,
            "error": self.error,
        }


class PersonaEvalService:
    def __init__(self, *, session_builder: Callable[[PersonaEvalConfig], Any],
                 get_persona: Callable[[str], Any], sut_for: Callable[[str], str],
                 simulator_factory: Callable[[str, str, str], Any],
                 runner: Callable[..., Any] = _default_runner,
                 engine: str = "gpt-4o-mini",
                 runs_dir: Optional[Path] = None) -> None:
        self._session_builder = session_builder
        self._get_persona = get_persona
        self._sut_for = sut_for
        self._simulator_factory = simulator_factory
        self._runner = runner
        self._engine = engine
        self._runs_dir = Path(runs_dir) if runs_dir is not None else _default_runs_dir()
        self._guard = threading.Lock()
        self._progress: Dict[str, PersonaEvalProgress] = {}

    def start(self, domain: str, persona_id: str, max_turns: int,
              goal_context_id: str = "scenario_default",
              *, now: Callable[[], str], engine: Optional[str] = None) -> str:
        # Persona is domain-free: any persona may run against any domain.
        # ``engine`` drives BOTH the recommender (per-run ``INTERECAGENT_ENGINE``)
        # and the user-simulator's OpenAI model; ``None`` keeps the service
        # default so existing callers are unchanged.
        persona = self._get_persona(persona_id)
        run_engine = engine or self._engine
        job_id = _new_persona_eval_id()
        progress = PersonaEvalProgress(
            job_id=job_id, domain=domain, persona_id=persona_id,
            persona_name=getattr(persona, "name", persona_id),
            sut_description=self._sut_for(domain),
            goal_context_id=goal_context_id)
        with self._guard:
            self._progress[job_id] = progress
        thread = threading.Thread(
            target=self._run, args=(progress, persona, max_turns, run_engine, now), daemon=True)
        thread.start()
        return job_id

    def view(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._guard:
            progress = self._progress.get(job_id)
            return progress.to_view() if progress else None

    # ------------------------------------------------------------------ #
    # Persisted runs (durable artifacts under ``runs_dir``)
    # ------------------------------------------------------------------ #
    def _persist_run(self, job_id: str, result: Any) -> None:
        """Write ``result.to_dict()`` (plus a top-level ``id``) atomically.

        Best-effort: a write failure must not fail the run itself, so a finished
        run still reports ``done`` even if its artifact could not be saved.
        """
        try:
            payload = result.to_dict()
        except Exception:  # noqa: BLE001 - non-serializable runner result
            return
        payload["id"] = job_id
        try:
            self._runs_dir.mkdir(parents=True, exist_ok=True)
            target = self._runs_dir / "{}.json".format(job_id)
            fd, tmp = tempfile.mkstemp(dir=str(self._runs_dir), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False, indent=2)
                os.replace(tmp, str(target))
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            return

    def _load_run(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else None
        except Exception:  # noqa: BLE001 - skip unreadable/corrupt artifacts
            return None

    def list_runs(self) -> List[Dict[str, Any]]:
        """Newest-first run summaries read from disk.

        Each summary is
        ``{id, createdAt, domain, personaName, source, goalContextId,
        overallRating, numTurns}``; corrupt/unreadable artifacts are skipped.
        """
        if not self._runs_dir.is_dir():
            return []
        summaries: List[Dict[str, Any]] = []
        for path in self._runs_dir.glob("*.json"):
            data = self._load_run(path)
            if data is None:
                continue
            config = data.get("config") or {}
            persona = data.get("persona") or {}
            questionnaire = data.get("questionnaire") or {}
            metric_scores = data.get("metricScores") or {}
            summaries.append({
                "id": data.get("id") or path.stem,
                "createdAt": data.get("createdAt"),
                "domain": config.get("domain"),
                "personaName": persona.get("name"),
                "source": persona.get("source"),
                "goalContextId": config.get("goalContextId"),
                "overallRating": questionnaire.get("overallRating"),
                "numTurns": metric_scores.get("numTurns"),
            })
        summaries.sort(key=lambda s: (s.get("createdAt") or ""), reverse=True)
        return summaries

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """The full stored result for ``run_id``, or ``None`` if absent.

        Guarantees a top-level ``id`` even for legacy artifacts (e.g. CLI-written
        runs keyed by persona id) that predate ``_persist_run``'s id injection, so
        the ``PersonaEvalResultView`` response contract always holds.
        """
        path = self._runs_dir / "{}.json".format(run_id)
        if not path.is_file():
            return None
        data = self._load_run(path)
        if data is not None:
            data["id"] = data.get("id") or run_id
        return data

    def _run(self, progress: PersonaEvalProgress, persona: Any, max_turns: int,
             engine: str, now: Callable[[], str]) -> None:
        with _RUN_LOCK:  # serialize all RecAI-driving persona-evals
            try:
                config = PersonaEvalConfig(domain=progress.domain, engine=engine,
                                        ranker_mode="native", resource_mode="recai_resources",
                                        max_turns=max_turns,
                                        goal_context_id=progress.goal_context_id)
                session = self._session_builder(config)
                with self._guard:
                    progress.status = "running"

                def on_event(event: Dict[str, Any]) -> None:
                    etype = event.get("type")
                    if etype == "phase":
                        phase = event.get("phase")
                        with self._guard:
                            progress.phase = phase
                    elif etype == "turn":
                        with self._guard:
                            progress.turns = list(getattr(session, "turns", progress.turns))
                    elif etype == "done":
                        result = event.get("result") or {}
                        questionnaire = result.get("questionnaire")
                        metric_scores = result.get("metricScores")
                        with self._guard:
                            progress.questionnaire = questionnaire
                            progress.metric_scores = metric_scores

                result = self._runner(
                    session, persona, progress.sut_description, config,
                    self._simulator_factory(engine, progress.goal_context_id, progress.domain),
                    created_at=now(), on_event=on_event)
                self._persist_run(progress.job_id, result)
                with self._guard:
                    progress.turns = list(getattr(session, "turns", progress.turns))
                    progress.phase = None
                    progress.status = "done"
            except BaseException as exc:  # noqa: BLE001 - surface any failure to the client
                with self._guard:
                    progress.error = "{}: {}".format(type(exc).__name__, exc)
                    progress.status = "error"
