"""Survey and web evals persist as Runs (so all three kinds show in Runs)."""

from __future__ import annotations

import time

from backend.service import run_store
from backend.service.local_survey_eval import LocalSurveyEvalRunner
from backend.service.local_web_eval import LocalWebEvalRunner
from backend.service.survey_eval_service import SurveyEvalService
from backend.service.survey_types import SurveyInstrument, SurveyQuestion
from backend.service.web_eval_service import WebEvalService
from backend.service.web_types import WebEvalTask
from persona_eval.types import Persona


class _FakeJSONClient:
    def __init__(self, payload):
        self.payload = payload

    def complete_json(self, system, user):
        return self.payload


def _persona():
    return Persona(id="p1", name="Marco", context="A budget-conscious user.", source="Nemotron")


def _instrument():
    return SurveyInstrument(
        id="survey1",
        title="Feature Survey",
        description="A survey about a concrete feature.",
        questions=[SurveyQuestion(id="fit", prompt="This fits me.")],
    )


def _wait_done(service, job_id, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        view = service.view(job_id)
        if view and view["status"] in ("done", "error"):
            return view
        time.sleep(0.01)
    return service.view(job_id)


def test_survey_eval_persists_a_run(tmp_path, monkeypatch):
    client = _FakeJSONClient(
        {"answers": [{"questionId": "fit", "value": 5, "rationale": "Fits.", "confidence": 0.9}]}
    )
    monkeypatch.setattr("backend.service.local_survey_eval.build_json_client", lambda model: client)
    instrument = _instrument()
    service = SurveyEvalService(
        get_persona=lambda pid: _persona(),
        get_instrument=lambda iid: instrument,
        list_instruments=lambda: [instrument],
        runner=LocalSurveyEvalRunner(),
        runs_dir=tmp_path,
    )

    job_id = service.start(
        persona_id="p1", instrument_id="survey1", persona_model="openai/gpt-4o-mini", now=lambda: "2026-06-27T00:00:00Z"
    )
    view = _wait_done(service, job_id)
    assert view["status"] == "done"

    record = run_store.load_run(tmp_path, job_id)
    assert record is not None
    assert record["applicationType"] == "survey"
    assert record["persona"]["name"] == "Marco"
    assert record["surveyResult"]["instrument"]["id"] == "survey1"
    assert record["surveyResult"]["answers"][0]["questionId"] == "fit"

    # And it surfaces in the shared Runs list with a survey summary.
    summaries = [run_store.summarize_record(r) for r in run_store.iter_run_records(tmp_path)]
    assert any(s["id"] == job_id and s["applicationType"] == "survey" for s in summaries)


def test_web_eval_persists_a_run_and_durable_screenshots(tmp_path, monkeypatch):
    client = _FakeJSONClient(
        {
            "goal": "Buy a lamp.",
            "steps": [{"message": "Looked at lamps.", "actions": [{"name": "search", "arguments": {}}]}],
            "selected_product_id": "lamp-001",
            "selected_product_name": "Desk Lamp",
            "need_satisfaction": 8,
            "ease_of_use": 7,
            "information_quality": 8,
            "overall_quality": 8,
            "reason": "Good lamp.",
        }
    )
    monkeypatch.setattr("backend.service.local_web_eval.build_json_client", lambda model: client)
    task = WebEvalTask(
        id="web1",
        title="Shop task",
        site_name="Shop",
        site_url="http://local.test/",
        task_path=tmp_path,
        description="Find and choose a product.",
    )
    service = WebEvalService(
        get_persona=lambda pid: _persona(),
        get_task=lambda tid: task,
        list_tasks=lambda: [task],
        runner=LocalWebEvalRunner(),
        runs_dir=tmp_path,
    )

    job_id = service.start(
        persona_id="p1", task_id="web1", persona_model="openai/gpt-4o-mini", now=lambda: "2026-06-27T00:00:00Z"
    )
    view = _wait_done(service, job_id)
    assert view["status"] == "done"

    record = run_store.load_run(tmp_path, job_id)
    assert record is not None
    assert record["applicationType"] == "web"
    assert record["persona"]["name"] == "Marco"
    assert record["webResult"]["selectedProductId"] == "lamp-001"
    assert record["webResult"]["overallExperienceRating"] == 8
    assert record["webTrace"]["events"]  # trace persisted

    # Screenshots are copied to a durable per-run dir and served via the fallback
    # even after the in-memory job is gone (i.e. after a restart).
    first_file = record["webTrace"]["events"][0]["screenshotFile"]
    service._progress.clear()  # simulate a restart: no in-memory job state
    path = service.screenshot_path(job_id, first_file)
    assert path.is_file()
