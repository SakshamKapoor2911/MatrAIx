# test_agents.py — Tests for agent module: tools, prompts, LLM client, orchestrator.
# Tests the full agent loop without requiring a live LLM endpoint.

import pytest
import requests
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from environments.oasis.agents.tools import TOOL_DEFINITIONS, TOOL_NAMES, get_tools_for_actions
from environments.oasis.agents.prompt import build_system_prompt, build_observation_prompt
from environments.oasis.agents.llm_client import LLMClient, LLMConfig, LLMResponse, ToolCall
from environments.oasis.agents.platform_client import PlatformClient
from environments.oasis.agents.runner import AgentConfig, AgentRunner, StepResult
from environments.oasis.agents.orchestrator import Orchestrator, SimulationConfig, SimulationResult
from environments.oasis.persona_loader.adapter import load_personas_from_directory, OasisUserInfo
from environments.oasis.platform.server import PlatformState

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "persona_loader" / "tests" / "fixtures"


class TestToolDefinitions:
    def test_has_all_core_actions(self):
        assert "create_post" in TOOL_NAMES
        assert "like_post" in TOOL_NAMES
        assert "repost" in TOOL_NAMES
        assert "follow" in TOOL_NAMES
        assert "do_nothing" in TOOL_NAMES
        assert "create_comment" in TOOL_NAMES
        assert "quote_post" in TOOL_NAMES

    def test_tool_count(self):
        assert len(TOOL_DEFINITIONS) == 19

    def test_each_tool_has_function_schema(self):
        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"

    def test_get_tools_for_actions_filters(self):
        subset = get_tools_for_actions(["like_post", "do_nothing"])
        assert len(subset) == 2
        names = [t["function"]["name"] for t in subset]
        assert "like_post" in names
        assert "do_nothing" in names

    def test_get_tools_for_actions_none_returns_all(self):
        result = get_tools_for_actions(None)
        assert len(result) == len(TOOL_DEFINITIONS)


class TestPrompt:
    def test_system_prompt_contains_persona(self):
        personas = load_personas_from_directory(FIXTURES_DIR, max_agents=1)
        prompt = build_system_prompt(personas[0])
        assert personas[0].name in prompt
        assert "social media user" in prompt.lower()
        assert "json" in prompt.lower()

    def test_observation_prompt_with_posts(self):
        posts = [
            {"post_id": 1, "user_id": 5, "content": "Hello world", "num_likes": 3, "num_dislikes": 0, "num_comments": 1, "num_shares": 0},
            {"post_id": 2, "user_id": 8, "content": "Tech news today", "num_likes": 10, "num_dislikes": 2, "num_comments": 5, "num_shares": 3},
        ]
        prompt = build_observation_prompt(posts)
        assert "Hello world" in prompt
        assert "Tech news" in prompt
        assert "post_id=1" in prompt
        assert "3 likes" in prompt

    def test_observation_prompt_empty_feed(self):
        prompt = build_observation_prompt([])
        assert "launched" in prompt.lower() or "no posts" in prompt.lower()

    def test_observation_respects_max_posts(self):
        posts = [{"post_id": i, "user_id": 1, "content": f"Post {i}", "num_likes": 0, "num_dislikes": 0, "num_comments": 0, "num_shares": 0} for i in range(50)]
        prompt = build_observation_prompt(posts, max_posts=5)
        assert "post_id=4" in prompt
        assert "post_id=10" not in prompt


class TestLLMClient:
    def test_config_defaults(self):
        config = LLMConfig()
        assert config.model == "Qwen/Qwen3-4B"
        assert config.temperature == 0.7

    def test_parse_tool_calls_from_json_response(self):
        client = LLMClient(LLMConfig())
        text = '{"name": "like_post", "arguments": {"post_id": 42}}'
        calls = client._parse_tool_calls_from_text(text)
        assert len(calls) == 1
        assert calls[0].name == "like_post"
        assert calls[0].arguments["post_id"] == 42

    def test_parse_tool_calls_list(self):
        client = LLMClient(LLMConfig())
        text = '[{"name": "like_post", "arguments": {"post_id": 1}}, {"name": "follow", "arguments": {"user_id": 3}}]'
        calls = client._parse_tool_calls_from_text(text)
        assert len(calls) == 2

    def test_parse_tool_calls_invalid_text(self):
        client = LLMClient(LLMConfig())
        calls = client._parse_tool_calls_from_text("I think this post is interesting")
        assert len(calls) == 0

    def test_connection_failure_returns_error(self):
        config = LLMConfig(base_url="http://127.0.0.1:19999/v1", timeout=2)
        client = LLMClient(config)
        response = client.chat([{"role": "user", "content": "hello"}])
        assert response.error is not None


def _mock_llm_response(tool_calls):
    import json
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    tc_list = [{"function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}, "id": f"call_{i}"} for i, tc in enumerate(tool_calls)]
    mock_resp.json.return_value = {"choices": [{"message": {"content": None, "tool_calls": tc_list}}]}
    return mock_resp


class TestOrchestratorLocal:
    def test_setup_creates_users(self):
        personas = load_personas_from_directory(FIXTURES_DIR)
        config = SimulationConfig(max_agents=5, num_steps=1)
        orch = Orchestrator(config)
        orch.setup(personas=personas)
        stats = orch.get_stats()
        assert stats["user"] == 5
        orch.close()

    def test_setup_with_graph(self):
        from environments.oasis.network.builder import build_social_graph, NetworkConfig
        personas = load_personas_from_directory(FIXTURES_DIR)
        graph = build_social_graph(personas, NetworkConfig(random_seed=42))
        config = SimulationConfig(max_agents=5, num_steps=1)
        orch = Orchestrator(config)
        orch.setup(personas=personas, graph=graph)
        stats = orch.get_stats()
        assert stats["user"] == 5
        assert stats["follow"] > 0
        orch.close()

    def test_setup_injects_seed_posts(self):
        from environments.oasis.network.builder import build_simple_topic_graph
        personas = load_personas_from_directory(FIXTURES_DIR)
        graph = build_simple_topic_graph(personas, follow_probability=0.5, random_seed=42)
        config = SimulationConfig(max_agents=5, num_steps=1)
        orch = Orchestrator(config)
        orch.setup(personas=personas, graph=graph)
        stats = orch.get_stats()
        assert stats["post"] > 0
        orch.close()

    @patch("environments.oasis.agents.llm_client.requests.post")
    def test_run_step_with_mocked_llm(self, mock_post):
        mock_post.return_value = _mock_llm_response([ToolCall(name="do_nothing", arguments={})])

        personas = load_personas_from_directory(FIXTURES_DIR)
        config = SimulationConfig(max_agents=3, num_steps=2, llm_base_url="http://fake:8002/v1")
        orch = Orchestrator(config)
        orch.setup(personas=personas[:3])
        results = orch.run_step_local()
        assert len(results) == 3
        for r in results:
            assert len(r.actions_taken) >= 1
        orch.close()

    @patch("environments.oasis.agents.llm_client.requests.post")
    def test_full_run_with_mocked_llm(self, mock_post):
        mock_post.return_value = _mock_llm_response([
            ToolCall(name="create_post", arguments={"content": "Hello from the simulation!"}),
        ])

        personas = load_personas_from_directory(FIXTURES_DIR)
        config = SimulationConfig(max_agents=3, num_steps=3, llm_base_url="http://fake:8002/v1")
        orch = Orchestrator(config)
        orch.setup(personas=personas[:3])
        result = orch.run()

        assert isinstance(result, SimulationResult)
        assert result.num_agents == 3
        assert result.num_steps == 3
        assert len(result.step_results) == 3
        assert result.platform_stats["post"] > 0
        assert result.platform_stats["trace"] > 0
        orch.close()

    @patch("environments.oasis.agents.llm_client.requests.post")
    def test_traces_recorded(self, mock_post):
        mock_post.return_value = _mock_llm_response([ToolCall(name="create_post", arguments={"content": "Test trace"})])

        personas = load_personas_from_directory(FIXTURES_DIR, max_agents=2)
        config = SimulationConfig(max_agents=2, num_steps=1, llm_base_url="http://fake:8002/v1")
        orch = Orchestrator(config)
        orch.setup(personas=personas)
        orch.run()
        traces = orch.get_traces()
        assert len(traces) > 0
        action_types = [t["action"] for t in traces]
        assert "create_post" in action_types
        orch.close()

    @patch("environments.oasis.agents.llm_client.requests.post")
    def test_llm_error_falls_back_to_do_nothing(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")

        personas = load_personas_from_directory(FIXTURES_DIR, max_agents=2)
        config = SimulationConfig(max_agents=2, num_steps=1, llm_base_url="http://fake:8002/v1")
        orch = Orchestrator(config)
        orch.setup(personas=personas)
        results = orch.run_step_local()
        for r in results:
            assert r.actions_taken[0]["action"] == "do_nothing"
        orch.close()
