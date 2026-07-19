from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from harbor.viewer.server import create_app


def _write_trial(tmp_path: Path) -> None:
    trial_dir = tmp_path / "demo-job" / "trial-a"
    trial_dir.mkdir(parents=True)


@pytest.mark.unit
def test_trial_serves_image_up_to_10mb(tmp_path: Path) -> None:
    _write_trial(tmp_path)
    image_path = tmp_path / "demo-job" / "trial-a" / "images" / "step_001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"x" * (1024 * 1024 + 300 * 1024))

    client = TestClient(create_app(tmp_path))
    response = client.get("/api/jobs/demo-job/trials/trial-a/files/images/step_001.png")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")


@pytest.mark.unit
def test_trial_rejects_text_file_over_1mb(tmp_path: Path) -> None:
    _write_trial(tmp_path)
    text_path = tmp_path / "demo-job" / "trial-a" / "agent.log"
    text_path.write_text("x" * (1024 * 1024 + 1))

    client = TestClient(create_app(tmp_path))
    response = client.get("/api/jobs/demo-job/trials/trial-a/files/agent.log")

    assert response.status_code == 413
    assert "max 1.0 MB" in response.json()["detail"]
