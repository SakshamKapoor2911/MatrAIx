"""Shared persistence for PersonaEval run artifacts.

All three eval surfaces (chatbot, survey, web) persist their finished runs as
``{id}.json`` files under one cache dir so the Runs list and detail surfaces can
show every kind of run and they survive a backend restart. Writes are atomic and
best-effort: a persistence failure must never fail the run itself.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional


def default_runs_dir() -> Path:
    """Canonical cache dir for run artifacts (gitignored).

    ``data/cache/persona_eval/persona_eval_runs`` relative to the repo root.
    run_store.py -> service -> backend -> persona_eval -> applications -> root.
    """
    return (
        Path(__file__).resolve().parents[4]
        / "data"
        / "cache"
        / "persona_eval"
        / "persona_eval_runs"
    )


def web_screenshots_dir(runs_dir: Path, run_id: str) -> Path:
    """Durable per-run dir for a web run's trace screenshots."""
    return runs_dir / "web_screenshots" / run_id


def friendly_persona_name(persona: Any) -> str:
    """A recognizable display name for a persona.

    Datasets like Nemotron label personas ``"Source · id"``; the Catalog instead
    shows the occupation from the structured context. Mirror that here so a run's
    persona reads as e.g. "Financial Manager" rather than "Nemotron · 01B0D4D4".
    Falls back to the raw name (then source) when no occupation is present.
    """
    if isinstance(persona, dict):
        name = str(persona.get("name") or "")
        context = str(persona.get("context") or "")
        source = str(persona.get("source") or "")
    else:
        name = str(getattr(persona, "name", "") or "")
        context = str(getattr(persona, "context", "") or "")
        source = str(getattr(persona, "source", "") or "")
    for line in context.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("occupation:"):
            occupation = stripped.split(":", 1)[1].strip()
            if occupation:
                return occupation
    return name or source or "Persona"


def persona_summary(persona: Any) -> Dict[str, Any]:
    """Minimal persona view stored on a run record (drives Runs list + detail)."""
    return {
        "id": getattr(persona, "id", None),
        "name": friendly_persona_name(persona),
        "source": getattr(persona, "source", None),
        "context": getattr(persona, "context", None),
    }


def persist_run(runs_dir: Path, payload: Dict[str, Any]) -> None:
    """Atomically write ``payload`` (which must carry a top-level ``id``) to
    ``{runs_dir}/{id}.json``. Best-effort: any failure is swallowed."""
    run_id = payload.get("id")
    if not run_id:
        return
    try:
        runs_dir.mkdir(parents=True, exist_ok=True)
        target = runs_dir / "{}.json".format(run_id)
        fd, tmp = tempfile.mkstemp(dir=str(runs_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, str(target))
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    except Exception:  # noqa: BLE001 - persistence is best-effort
        return


def load_run(runs_dir: Path, run_id: str) -> Optional[Dict[str, Any]]:
    """Return the stored record for ``run_id``, or ``None`` if absent/corrupt."""
    path = runs_dir / "{}.json".format(run_id)
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001 - skip unreadable/corrupt artifacts
        return None


def iter_run_records(runs_dir: Path) -> List[Dict[str, Any]]:
    """Load every run record under ``runs_dir`` (corrupt artifacts skipped)."""
    if not runs_dir.is_dir():
        return []
    records: List[Dict[str, Any]] = []
    for path in runs_dir.glob("*.json"):
        data = load_run(runs_dir, path.stem)
        if data is not None:
            records.append(data)
    return records


def _application_type(record: Dict[str, Any]) -> str:
    """Discriminate a run record's kind: explicit field, else sniff its artifact."""
    explicit = str(record.get("applicationType") or "").lower()
    if explicit in ("survey", "web", "chatbot"):
        return explicit
    if (
        record.get("webResult") is not None
        or record.get("webTrace") is not None
        or record.get("trace") is not None
    ):
        return "web"
    if record.get("surveyResult") is not None:
        return "survey"
    return "chatbot"


def summarize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Type-aware Runs-list summary for one persisted run record.

    Keeps the chatbot summary contract (``domain``/``goalContextId``/``numTurns``)
    and adds ``applicationType`` plus a per-type ``overallRating`` (out of 10):
    chatbot uses the self-report rating, web the experience rating, and survey
    maps its 1-5 mean Likert onto the shared 1-10 chip scale.
    """
    app_type = _application_type(record)
    persona = record.get("persona") or {}
    summary: Dict[str, Any] = {
        "id": record.get("id"),
        "createdAt": record.get("createdAt"),
        "applicationType": app_type,
        "domain": None,
        "personaName": friendly_persona_name(persona),
        "source": persona.get("source"),
        "goalContextId": None,
        "overallRating": None,
        "numTurns": None,
    }
    if app_type == "survey":
        completion = (record.get("surveyResult") or {}).get("completion") or {}
        mean_likert = completion.get("meanLikert")
        if isinstance(mean_likert, (int, float)):
            summary["overallRating"] = round(mean_likert * 2)
    elif app_type == "web":
        rating = (record.get("webResult") or {}).get("overallExperienceRating")
        if isinstance(rating, (int, float)):
            summary["overallRating"] = rating
    else:  # chatbot
        config = record.get("config") or {}
        questionnaire = record.get("questionnaire") or {}
        metric_scores = record.get("metricScores") or {}
        summary["domain"] = config.get("domain")
        summary["goalContextId"] = config.get("goalContextId")
        summary["overallRating"] = questionnaire.get("overallRating")
        summary["numTurns"] = metric_scores.get("numTurns")
    return summary
