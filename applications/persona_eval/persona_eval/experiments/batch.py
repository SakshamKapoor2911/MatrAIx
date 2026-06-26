from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from persona_eval.experiments.applications import ApplicationSpec
from persona_eval.experiments.models import ExperimentRunResult, ExperimentRunSpec
from persona_eval.types import Persona


def _utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def build_run_specs(
    *,
    personas: Sequence[Persona],
    applications: Sequence[ApplicationSpec],
    api_url: str,
    persona_model: str,
    max_turns: int,
    min_turns: int,
    goal_context_id: str,
    retries: int = 6,
    retry_delay: float = 2.0,
    max_runs: Optional[int] = None,
) -> List[ExperimentRunSpec]:
    specs: List[ExperimentRunSpec] = []
    for application in applications:
        for persona in personas:
            run_id = "{}__{}".format(
                _slug(application.key),
                _slug(persona.id),
            )
            specs.append(
                ExperimentRunSpec(
                    run_id=run_id,
                    persona_id=persona.id,
                    application_key=application.key,
                    application_type=application.application_type,
                    application_id=application.application_id,
                    application_context=application.application_context,
                    domain=application.domain,
                    api_url=api_url,
                    persona_model=persona_model,
                    max_turns=max_turns,
                    min_turns=min(min_turns, max_turns),
                    goal_context_id=goal_context_id,
                    retries=retries,
                    retry_delay=retry_delay,
                    metadata={"applicationLabel": application.label},
                )
            )
            if max_runs is not None and len(specs) >= max_runs:
                return specs
    return specs


class ExperimentBatchRunner:
    """Run many persona experiments with per-application concurrency limits."""

    def __init__(
        self,
        *,
        applications: Sequence[ApplicationSpec],
        personas: Sequence[Persona],
        run_one: Callable[[ExperimentRunSpec, Persona, Path, ApplicationSpec], ExperimentRunResult],
        now: Callable[[], str] = _utc_now,
    ) -> None:
        self.applications = {app.key: app for app in applications}
        self.personas = {persona.id: persona for persona in personas}
        self.run_one = run_one
        self.now = now
        self._result_lock = threading.Lock()

    def run_batch(
        self,
        specs: Sequence[ExperimentRunSpec],
        *,
        output_dir: Path,
        max_workers: int,
    ) -> Dict[str, object]:
        output_dir.mkdir(parents=True, exist_ok=True)
        runs_dir = output_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        created_at = self.now()
        results_path = output_dir / "results.ndjson"
        manifest = {
            "createdAt": created_at,
            "maxWorkers": max_workers,
            "applications": [app.to_dict() for app in self.applications.values()],
            "runs": [spec.to_dict() for spec in specs],
        }
        _write_json(output_dir / "manifest.json", manifest)

        semaphores = {
            key: threading.BoundedSemaphore(max(1, app.concurrency_limit))
            for key, app in self.applications.items()
        }
        results: List[ExperimentRunResult] = []

        def run_spec(spec: ExperimentRunSpec) -> ExperimentRunResult:
            application = self.applications[spec.application_key]
            persona = self.personas[spec.persona_id]
            with semaphores[application.key]:
                result = self.run_one(
                    spec,
                    persona,
                    runs_dir / spec.run_id,
                    application,
                )
            with self._result_lock:
                results.append(result)
                with results_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
                _write_json(
                    output_dir / "summary.json",
                    _summary(created_at, self.now(), results, total=len(specs)),
                )
            return result

        with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
            futures = [executor.submit(run_spec, spec) for spec in specs]
            for future in as_completed(futures):
                future.result()

        summary = _summary(created_at, self.now(), results, total=len(specs))
        _write_json(output_dir / "summary.json", summary)
        return summary


def _summary(
    created_at: str,
    finished_at: str,
    results: Iterable[ExperimentRunResult],
    *,
    total: int,
) -> Dict[str, object]:
    status_counts: Dict[str, int] = {}
    payload_results: List[Dict[str, object]] = []
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
        payload_results.append(result.to_dict())
    payload_results.sort(key=lambda item: str(item.get("runId") or ""))
    return {
        "createdAt": created_at,
        "finishedAt": finished_at,
        "total": total,
        "completed": len(payload_results),
        "statusCounts": status_counts,
        "results": payload_results,
    }


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_")
