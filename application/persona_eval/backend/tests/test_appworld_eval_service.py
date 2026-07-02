from __future__ import annotations

import time

from backend.service.appworld_eval_service import AppWorldEvalService
from backend.service.appworld_tasks import (
    get_appworld_eval_task,
    list_appworld_eval_tasks,
)
from backend.service.local_appworld_eval import LocalAppWorldEvalRunner
from persona_eval.types import Persona


def _persona(_persona_id: str) -> Persona:
    return Persona(
        id="p1",
        name="Persona One",
        context="Occupation: operations manager\nNeeds a careful assistant.",
    )


def test_appworld_eval_service_returns_trace_in_job_view():
    service = AppWorldEvalService(
        get_persona=_persona,
        get_task=get_appworld_eval_task,
        list_tasks=list_appworld_eval_tasks,
        runner=LocalAppWorldEvalRunner(),
    )

    job_id = service.start(
        persona_id="p1",
        task_id="appworld-demo-personal-admin",
        persona_model="openai/gpt-4o-mini",
        now=lambda: "2026-06-29T00:00:00Z",
    )
    view = _wait_done(service, job_id)

    assert view["applicationType"] == "appworld"
    assert view["appworldResult"]["success"] is True
    assert view["trace"]["events"][0]["actions"][0]["name"] == "appworld_api_call"
    assert view["trace"]["raw"]["trajectory"][0]["action"] == "list_apps"


def _wait_done(service: AppWorldEvalService, job_id: str) -> dict[str, object]:
    deadline = time.time() + 5
    while True:
        view = service.view(job_id)
        assert view is not None
        if view["status"] in {"done", "error"}:
            assert view["status"] == "done", view
            return view
        assert time.time() < deadline
        time.sleep(0.01)
