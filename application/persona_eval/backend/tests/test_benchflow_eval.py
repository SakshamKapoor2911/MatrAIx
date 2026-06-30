from __future__ import annotations

import json
import time
from pathlib import Path

from backend.api.deps import build_state
from backend.service import run_store
from backend.service.benchflow_client import BenchFlowClient, BenchFlowRun
from backend.service.benchflow_persona_eval import BenchFlowPersonaEvalRunner
from backend.service.benchflow_survey_eval import BenchFlowSurveyEvalRunner
from backend.service.benchflow_web_eval import BenchFlowWebEvalRunner
from backend.service.config import persona_eval_runtime
from backend.service.survey_types import SurveyEvalConfig, SurveyInstrument, SurveyQuestion
from backend.service.web_eval_service import WebEvalService
from backend.service.web_types import WebEvalConfig, WebEvalTask
from persona_eval.types import Persona, PersonaEvalConfig


class FakeBenchFlowClient(BenchFlowClient):
    def __init__(self, artifacts):
        self.artifacts = artifacts
        self.requests = []
        self.artifact_requests = []

    def create_run(self, *, task_type, payload):
        self.requests.append({"taskType": task_type, "payload": payload})
        return BenchFlowRun(id=f"bf_{task_type}_1", status="running")

    def wait_for_run(self, run_id):
        return BenchFlowRun(id=run_id, status="succeeded")

    def get_artifact(self, run_id, name):
        self.artifact_requests.append((run_id, name))
        return self.artifacts[name]


def _persona():
    return Persona(
        id="p1",
        name="Persona One",
        context="A careful shopper who values clear tradeoffs.",
    )


def _instrument():
    return SurveyInstrument(
        id="survey1",
        title="Concept survey",
        description="A product concept survey.",
        questions=[
            SurveyQuestion(
                id="fit",
                prompt="This fits my needs.",
                type="likert",
                min_value=1,
                max_value=5,
                construct="need_fit",
            )
        ],
    )


def _web_task(tmp_path):
    return WebEvalTask(
        id="web1",
        title="Web task",
        site_name="Shop",
        site_url="http://shop.test/",
        task_path=tmp_path,
        description="Find and choose one product.",
    )


def test_benchflow_survey_runner_maps_artifact_to_existing_result_shape():
    client = FakeBenchFlowClient(
        {
            "survey_result.json": {
                "instrument": {"id": "survey1", "title": "Concept survey"},
                "answers": [
                    {
                        "questionId": "fit",
                        "value": 4,
                        "rationale": "It is useful but not perfect.",
                        "confidence": 0.8,
                    }
                ],
                "trajectory": [
                    {
                        "timestamp": "2026-06-29T00:00:00Z",
                        "actor": "system",
                        "action": "survey_started",
                        "context": {"instrumentId": "survey1"},
                        "outcome": {},
                    }
                ],
            }
        }
    )
    events = []

    result = BenchFlowSurveyEvalRunner(client=client)(
        _persona(),
        _instrument(),
        SurveyEvalConfig(persona_model="openai/gpt-4o-mini"),
        created_at="2026-06-29T00:00:00Z",
        on_event=events.append,
    )

    assert client.requests[0]["taskType"] == "survey"
    payload = client.requests[0]["payload"]
    assert payload["persona"]["id"] == "p1"
    assert payload["instrument"]["id"] == "survey1"
    assert payload["config"]["mode"] == "benchflow_persona_survey"
    assert "taskPrompt" in payload["prompts"]
    assert "`trajectory` alongside `answers`" in payload["prompts"]["taskPrompt"]
    assert result.answers[0].question_id == "fit"
    assert result.metrics.mean_likert == 4.0
    assert events[0]["type"] == "prompts"
    assert events[-1]["type"] == "done"


def test_benchflow_survey_runner_rejects_invalid_artifact():
    client = FakeBenchFlowClient(
        {
            "survey_result.json": {
                "instrument": {"id": "survey1", "title": "Concept survey"},
                "answers": [
                    {
                        "questionId": "fit",
                        "value": 10,
                        "rationale": "Out of range.",
                    }
                ],
                "trajectory": [
                    {
                        "timestamp": "2026-06-29T00:00:00Z",
                        "actor": "system",
                        "action": "survey_started",
                        "context": {"instrumentId": "survey1"},
                        "outcome": {},
                    }
                ],
            }
        }
    )

    try:
        BenchFlowSurveyEvalRunner(client=client)(
            _persona(),
            _instrument(),
            SurveyEvalConfig(persona_model="openai/gpt-4o-mini"),
            created_at="2026-06-29T00:00:00Z",
        )
    except ValueError as exc:
        assert "must be between" in str(exc)
    else:
        raise AssertionError("invalid survey artifact should fail")


def test_benchflow_web_runner_maps_artifact_and_trace(tmp_path):
    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    (trace_dir / "screenshot_001.webp").write_bytes(b"webp")
    client = FakeBenchFlowClient(
        {
            "ecommerce_interaction.json": {
                "selected_product_id": "desk-001",
                "selected_product_name": "Compact Desk",
                "need_satisfaction": 8,
                "ease_of_use": 7,
                "overall_experience_rating": 8,
                "reason": "The site made product comparison easy for a compact desk.",
            },
            "trace.json": {
                "events": [
                    {
                        "step": 1,
                        "source": "agent",
                        "message": "Compared two desks.",
                        "actions": [{"name": "click", "arguments": {"id": "desk-001"}}],
                        "screenshotFile": "screenshot_001.webp",
                    }
                ],
                "raw": {"benchflowRunId": "bf_web_1"},
            },
            "screenshots_dir": str(trace_dir),
        }
    )

    result = BenchFlowWebEvalRunner(client=client)(
        _persona(),
        _web_task(tmp_path),
        WebEvalConfig(persona_model="openai/gpt-4o-mini"),
        created_at="2026-06-29T00:00:00Z",
    )

    assert client.requests[0]["taskType"] == "web"
    assert client.requests[0]["payload"]["task"]["id"] == "web1"
    assert client.requests[0]["payload"]["config"]["mode"] == "benchflow_persona_web"
    assert ("bf_web_1", "ecommerce_interaction.json") in client.artifact_requests
    assert result.web_result.selected_product_id == "desk-001"
    assert result.web_result.overall_quality == 8
    assert result.to_dict()["webResult"]["overallExperienceRating"] == 8
    assert result.trace.events[0]["actions"][0]["name"] == "click"
    assert result.trace.screenshots_dir == trace_dir


def test_benchflow_persona_eval_runner_maps_chatbot_artifacts():
    client = FakeBenchFlowClient(
        {
            "transcript.json": {
                "turns": [
                    {
                        "turnId": "0",
                        "conversationId": "bf-chat",
                        "backend": "benchflow",
                        "userMessage": "I need a practical movie recommendation.",
                        "assistantMessage": "Try Arrival.",
                        "recommendedItems": [
                            {"itemId": "movie-1", "title": "Arrival"}
                        ],
                        "groundedItems": [
                            {"itemId": "movie-1", "title": "Arrival"}
                        ],
                    }
                ]
            },
            "application_result.json": {
                "groundedItems": [{"itemId": "movie-1", "title": "Arrival"}],
                "turnsToRecommendation": 1,
            },
            "user_feedback.json": {
                "overallRating": 8,
                "constraintSatisfaction": 4,
                "preferenceSatisfaction": 5,
            },
        }
    )

    session = type("Session", (), {"turns": []})()
    result = BenchFlowPersonaEvalRunner(client=client)(
        session,
        _persona(),
        "A movie recommendation chatbot.",
        PersonaEvalConfig(domain="movie", max_turns=3, persona_model="openai/gpt-4o-mini"),
        None,
        created_at="2026-06-29T00:00:00Z",
    )

    assert client.requests[0]["taskType"] == "chatbot"
    assert client.requests[0]["payload"]["maxTurns"] == 3
    assert result.metric_scores["numTurns"] == 1
    assert result.questionnaire["overallRating"] == 8
    assert session.turns[0]["backend"] == "benchflow"


def test_benchflow_persona_eval_accepts_application_scorer_feedback_shape():
    client = FakeBenchFlowClient(
        {
            "transcript.json": {
                "sessionId": "bf-chat",
                "turns": [
                    {
                        "turnId": "0",
                        "userMessage": "I want a thoughtful movie.",
                        "assistantMessage": "Arrival fits that need.",
                        "recommendedItems": [
                            {"itemId": "movie-1", "title": "Arrival"}
                        ],
                    }
                ],
            },
            "application_result.json": {
                "groundedItems": [{"itemId": "movie-1", "title": "Arrival"}],
                "turnsToRecommendation": 1,
            },
            "user_feedback.json": {
                "productNeedSatisfaction": 4,
                "personalPreferenceSatisfaction": 5,
                "overallExperienceRating": 9,
                "reason": "The recommendation matched the persona's taste.",
                "askedUsefulClarificationQuestions": True,
            },
        }
    )

    result = BenchFlowPersonaEvalRunner(client=client)(
        type("Session", (), {"turns": []})(),
        _persona(),
        "A movie recommendation chatbot.",
        PersonaEvalConfig(domain="movie", max_turns=3),
        None,
        created_at="2026-06-29T00:00:00Z",
    )

    questionnaire = result.to_dict()["questionnaire"]
    assert questionnaire["constraintSatisfaction"] == 4
    assert questionnaire["preferenceSatisfaction"] == 5
    assert questionnaire["overallRating"] == 9
    assert questionnaire["askedUsefulClarifyingQuestions"] is True
    assert questionnaire["ratingReason"] == "The recommendation matched the persona's taste."


def test_benchflow_persona_eval_preserves_recommendations_for_message_transcript():
    client = FakeBenchFlowClient(
        {
            "transcript.json": {
                "sessionId": "bf-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": "I need a practical movie recommendation.",
                    },
                    {"role": "assistant", "content": "Try Arrival."},
                ],
            },
            "application_result.json": {
                "groundedItems": [{"itemId": "movie-1", "title": "Arrival"}],
                "turnsToRecommendation": 1,
            },
        }
    )

    session = type("Session", (), {"turns": []})()
    result = BenchFlowPersonaEvalRunner(client=client)(
        session,
        _persona(),
        "A movie recommendation chatbot.",
        PersonaEvalConfig(domain="movie", max_turns=3),
        None,
        created_at="2026-06-29T00:00:00Z",
    )

    payload = result.to_dict()
    assert payload["recommendedItemIds"]["final"] == ["movie-1"]
    assert payload["transcript"][-1]["groundedItems"] == []
    assert payload["recommendedItems"][0]["itemId"] == "movie-1"
    assert session.turns[-1]["groundedItems"] == []


def test_runtime_env_selects_benchflow_services(monkeypatch, tmp_path):
    monkeypatch.setenv("MATRIX_PERSONA_EVAL_RUNTIME", "benchflow")
    monkeypatch.setenv("BENCHFLOW_API_URL", "http://benchflow.test")
    assert persona_eval_runtime() == "benchflow"

    state = build_state(str(tmp_path / "missing-items.jsonl"))

    assert state.persona_eval._runner.__class__.__name__ == "BenchFlowPersonaEvalRunner"
    assert state.survey_eval._runner.__class__.__name__ == "BenchFlowSurveyEvalRunner"
    assert state.web_eval._runner.__class__.__name__ == "BenchFlowWebEvalRunner"


def test_benchflow_client_allows_scalar_json_artifacts(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps("/tmp/benchflow/screens").encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response())

    client = BenchFlowClient(base_url="http://benchflow.test")

    assert client.get_artifact("bf_web_1", "screenshots_dir") == "/tmp/benchflow/screens"


def test_benchflow_web_service_persists_webp_screenshots(tmp_path):
    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    (trace_dir / "screenshot_001.webp").write_bytes(b"webp")
    client = FakeBenchFlowClient(
        {
            "web_result.json": {
                "selected_product_id": "desk-001",
                "selected_product_name": "Compact Desk",
                "overall_experience_rating": 8,
            },
            "trace.json": {
                "events": [
                    {
                        "step": 1,
                        "source": "agent",
                        "message": "Compared two desks.",
                        "actions": [{"name": "click", "arguments": {"id": "desk-001"}}],
                        "screenshotFile": "screenshot_001.webp",
                    }
                ]
            },
            "screenshots_dir": str(trace_dir),
        }
    )
    service = WebEvalService(
        get_persona=lambda _persona_id: _persona(),
        get_task=lambda _task_id: _web_task(tmp_path),
        list_tasks=lambda: [_web_task(tmp_path)],
        runner=BenchFlowWebEvalRunner(client=client),
        runs_dir=tmp_path / "runs",
    )

    job_id = service.start(
        persona_id="p1",
        task_id="web1",
        persona_model="openai/gpt-4o-mini",
        now=lambda: "2026-06-29T00:00:00Z",
    )
    deadline = time.time() + 5
    view = service.view(job_id)
    while view is not None and view["status"] not in {"done", "error"}:
        assert time.time() < deadline
        time.sleep(0.01)
        view = service.view(job_id)

    assert view is not None
    assert view["status"] == "done"
    record = run_store.load_run(tmp_path / "runs", job_id)
    assert record is not None
    assert record["webTrace"]["events"][0]["screenshotFile"] == "screenshot_001.webp"
    service._progress.clear()
    assert service.screenshot_path(job_id, "screenshot_001.webp").is_file()


def test_benchflow_web_service_preserves_remote_screenshot_urls(tmp_path):
    client = FakeBenchFlowClient(
        {
            "web_result.json": {
                "selected_product_id": "desk-001",
                "selected_product_name": "Compact Desk",
                "overall_experience_rating": 8,
            },
            "trace.json": {
                "events": [
                    {
                        "step": 1,
                        "source": "agent",
                        "message": "Compared two desks.",
                        "screenshotFile": "screenshot_001.webp",
                        "screenshotUrl": "https://benchflow.example/runs/1/screenshot.webp",
                    }
                ]
            },
        }
    )
    service = WebEvalService(
        get_persona=lambda _persona_id: _persona(),
        get_task=lambda _task_id: _web_task(tmp_path),
        list_tasks=lambda: [_web_task(tmp_path)],
        runner=BenchFlowWebEvalRunner(client=client),
        runs_dir=tmp_path / "runs",
    )

    job_id = service.start(
        persona_id="p1",
        task_id="web1",
        persona_model="openai/gpt-4o-mini",
        now=lambda: "2026-06-29T00:00:00Z",
    )
    deadline = time.time() + 5
    view = service.view(job_id)
    while view is not None and view["status"] not in {"done", "error"}:
        assert time.time() < deadline
        time.sleep(0.01)
        view = service.view(job_id)

    assert view is not None
    assert view["status"] == "done"
    assert (
        view["trace"]["events"][0]["screenshotUrl"]
        == "https://benchflow.example/runs/1/screenshot.webp"
    )


def test_benchflow_web_service_persists_webarena_trajectory(tmp_path):
    trace = {
        "events": [
            {
                "step": 1,
                "source": "agent",
                "message": "Navigated to the product listing.",
                "actions": [
                    {
                        "name": "computer_action",
                        "arguments": {"action": "goto", "url": "http://shop.test/"},
                    }
                ],
                "screenshotUrl": "https://benchflow.example/runs/1/step-1.webp",
            },
            {
                "step": 2,
                "source": "agent",
                "message": "Selected the compact desk.",
                "actions": [
                    {
                        "name": "computer_action",
                        "arguments": {"action": "click", "selector": "#desk-001"},
                    }
                ],
                "screenshotUrl": "https://benchflow.example/runs/1/step-2.webp",
            },
        ],
        "raw": {
            "benchflowRunId": "bf_web_1",
            "trajectory": [
                {"observation": "home", "action": "goto"},
                {"observation": "desk detail", "action": "click"},
            ],
        },
    }
    client = FakeBenchFlowClient(
        {
            "web_result.json": {
                "selected_product_id": "desk-001",
                "selected_product_name": "Compact Desk",
                "overall_experience_rating": 8,
            },
            "trace.json": trace,
        }
    )
    service = WebEvalService(
        get_persona=lambda _persona_id: _persona(),
        get_task=lambda _task_id: _web_task(tmp_path),
        list_tasks=lambda: [_web_task(tmp_path)],
        runner=BenchFlowWebEvalRunner(client=client),
        runs_dir=tmp_path / "runs",
    )

    job_id = service.start(
        persona_id="p1",
        task_id="web1",
        persona_model="openai/gpt-4o-mini",
        now=lambda: "2026-06-29T00:00:00Z",
    )
    deadline = time.time() + 5
    view = service.view(job_id)
    while view is not None and view["status"] not in {"done", "error"}:
        assert time.time() < deadline
        time.sleep(0.01)
        view = service.view(job_id)

    assert view is not None
    assert view["status"] == "done"
    assert (
        view["trace"]["events"][1]["actions"][0]["arguments"]["selector"]
        == "#desk-001"
    )
    assert (
        view["trace"]["events"][1]["screenshotUrl"]
        == "https://benchflow.example/runs/1/step-2.webp"
    )
    assert view["trace"]["raw"]["trajectory"][0]["observation"] == "home"

    record = run_store.load_run(tmp_path / "runs", job_id)
    assert record is not None
    assert record["webTrace"]["events"] == view["trace"]["events"]
    assert record["webTrace"]["raw"]["trajectory"][1]["action"] == "click"


def test_benchflow_web_service_does_not_fabricate_local_url_for_remote_path(tmp_path):
    client = FakeBenchFlowClient(
        {
            "web_result.json": {
                "selected_product_id": "desk-001",
                "selected_product_name": "Compact Desk",
                "overall_experience_rating": 8,
            },
            "trace.json": {
                "events": [
                    {
                        "step": 1,
                        "source": "agent",
                        "message": "Compared two desks.",
                        "screenshotFile": "screenshot_001.webp",
                    }
                ]
            },
            "screenshots_dir": "/benchflow/remote/run",
        }
    )
    service = WebEvalService(
        get_persona=lambda _persona_id: _persona(),
        get_task=lambda _task_id: _web_task(tmp_path),
        list_tasks=lambda: [_web_task(tmp_path)],
        runner=BenchFlowWebEvalRunner(client=client),
        runs_dir=tmp_path / "runs",
    )

    job_id = service.start(
        persona_id="p1",
        task_id="web1",
        persona_model="openai/gpt-4o-mini",
        now=lambda: "2026-06-29T00:00:00Z",
    )
    deadline = time.time() + 5
    view = service.view(job_id)
    while view is not None and view["status"] not in {"done", "error"}:
        assert time.time() < deadline
        time.sleep(0.01)
        view = service.view(job_id)

    assert view is not None
    assert view["status"] == "done"
    assert "screenshotUrl" not in view["trace"]["events"][0]
