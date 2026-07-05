"""Bridge iOS CUA `done` submissions to on-host decision.json for verifiers."""

from __future__ import annotations

from typing import Any
from pathlib import Path

from personabench.agents.persona.cua_submission import (
    extract_ios_decision_from_trajectory,
    materialize_json_file,
)

__all__ = [
    "extract_ios_decision_from_trajectory",
    "materialize_ios_decision_file",
]


async def materialize_ios_decision_file(
    environment: Any,
    logs_dir: Path,
    *,
    output_path: str = "/tmp/personabench-ios-photo-access-review/decision.json",
    logger: Any | None = None,
) -> bool:
    """Write decision.json on the simulator host from trajectory `done` tool output."""
    return await materialize_json_file(
        environment,
        logs_dir,
        extractor=extract_ios_decision_from_trajectory,
        output_path=output_path,
        logger=logger,
        log_label="ios submission",
    )
