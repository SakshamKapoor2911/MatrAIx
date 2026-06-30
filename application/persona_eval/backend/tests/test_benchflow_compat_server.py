from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.service.benchflow_client import BenchFlowClient
from backend.service.benchflow_compat_server import create_app
from backend.service.benchflow_web_eval import BenchFlowWebEvalRunner
from backend.service.web_types import WebEvalConfig, WebEvalTask
from persona_eval.types import Persona


def _web_payload() -> dict[str, object]:
    task = WebEvalTask(
        id="web-ecommerce-platform_product-discovery",
        title="Ecommerce product discovery",
        site_name="Northstar Home Goods",
        site_url="http://ecommerce-web:8000/",
        task_path=Path("application/tasks/web-ecommerce-platform_product-discovery"),
        description="Browse the site and choose one product.",
        output_artifact="ecommerce_interaction.json",
    )
    persona = Persona(
        id="p1",
        name="Persona One",
        context="A careful shopper who values clear tradeoffs.",
    )
    return {
        "persona": persona.to_dict(),
        "task": task.to_dict(),
        "config": WebEvalConfig(persona_model="openai/gpt-4o-mini").to_dict(),
        "prompts": {"taskPrompt": "Find one product."},
    }


def test_compat_server_mock_web_run_exposes_webarena_artifacts(tmp_path):
    app = create_app(runs_dir=tmp_path)
    client = TestClient(app)

    created = client.post(
        "/v1/runs",
        json={"taskType": "web", "payload": _web_payload()},
    )
    assert created.status_code == 200
    run_id = created.json()["id"]

    status = _wait_terminal(client, run_id)
    assert status["status"] == "succeeded"

    result = client.get(f"/v1/runs/{run_id}/artifacts/ecommerce_interaction.json")
    assert result.status_code == 200
    assert result.json()["selected_product_id"] == "benchflow-demo-product"

    trace = client.get(f"/v1/runs/{run_id}/artifacts/trace.json")
    assert trace.status_code == 200
    assert trace.json()["events"][1]["actions"][0]["arguments"]["selector"]
    assert trace.json()["raw"]["trajectory"][0]["action"] == "goto"
    screenshot_url = trace.json()["events"][0]["screenshotUrl"]
    assert screenshot_url.startswith("http://127.0.0.1:9000")
    screenshot_path = "/" + screenshot_url.split("://", 1)[1].split("/", 1)[1]
    screenshot = client.get(screenshot_path)
    assert screenshot.status_code == 200
    assert screenshot.headers["content-type"].startswith("image/")


def test_compat_server_can_drive_benchflow_web_runner_without_auth(tmp_path):
    app = create_app(runs_dir=tmp_path)
    http = TestClient(app)

    class InProcessBenchFlowClient(BenchFlowClient):
        def _request_json(self, method, path, *, body=None):
            if method == "POST":
                response = http.post(path, json=body)
            else:
                response = http.get(path)
            response.raise_for_status()
            return response.json()

    task = WebEvalTask(
        id="web-ecommerce-platform_product-discovery",
        title="Ecommerce product discovery",
        site_name="Northstar Home Goods",
        site_url="http://ecommerce-web:8000/",
        task_path=Path("application/tasks/web-ecommerce-platform_product-discovery"),
        description="Browse the site and choose one product.",
        output_artifact="ecommerce_interaction.json",
    )
    result = BenchFlowWebEvalRunner(client=InProcessBenchFlowClient())(
        Persona(
            id="p1",
            name="Persona One",
            context="A careful shopper who values clear tradeoffs.",
        ),
        task,
        WebEvalConfig(persona_model="openai/gpt-4o-mini"),
        created_at="2026-06-29T00:00:00Z",
    )

    assert result.web_result.selected_product_id == "benchflow-demo-product"
    assert result.trace.raw["trajectory"][1]["action"] == "click"
    assert result.trace.events[0]["screenshotUrl"].startswith("http://127.0.0.1:9000")


def _wait_terminal(client: TestClient, run_id: str) -> dict[str, object]:
    deadline = time.time() + 5
    while True:
        response = client.get(f"/v1/runs/{run_id}")
        response.raise_for_status()
        payload = response.json()
        if payload["status"] in {"succeeded", "failed"}:
            return payload
        assert time.time() < deadline
        time.sleep(0.01)
