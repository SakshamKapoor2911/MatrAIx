from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ExperimentRunSpec:
    """Concrete persona x application run scheduled by a batch."""

    run_id: str
    persona_id: str
    application_key: str
    application_type: str
    application_id: str
    application_context: str
    domain: str
    api_url: str
    persona_model: str
    max_turns: int = 3
    min_turns: int = 3
    goal_context_id: str = "scenario_default"
    retries: int = 6
    retry_delay: float = 2.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runId": self.run_id,
            "personaId": self.persona_id,
            "applicationKey": self.application_key,
            "applicationType": self.application_type,
            "applicationId": self.application_id,
            "applicationContext": self.application_context,
            "domain": self.domain,
            "apiUrl": self.api_url,
            "personaModel": self.persona_model,
            "maxTurns": self.max_turns,
            "minTurns": self.min_turns,
            "goalContextId": self.goal_context_id,
            "retries": self.retries,
            "retryDelay": self.retry_delay,
            "metadata": dict(self.metadata),
        }


@dataclass
class ExperimentRunResult:
    """Final status for one experiment run."""

    run_id: str
    status: str
    output_dir: Path
    started_at: str
    finished_at: str
    artifacts: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runId": self.run_id,
            "status": self.status,
            "outputDir": str(self.output_dir),
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "artifacts": list(self.artifacts),
            "error": self.error,
            "metadata": dict(self.metadata),
        }
