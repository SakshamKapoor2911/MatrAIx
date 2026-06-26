# runner.py — Agent execution loop: observe feed → call LLM → execute actions → repeat.
# This is the core agent process that runs inside a Docker container (or locally).
# Mirrors OASIS's SocialAgent.perform_action_by_llm() but uses HTTP instead of Channel.

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from environments.oasis.agents.llm_client import LLMClient, LLMConfig, LLMResponse, ToolCall
from environments.oasis.agents.platform_client import PlatformClient
from environments.oasis.agents.prompt import build_observation_prompt, build_system_prompt
from environments.oasis.agents.tools import TOOL_DEFINITIONS, get_tools_for_actions
from environments.oasis.persona_loader.adapter import OasisUserInfo, load_personas_from_files

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    persona_path: str = ""
    platform_url: str = "http://localhost:8000"
    llm_base_url: str = "http://localhost:8002/v1"
    llm_api_key: str = ""
    llm_model: str = "Qwen/Qwen3-4B"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 512
    max_posts_in_feed: int = 20
    available_actions: list[str] = field(default_factory=lambda: [
        "create_post", "like_post", "dislike_post", "repost",
        "quote_post", "create_comment", "follow", "do_nothing",
    ])
    max_actions_per_step: int = 3
    # When set (>=0), the agent is one of a pre-seeded cluster: the orchestrator
    # already signed everyone up in index order, so this agent resolves its
    # user_id by its agent_id instead of signing up again (which would mint a
    # different user_id and break graph/edge alignment). Used by the Greenland
    # multi-container run; ignored (left None) for the standalone/local path.
    cluster_agent_id: int | None = None


@dataclass
class StepResult:
    step: int
    user_id: int
    actions_taken: list[dict[str, Any]]
    llm_response: LLMResponse | None = None
    error: str | None = None
    duration_ms: int = 0


class AgentRunner:
    def __init__(self, config: AgentConfig):
        self._config = config
        self._persona: OasisUserInfo | None = None
        self._user_id: int | None = None
        self._platform = PlatformClient(base_url=config.platform_url)
        self._llm = LLMClient(LLMConfig(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            model=config.llm_model,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
        ))
        self._system_prompt: str = ""
        self._tools: list[dict[str, Any]] = []
        self._step_count: int = 0

    @property
    def persona(self) -> OasisUserInfo | None:
        return self._persona

    @property
    def user_id(self) -> int | None:
        return self._user_id

    @property
    def step_count(self) -> int:
        return self._step_count

    def initialize(self) -> int:
        personas = load_personas_from_files([self._config.persona_path])
        self._persona = personas[0]

        self._system_prompt = build_system_prompt(self._persona)
        self._tools = get_tools_for_actions(self._config.available_actions)

        if self._config.cluster_agent_id is not None:
            # Pre-seeded cluster mode: orchestrator already registered every user
            # in index order (agent_id=i -> user_id=i+1). Resolve our user_id by
            # agent_id so it matches the graph edges, instead of re-signing-up.
            state = self._platform.get_state(self._config.cluster_agent_id)
            self._user_id = state["user_id"]
            return self._user_id

        result = self._platform.signup(
            agent_id=hash(self._persona.persona_id) % 1000000,
            user_name=self._persona.user_name,
            name=self._persona.name,
            bio=self._persona.bio,
        )
        self._user_id = result["user_id"]
        return self._user_id

    def step(self) -> StepResult:
        if self._user_id is None:
            return StepResult(step=self._step_count, user_id=0, actions_taken=[], error="Agent not initialized")

        start = time.time()
        self._step_count += 1

        posts = self._platform.refresh(self._user_id)
        observation = build_observation_prompt(posts, max_posts=self._config.max_posts_in_feed)

        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": observation},
        ]

        llm_response = self._llm.chat(messages, tools=self._tools)

        if llm_response.error:
            duration = int((time.time() - start) * 1000)
            return StepResult(
                step=self._step_count, user_id=self._user_id,
                actions_taken=[], llm_response=llm_response,
                error=llm_response.error, duration_ms=duration,
            )

        actions_taken = []
        tool_calls = llm_response.tool_calls[:self._config.max_actions_per_step]

        if not tool_calls:
            self._platform.do_nothing(self._user_id)
            actions_taken.append({"action": "do_nothing", "params": {}, "result": {"success": True}})
        else:
            for tc in tool_calls:
                result = self._execute_tool_call(tc)
                actions_taken.append({
                    "action": tc.name,
                    "params": tc.arguments,
                    "result": result,
                })

        duration = int((time.time() - start) * 1000)
        return StepResult(
            step=self._step_count, user_id=self._user_id,
            actions_taken=actions_taken, llm_response=llm_response,
            duration_ms=duration,
        )

    def _execute_tool_call(self, tc: ToolCall) -> dict[str, Any]:
        action_type = tc.name
        params = tc.arguments

        if action_type not in self._config.available_actions:
            return {"success": False, "error": f"Action '{action_type}' not available"}

        try:
            return self._platform.action(self._user_id, action_type, params)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run(self, num_steps: int = 1, step_delay_s: float = 0.0) -> list[StepResult]:
        results = []
        for n in range(num_steps):
            result = self.step()
            results.append(result)
            # Pace steps so a long-horizon social sim evolves over wall-clock
            # time instead of finishing in seconds. Skip the delay after the
            # last step.
            if step_delay_s > 0 and n < num_steps - 1:
                time.sleep(step_delay_s)
        return results
