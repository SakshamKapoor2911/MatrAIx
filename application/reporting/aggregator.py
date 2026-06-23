"""Aggregate persona trial results across a Harbor job directory.

TODO: implement after persona agents write persona_meta.json and
application tasks use rewardkit verifiers.
"""

from __future__ import annotations

from pathlib import Path


def aggregate_job(job_dir: Path) -> dict:
    """Placeholder: scan job_dir and return summary dict."""
    raise NotImplementedError(
        "MatrAIx reporting is not implemented yet. "
        f"Would aggregate results under {job_dir}"
    )
