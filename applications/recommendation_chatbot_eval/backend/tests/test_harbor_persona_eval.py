import json
from pathlib import Path

import pytest
import yaml

from backend.service.harbor_persona_eval import (
    HarborPersonaEvalRunner,
    build_recommender_simulation_prompt,
    build_result_from_harbor_artifacts,
    resolve_repo_root,
    write_harbor_persona_yaml,
)
from persona_eval.types import Persona, PersonaEvalConfig


def test_build_result_from_harbor_artifacts_maps_transcript_feedback_and_metrics(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "transcript.json").write_text(json.dumps({
        "sessionId": "ses_123",
        "domain": "movie",
        "messages": [
            {"role": "user", "content": "I want something tense but not graphic."},
            {"role": "assistant", "content": "Do you prefer mainstream or lesser-known films?"},
            {"role": "user", "content": "Lesser-known is fine if it fits."},
            {"role": "assistant", "content": "Try Movie A."},
        ],
        "turns": [
            {
                "turnId": "0",
                "conversationId": "ses_123",
                "backend": "interecagent",
                "userMessage": "I want something tense but not graphic.",
                "assistantMessage": "Do you prefer mainstream or lesser-known films?",
                "plan": [],
                "recommendedItems": [],
                "nativeRaw": None,
                "rawToolOutputs": None,
            },
            {
                "turnId": "1",
                "conversationId": "ses_123",
                "backend": "interecagent",
                "userMessage": "Lesser-known is fine if it fits.",
                "assistantMessage": "Try Movie A.",
                "plan": [],
                "recommendedItems": [{"itemId": "42", "title": "Movie A", "rank": 1}],
                "nativeRaw": None,
                "rawToolOutputs": None,
            },
        ],
    }), encoding="utf-8")
    (output_dir / "recommendation_result.json").write_text(json.dumps({
        "sessionId": "ses_123",
        "domain": "movie",
        "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
        "turnsToRecommendation": 2,
    }), encoding="utf-8")
    (output_dir / "user_feedback.json").write_text(json.dumps({
        "productNeedConstraintSatisfaction": "partially",
        "personalPreferenceSatisfaction": "yes",
        "overallExperienceRating": 8,
        "reason": "The final choice fit, but the first response was broad.",
        "askedUsefulClarificationQuestions": True,
    }), encoding="utf-8")

    result = build_result_from_harbor_artifacts(
        output_dir=output_dir,
        config=PersonaEvalConfig(domain="movie", engine="gpt-4o-mini", max_turns=8),
        persona=Persona(id="p1", name="Persona One", source="fixture"),
        sut_description="Movie recommender.",
        created_at="2026-06-23T00:00:00Z",
        prompts={"harborPrompt": "Persona system prompt.", "taskPrompt": "Task prompt."},
    )

    assert result.turn_views[1]["recommendedItems"] == [
        {"itemId": "42", "title": "Movie A", "rank": 1}
    ]
    payload = result.to_dict()
    assert payload["config"]["domain"] == "movie"
    assert payload["persona"]["name"] == "Persona One"
    assert payload["transcript"][1]["assistantMessage"] == "Try Movie A."
    assert payload["recommendedItemIds"] == {"perTurn": [[], ["42"]], "final": ["42"]}
    assert payload["prompts"] == {
        "harborPrompt": "Persona system prompt.",
        "taskPrompt": "Task prompt.",
    }
    assert payload["questionnaire"] == {
        "constraintSatisfaction": 3,
        "constraintRationale": "The final choice fit, but the first response was broad.",
        "preferenceSatisfaction": 5,
        "preferenceRationale": "The final choice fit, but the first response was broad.",
        "overallRating": 8,
        "ratingReason": "The final choice fit, but the first response was broad.",
        "askedUsefulClarifyingQuestions": True,
        "clarifyingNotes": "The final choice fit, but the first response was broad.",
    }
    assert payload["metricScores"] == {
        "turnsToRecommendation": 2,
        "numTurns": 2,
        "recommendedItemCount": 1,
    }


def test_build_result_from_harbor_artifacts_rejects_ungrounded_recommendations(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "transcript.json").write_text(json.dumps({
        "sessionId": "ses_123",
        "domain": "movie",
        "messages": [
            {"role": "user", "content": "I want a thoughtful movie."},
            {"role": "assistant", "content": "What tone do you prefer?"},
            {"role": "user", "content": "Quiet and reflective."},
            {"role": "assistant", "content": "Any settings you like?"},
            {"role": "user", "content": "Asian cinema would be good."},
            {"role": "assistant", "content": "Here are some ideas."},
        ],
        "turns": [],
    }), encoding="utf-8")
    (output_dir / "recommendation_result.json").write_text(json.dumps({
        "sessionId": "ses_123",
        "domain": "movie",
        "recommendedItems": [{"itemId": "movie_0001", "title": "Invented Movie"}],
        "turnsToRecommendation": 3,
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="grounded"):
        build_result_from_harbor_artifacts(
            output_dir=output_dir,
            config=PersonaEvalConfig(domain="movie", engine="gpt-4o-mini", max_turns=8),
            persona=Persona(id="p1", name="Persona One", source="fixture"),
            sut_description="Movie recommender.",
            created_at="2026-06-23T00:00:00Z",
        )


def test_write_harbor_persona_yaml_uses_persona_context_as_system_prompt(tmp_path):
    persona = Persona(
        id="p1",
        name="Persona One",
        source="fixture",
        summary="A careful viewer.",
        context="Name: Persona One\nHow you talk: concise and skeptical",
    )

    path = write_harbor_persona_yaml(tmp_path, persona)

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data == {
        "persona_id": "p1",
        "display_name": "Persona One",
        "summary": "A careful viewer.",
        "system_prompt": "Name: Persona One\nHow you talk: concise and skeptical",
    }


def test_build_recommender_simulation_prompt_is_task_specific_not_persona_identity():
    prompt = build_recommender_simulation_prompt(
        domain="game",
        max_turns=7,
        sut_description="A game recommender exposed through a chat API.",
        goal_context_description="Persona reveals preferences gradually.",
    )

    assert "Harbor supplies the persona system prompt" in prompt
    assert "You are testing a game recommendation system" in prompt
    assert '"domain": "game"' in prompt
    assert "at least three user turns and three assistant turns" in prompt
    assert "Do not reveal everything at once" in prompt
    assert "Finish within 7 user turns" in prompt
    assert "Do not simulate the recommender" in prompt
    assert "application feedback scorer" in prompt
    assert "user_feedback.json" not in prompt
    assert "overallExperienceRating" not in prompt
    assert "7-8: the run is useful overall" not in prompt


def test_resolve_repo_root_handles_local_and_container_layouts():
    assert resolve_repo_root(
        Path("/workspace/applications/recommendation_chatbot_eval/backend/service/harbor_persona_eval.py")
    ) == Path("/workspace")
    assert resolve_repo_root(
        Path("/app/backend/service/harbor_persona_eval.py")
    ) == Path("/app")


def test_harbor_runner_writes_run_inputs_invokes_harbor_and_maps_artifacts(tmp_path):
    calls = []
    (tmp_path / ".env.local").write_text(
        "OPENAI_API_KEY=sk-test-openai\nANTHROPIC_API_KEY=sk-test-anthropic\n",
        encoding="utf-8",
    )

    def fake_command(command, *, cwd, env):
        calls.append((command, cwd, env))
        config_path = command[command.index("-c") + 1]
        config = yaml.safe_load(open(config_path, encoding="utf-8"))
        assert config["agents"][0]["name"] == "persona-claude-code"
        assert config["environment"]["force_build"] is True
        assert config["environment"]["delete"] is False
        assert config["agents"][0]["kwargs"]["persona_path"].endswith("persona.yaml")
        assert config["tasks"][0]["path"].endswith("application/tasks/recommender-agent_chat_api")
        prompt_path = config["extra_instruction_paths"][0]
        assert prompt_path.endswith("task_prompt.md")
        assert "You are testing a movie recommendation system" in open(
            prompt_path, encoding="utf-8"
        ).read()
        assert env["INTERECAGENT_ENGINE"] == "gpt-4o"
        assert env["RECBOT_READY_DOMAIN"] == "movie"
        assert env["OPENAI_API_KEY"] == "sk-test-openai"
        assert env["ANTHROPIC_API_KEY"] == "sk-test-anthropic"

        output_dir = (
            tmp_path
            / "runs"
            / config["job_name"]
            / "recommender-agent_chat_api__fake"
            / "artifacts"
            / "app"
            / "output"
        )
        output_dir.mkdir(parents=True)
        (output_dir / "transcript.json").write_text(json.dumps({
            "sessionId": "ses_123",
            "domain": "movie",
            "messages": [
                {"role": "user", "content": "I want a movie."},
                {"role": "assistant", "content": "Try Movie A."},
            ],
            "turns": [{
                "turnId": "0",
                "userMessage": "I want a movie.",
                "assistantMessage": "Try Movie A.",
                "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            }],
        }), encoding="utf-8")
        (output_dir / "recommendation_result.json").write_text(json.dumps({
            "sessionId": "ses_123",
            "domain": "movie",
            "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            "turnsToRecommendation": 1,
        }), encoding="utf-8")
        (output_dir / "user_feedback.json").write_text(json.dumps({
            "productNeedConstraintSatisfaction": "yes",
            "personalPreferenceSatisfaction": "yes",
            "overallExperienceRating": 9,
            "reason": "Good fit.",
            "askedUsefulClarificationQuestions": False,
        }), encoding="utf-8")
        return 0

    class Session:
        turns = []

    runner = HarborPersonaEvalRunner(
        repo_root=tmp_path,
        runs_root=tmp_path / "runs",
        command_runner=fake_command,
        harbor_command=("uv", "run", "--frozen", "harbor", "run"),
    )
    session = Session()
    events = []

    result = runner(
        session,
        Persona(id="p1", name="Persona One", context="A careful viewer."),
        "Movie recommender.",
        PersonaEvalConfig(domain="movie", engine="gpt-4o", max_turns=5),
        object(),
        created_at="2026-06-23T00:00:00Z",
        on_event=events.append,
    )

    assert calls
    assert "--agent-env" in calls[0][0]
    assert "--env-file" in calls[0][0]
    assert session.turns[0]["recommendedItems"][0]["itemId"] == "42"
    payload = result.to_dict()
    assert payload["questionnaire"]["overallRating"] == 9
    assert payload["prompts"]["harborPrompt"] == "A careful viewer."
    assert "You are testing a movie recommendation system" in payload["prompts"]["taskPrompt"]
    assert {"type": "phase", "phase": "harbor_starting"} in events
    assert any(
        event.get("type") == "prompts"
        and event["prompts"]["harborPrompt"] == "A careful viewer."
        and "You are testing a movie recommendation system" in event["prompts"]["taskPrompt"]
        for event in events
    )
    assert {"type": "phase", "phase": "harbor_collecting_artifacts"} in events


def test_harbor_runner_uses_feedback_scorer_over_harbor_self_rating(tmp_path):
    scorer_calls = []

    def feedback_scorer(*, persona, sut_description, config, turn_views, recommended_items):
        scorer_calls.append(
            {
                "persona": persona.id,
                "sut": sut_description,
                "domain": config.domain,
                "turn_items": turn_views[0]["recommendedItems"],
                "final_items": recommended_items,
            }
        )
        return {
            "constraintSatisfaction": 4,
            "constraintRationale": "Original scorer judged the need mostly met.",
            "preferenceSatisfaction": 4,
            "preferenceRationale": "Original scorer judged preferences mostly met.",
            "overallRating": 8,
            "ratingReason": "Original scoring prompt output.",
            "askedUsefulClarifyingQuestions": True,
            "clarifyingNotes": "The recommender adapted after feedback.",
        }

    def fake_command(command, *, cwd, env):
        config = yaml.safe_load(open(command[command.index("-c") + 1], encoding="utf-8"))
        output_dir = (
            tmp_path
            / "runs"
            / config["job_name"]
            / "recommender-agent_chat_api__fake"
            / "artifacts"
            / "app"
            / "output"
        )
        output_dir.mkdir(parents=True)
        (output_dir / "transcript.json").write_text(json.dumps({
            "sessionId": "ses_123",
            "domain": "movie",
            "messages": [
                {"role": "user", "content": "I want a movie."},
                {"role": "assistant", "content": "Try Movie A."},
            ],
            "turns": [{
                "turnId": "0",
                "userMessage": "I want a movie.",
                "assistantMessage": "Try Movie A.",
                "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            }],
        }), encoding="utf-8")
        (output_dir / "recommendation_result.json").write_text(json.dumps({
            "sessionId": "ses_123",
            "domain": "movie",
            "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            "turnsToRecommendation": 1,
        }), encoding="utf-8")
        (output_dir / "user_feedback.json").write_text(json.dumps({
            "productNeedConstraintSatisfaction": "no",
            "personalPreferenceSatisfaction": "no",
            "overallExperienceRating": 2,
            "reason": "Harbor self-rating should be ignored.",
            "askedUsefulClarificationQuestions": False,
        }), encoding="utf-8")
        return 0

    class Session:
        turns = []

    runner = HarborPersonaEvalRunner(
        repo_root=tmp_path,
        runs_root=tmp_path / "runs",
        command_runner=fake_command,
        feedback_scorer=feedback_scorer,
    )
    result = runner(
        Session(),
        Persona(id="p1", name="Persona One", context="A careful viewer."),
        "Movie recommender.",
        PersonaEvalConfig(domain="movie"),
        object(),
        created_at="2026-06-23T00:00:00Z",
    )

    assert result.to_dict()["questionnaire"]["overallRating"] == 8
    assert scorer_calls == [
        {
            "persona": "p1",
            "sut": "Movie recommender.",
            "domain": "movie",
            "turn_items": [{"itemId": "42", "title": "Movie A"}],
            "final_items": [{"itemId": "42", "title": "Movie A"}],
        }
    ]


def test_harbor_runner_cache_flags_can_be_overridden(tmp_path, monkeypatch):
    monkeypatch.setenv("MATRIX_HARBOR_FORCE_BUILD", "0")
    monkeypatch.setenv("MATRIX_HARBOR_DELETE", "1")

    def fake_command(command, *, cwd, env):
        config = yaml.safe_load(open(command[command.index("-c") + 1], encoding="utf-8"))
        assert config["environment"] == {
            "type": "docker",
            "delete": True,
            "force_build": False,
        }
        output_dir = (
            tmp_path
            / "runs"
            / config["job_name"]
            / "recommender-agent_chat_api__fake"
            / "artifacts"
            / "app"
            / "output"
        )
        output_dir.mkdir(parents=True)
        (output_dir / "transcript.json").write_text(json.dumps({
            "sessionId": "ses_123",
            "domain": "movie",
            "messages": [
                {"role": "user", "content": "I want a movie."},
                {"role": "assistant", "content": "Try Movie A."},
            ],
            "turns": [{
                "turnId": "0",
                "userMessage": "I want a movie.",
                "assistantMessage": "Try Movie A.",
                "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            }],
        }), encoding="utf-8")
        (output_dir / "recommendation_result.json").write_text(json.dumps({
            "sessionId": "ses_123",
            "domain": "movie",
            "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            "turnsToRecommendation": 1,
        }), encoding="utf-8")
        return 0

    class Session:
        turns = []

    runner = HarborPersonaEvalRunner(
        repo_root=tmp_path,
        runs_root=tmp_path / "runs",
        command_runner=fake_command,
    )
    runner(
        Session(),
        Persona(id="p1", name="Persona One", context="A careful viewer."),
        "Movie recommender.",
        PersonaEvalConfig(domain="movie"),
        object(),
        created_at="2026-06-23T00:00:00Z",
    )


def test_harbor_runner_default_command_uses_configured_uv_path(tmp_path, monkeypatch):
    monkeypatch.setenv("MATRIX_HARBOR_UV", "/custom/bin/uv")
    calls = []

    def fake_command(command, *, cwd, env):
        calls.append(command)
        config = yaml.safe_load(open(command[command.index("-c") + 1], encoding="utf-8"))
        output_dir = (
            tmp_path
            / "runs"
            / config["job_name"]
            / "recommender-agent_chat_api__fake"
            / "artifacts"
            / "app"
            / "output"
        )
        output_dir.mkdir(parents=True)
        (output_dir / "transcript.json").write_text(json.dumps({
            "sessionId": "ses_123",
            "domain": "movie",
            "messages": [
                {"role": "user", "content": "I want a movie."},
                {"role": "assistant", "content": "Try Movie A."},
            ],
            "turns": [{
                "turnId": "0",
                "userMessage": "I want a movie.",
                "assistantMessage": "Try Movie A.",
                "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            }],
        }), encoding="utf-8")
        (output_dir / "recommendation_result.json").write_text(json.dumps({
            "sessionId": "ses_123",
            "domain": "movie",
            "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            "turnsToRecommendation": 1,
        }), encoding="utf-8")
        return 0

    class Session:
        turns = []

    runner = HarborPersonaEvalRunner(
        repo_root=tmp_path,
        runs_root=tmp_path / "runs",
        command_runner=fake_command,
    )
    runner(
        Session(),
        Persona(id="p1", name="Persona One", context="A careful viewer."),
        "Movie recommender.",
        PersonaEvalConfig(domain="movie"),
        object(),
        created_at="2026-06-23T00:00:00Z",
    )

    assert calls[0][:4] == ["/custom/bin/uv", "run", "--frozen", "harbor"]


def test_harbor_runner_surfaces_trial_errors_when_artifacts_are_missing(tmp_path):
    def fake_command(command, *, cwd, env):
        config = yaml.safe_load(open(command[command.index("-c") + 1], encoding="utf-8"))
        job_dir = tmp_path / "runs" / config["job_name"]
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "result.json").write_text(json.dumps({
            "stats": {
                "n_errored_trials": 1,
                "evals": {
                    "persona-claude-code__claude-sonnet-4-6__adhoc": {
                        "exception_stats": {
                            "RuntimeError": ["recommender-agent_chat_api__fake"]
                        }
                    }
                },
            }
        }), encoding="utf-8")
        trial_dir = job_dir / "recommender-agent_chat_api__fake"
        trial_dir.mkdir()
        (trial_dir / "exception.txt").write_text(
            "Docker build failed: No space left on device",
            encoding="utf-8",
        )
        return 0

    class Session:
        turns = []

    runner = HarborPersonaEvalRunner(
        repo_root=tmp_path,
        runs_root=tmp_path / "runs",
        command_runner=fake_command,
    )

    with pytest.raises(RuntimeError, match="No space left on device"):
        runner(
            Session(),
            Persona(id="p1", name="Persona One", context="A careful viewer."),
            "Movie recommender.",
            PersonaEvalConfig(domain="movie"),
            object(),
            created_at="2026-06-23T00:00:00Z",
        )
