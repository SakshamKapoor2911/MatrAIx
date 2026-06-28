from pathlib import Path

from fastapi.testclient import TestClient

import harbor.viewer.server as viewer_server
from harbor.viewer.server import create_app


def test_persona_synthesis_info_reports_full_catalog(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))

    response = client.get("/api/persona-synthesis")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "1.0"
    assert payload["dimension_count"] == 1339
    assert payload["constraint_count"] == 115
    assert (
        payload["constraint_validation"]["applicable_to_generated_dimensions_count"]
        == 115
    )


def test_persona_synthesis_api_generates_dataset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    generated_root = tmp_path / "_generated"
    monkeypatch.setattr(
        viewer_server,
        "_persona_generated_datasets_dir",
        lambda: generated_root,
    )
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/api/persona-synthesis",
        json={
            "count": 1,
            "seed": 5,
            "output_name": "api-smoke",
            "max_attempts_per_persona": 1000,
            "preview_dimensions": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["dimension_count"] == 1339
    assert payload["sample_dimension_total"] == 1339
    assert len(payload["sample_dimensions"]) == 5
    assert Path(payload["manifest_path"]).exists()


def test_persona_synthesis_rejects_unsafe_output_name(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/api/persona-synthesis",
        json={"count": 1, "output_name": "../outside"},
    )

    assert response.status_code == 400
