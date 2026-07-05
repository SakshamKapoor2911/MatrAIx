"""Tests for the tool-driven user simulator and runner integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from persona_eval.task_content_bundle import TaskContentBundle
from persona_eval.types import Persona, PersonaEvalConfig, Questionnaire
from persona_eval.user_sim.runner import run_persona_eval
from persona_eval.user_sim.session import UserSimSession
from persona_eval.user_sim.tool_client import FakeToolStepClient
from persona_eval.user_sim.tools import ToolCall, parse_tool_calls


class FakeSession:
    def __init__(self, turns):
        self._turns = list(turns)
        self.calls = []
        self._session_id = "sess-user-sim"

    @property
    def session_id(self) -> str:
        return self._session_id

    def run_turn_sync(self, message):
        self.calls.append(message)
        return self._turns.pop(0)


class FakeSelfReportClient:
    def complete_json(self, system, user):
        return {
            "needConstraintSatisfaction": "yes",
            "personalPreferenceSatisfaction": "yes",
            "overallExperienceRating": 8,
            "reason": "Solid chat",
            "askedUsefulClarificationQuestions": True,
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
    session = UserSimSession(client, _persona())
    action = session.opening_action()
    assert action.message == "Hi, need a movie recommendation"
    assert len(client.calls) == 1
    assert client.calls[0][0]["role"] == "system"


def test_run_persona_eval_tool_loop(monkeypatch):
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
    repo = Path(__file__).resolve().parents[5]
    result = run_persona_eval(
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
    assert result.metric_scores.num_turns == 2
    assert result.transcript[-1].persona_exposure[0]["value"] == [
        {"itemId": "movie-1", "title": "Past Lives"}
    ]
    assert isinstance(result.questionnaire, Questionnaire)
    assert result.prompts["taskPrompt"]
    assert len(client.calls) >= 3
    second_step = client.calls[1]
    assert second_step[-1]["role"] == "user"
    assert 'RecAI Answer:\n"""What genre?"""' in second_step[-1]["content"]
    third_step = client.calls[2]
    assert "Visible structured details" in third_step[-1]["content"]
    assert "Recommended items: Past Lives (movie-1)" in third_step[-1]["content"]


def test_prompt_bundle_separates_persona_and_task():
    from persona_eval.user_sim.prompt import (
        assemble_report_system_prompt,
        prompt_bundle,
    )

    persona = Persona(id="p1", name="Test", source="", context="Bio line")
    task_bundle = TaskContentBundle(
        instruction_markdown="Stay in character and judge the chatbot honestly.",
        context_markdown="The chatbot helps a user discover products.",
        output_schema_markdown="Write transcript.json and user_feedback.json.",
    )
    bundle = prompt_bundle(
        persona,
        task_bundle=task_bundle,
        task_prompt="Kickoff instruction.",
    )
    report_prompt = assemble_report_system_prompt(
        persona,
        task_bundle=task_bundle,
    )
    assert "Progressive disclosure" not in bundle["personaPrompt"]
    assert "## Persona" in bundle["personaPrompt"]
    assert "## Task instruction" not in bundle["personaPrompt"]
    assert "## Task instruction" in bundle["taskPrompt"]
    assert "## Task context" in bundle["taskPrompt"]
    assert "Kickoff instruction." in bundle["taskPrompt"]
    assert "Progressive disclosure" in bundle["harborPrompt"]
    assert bundle["harborPrompt"].index("## Persona") < bundle["harborPrompt"].index("Progressive disclosure")
    assert "Keep messages short and natural (usually 1-3 sentences)." in bundle["harborPrompt"]
    assert "Prefer plainspoken end-user language" in bundle["harborPrompt"]
    assert "## Task instruction" in bundle["harborPrompt"]
    assert "## Task context" in bundle["harborPrompt"]
    assert "## Task instruction" in report_prompt
    assert "## Task context" in report_prompt
    assert "## Output schema" not in report_prompt


def test_public_runner_delegates_to_user_sim(monkeypatch):
    from persona_eval.runner import run_persona_eval

    sentinel = object()
    captured = {}

    def fake_run(session, persona, sut_description, config, *, created_at, on_event, task_path, persona_yaml_path, repo_root):
        captured["session"] = session
        captured["persona"] = persona
        captured["sut_description"] = sut_description
        captured["config"] = config
        captured["created_at"] = created_at
        captured["task_path"] = task_path
        captured["persona_yaml_path"] = persona_yaml_path
        captured["repo_root"] = repo_root
        return sentinel

    monkeypatch.setattr("persona_eval.user_sim.runner.run_persona_eval", fake_run)
    session = FakeSession([{"assistantMessage": "Hi", "recommendedItems": []}])
    config = PersonaEvalConfig(domain="movie", max_turns=3)
    result = run_persona_eval(
        session,
        _persona(),
        "desc",
        config,
        created_at="t",
        task_path="application/tasks/recommender-agent_chat_api",
        persona_yaml_path="persona.yaml",
        repo_root=Path("/tmp/demo-repo"),
    )
    assert result is sentinel
    assert captured["session"] is session
    assert captured["config"] is config
    assert captured["task_path"] == "application/tasks/recommender-agent_chat_api"
