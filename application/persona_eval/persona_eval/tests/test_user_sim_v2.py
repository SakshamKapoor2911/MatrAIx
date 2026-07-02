"""Tests for UserSim v2 tool loop and runner integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from persona_eval.goal_contexts import get_goal_context
from persona_eval.types import Persona, PersonaEvalConfig, Questionnaire
from persona_eval.user_sim.runner import run_persona_eval_v2
from persona_eval.user_sim.scenario import load_user_scenario, resolve_user_scenario
from persona_eval.user_sim.session import UserSimSession
from persona_eval.user_sim.tool_client import FakeToolStepClient
from persona_eval.user_sim.tools import ToolCall, parse_tool_calls


class FakeSession:
    def __init__(self, turns):
        self._turns = list(turns)
        self.calls = []
        self._session_id = "sess-v2"

    @property
    def session_id(self) -> str:
        return self._session_id

    def run_turn_sync(self, message):
        self.calls.append(message)
        return self._turns.pop(0)


class FakeSelfReportClient:
    def complete_json(self, system, user):
        return {
            "constraintSatisfaction": 4,
            "preferenceSatisfaction": 5,
            "overallRating": 8,
            "ratingReason": "Solid chat",
            "askedUsefulClarifyingQuestions": True,
            "clarifyingNotes": "Asked about genre",
        }


def _persona():
    return Persona(
        id="p1",
        name="Alex",
        summary="Movie fan",
        context="Name: Alex\nLikes thoughtful dramas.",
    )


def test_parse_tool_calls_send_and_end():
    action = parse_tool_calls(
        [
            ToolCall("send_message", {"message": "Looking for something warm"}),
            ToolCall("end_conversation", {"reason": "satisfied", "note": "found it"}),
        ]
    )
    assert action.message == "Looking for something warm"
    assert action.end_reason == "satisfied"
    assert action.decision == "satisfied"


def test_user_sim_session_opening_action():
    client = FakeToolStepClient(
        [[ToolCall("send_message", {"message": "Hi, need a movie recommendation"})]]
    )
    scenario = resolve_user_scenario(
        goal_context=get_goal_context("scenario_default"),
        domain="movie",
        sut_description="Movie recommender",
    )
    session = UserSimSession(client, _persona(), scenario)
    action = session.opening_action()
    assert action.message == "Hi, need a movie recommendation"
    assert len(client.calls) == 1
    assert client.calls[0][0]["role"] == "system"


def test_run_persona_eval_v2_tool_loop(monkeypatch):
    monkeypatch.setattr(
        "persona_eval.user_sim.runner.build_json_client",
        lambda *_args, **_kwargs: FakeSelfReportClient(),
    )
    session = FakeSession(
        [
            {"assistantMessage": "What genre?", "recommendedItems": []},
            {
                "assistantMessage": "Try Past Lives",
                "recommendedItems": [{"itemId": "movie-1", "title": "Past Lives"}],
            },
        ]
    )
    client = FakeToolStepClient(
        [
            [ToolCall("send_message", {"message": "Hi, looking for a warm drama"})],
            [ToolCall("send_message", {"message": "Something character-driven"})],
            [ToolCall("end_conversation", {"reason": "satisfied"})],
        ]
    )
    monkeypatch.setattr(
        "persona_eval.user_sim.runner.build_tool_step_client",
        lambda *_args, **_kwargs: client,
    )
    repo = Path(__file__).resolve().parents[4]
    result = run_persona_eval_v2(
        session,
        _persona(),
        "Movie recommender",
        PersonaEvalConfig(domain="movie", max_turns=5),
        created_at="2026-06-30T00:00:00Z",
        task_path="application/tasks/recommender-agent_chat_api",
        repo_root=repo,
    )
    assert len(result.transcript) == 2
    assert result.transcript[0].user_message == "Hi, looking for a warm drama"
    assert result.transcript[-1].decision == "satisfied"
    assert result.metric_scores.turns_to_recommendation == 2
    assert isinstance(result.questionnaire, Questionnaire)
    assert result.prompts["taskPrompt"]


def test_load_user_scenario_from_task(tmp_path):
    task_dir = tmp_path / "application" / "tasks" / "demo-chat"
    task_dir.mkdir(parents=True)
    (task_dir / "user_scenario.yaml").write_text(
        "identity: Demo user\ngoal: Find help\nstyle: Brief\n",
        encoding="utf-8",
    )
    scenario = load_user_scenario(task_dir / "user_scenario.yaml")
    assert scenario.identity == "Demo user"
    assert scenario.goal == "Find help"


def test_runner_uses_t0_when_v2_disabled(monkeypatch):
    from persona_eval.runner import run_persona_eval
    from persona_eval.types import SimulatorTurn

    monkeypatch.setenv("MATRIX_USER_SIM_V2", "0")

    class T0Simulator:
        def kickoff(self, persona, sut):
            return "hello"

        def respond(self, persona, sut, pairs, last, items):
            return SimulatorTurn("thanks", "satisfied")

        def final_feedback(self, persona, sut, transcript, final_items):
            return Questionnaire(4, "", 4, "", 8, "", True, "")

    session = FakeSession([{"assistantMessage": "Hi", "recommendedItems": []}])
    result = run_persona_eval(
        session,
        _persona(),
        "desc",
        PersonaEvalConfig(domain="movie", max_turns=3),
        T0Simulator(),
        created_at="t",
    )
    assert len(result.transcript) == 1
    assert result.transcript[0].user_message == "hello"
