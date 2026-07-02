"""PersonaEval computer-use (CUA) task types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CuaEvalTask:
    id: str
    title: str
    platform: str
    description: str
    task_path: str
    output_artifact: str = "decision.json"
    cua_submission_profile: Optional[str] = None
    environment_label: str = "Docker · persona-computer-1"
    cua_backend: str = "docker"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "platform": self.platform,
            "description": self.description,
            "taskPath": self.task_path,
            "outputArtifact": self.output_artifact,
            "cuaSubmissionProfile": self.cua_submission_profile,
            "environmentLabel": self.environment_label,
            "cuaBackend": self.cua_backend,
        }
