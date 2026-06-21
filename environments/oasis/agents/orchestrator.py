# orchestrator.py — Simulation orchestrator: starts platform, registers agents, runs timesteps.
# This is the entry point for running a complete OASIS simulation locally or on Greenland.
# For Docker deployment, each agent runs as a separate container; this runs them in-process.

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from environments.oasis.agents.runner import AgentConfig, AgentRunner, StepResult
from environments.oasis.network.builder import SocialGraph, build_oasis_follow_data
from environments.oasis.persona_loader.adapter import OasisUserInfo, load_personas_from_directory
from environments.oasis.platform.server import PlatformState, create_app

logger = logging.getLogger(__name__)


@dataclass
class SimulationConfig:
    persona_dir: str = ""
    max_agents: int = 10
    num_steps: int = 5
    platform_port: int = 8000
    platform_db_path: str = ":memory:"
    recsys_type: str = "random"
    llm_base_url: str = "http://localhost:8002/v1"
    llm_api_key: str = ""
    llm_model: str = "Qwen/Qwen3-4B"
    llm_temperature: float = 0.7
    available_actions: list[str] = field(default_factory=lambda: [
        "create_post", "like_post", "repost", "follow", "do_nothing",
    ])


@dataclass
class SimulationResult:
    num_agents: int
    num_steps: int
    step_results: list[list[StepResult]]
    platform_stats: dict[str, Any]
    duration_seconds: float


class Orchestrator:
    def __init__(self, config: SimulationConfig):
        self._config = config
        self._platform_state: PlatformState | None = None
        self._agents: list[AgentRunner] = []
        self._personas: list[OasisUserInfo] = []
        self._server_thread: threading.Thread | None = None

    def setup(self, personas: list[OasisUserInfo] | None = None, graph: SocialGraph | None = None):
        if personas is not None:
            self._personas = personas
        elif self._config.persona_dir:
            self._personas = load_personas_from_directory(
                self._config.persona_dir, max_agents=self._config.max_agents
            )
        else:
            raise ValueError("Must provide personas or set persona_dir in config")

        self._platform_state = PlatformState(
            db_path=self._config.platform_db_path,
            recsys_type=self._config.recsys_type,
        )

        for i, persona in enumerate(self._personas):
            user_id = self._platform_state.db.signup_user(
                agent_id=i,
                user_name=persona.user_name,
                name=persona.name,
                bio=persona.bio,
            )

        if graph is not None:
            edges = [(e.follower_idx + 1, e.followee_idx + 1) for e in graph.edges]
            self._platform_state.db.add_follows_bulk(edges)

            for sp in graph.seed_posts:
                self._platform_state.db.create_post(sp.author_idx + 1, sp.content)

        self._platform_state.advance_step()

    def _create_agent(self, persona: OasisUserInfo, persona_path: str) -> AgentRunner:
        config = AgentConfig(
            persona_path=persona_path,
            platform_url=f"http://localhost:{self._config.platform_port}",
            llm_base_url=self._config.llm_base_url,
            llm_api_key=self._config.llm_api_key,
            llm_model=self._config.llm_model,
            llm_temperature=self._config.llm_temperature,
            available_actions=self._config.available_actions,
        )
        return AgentRunner(config)

    def run_step_local(self) -> list[StepResult]:
        if self._platform_state is None:
            raise RuntimeError("Call setup() first")

        results = []
        for i, persona in enumerate(self._personas):
            user_id = i + 1
            from environments.oasis.agents.prompt import build_system_prompt, build_observation_prompt
            from environments.oasis.agents.llm_client import LLMClient, LLMConfig
            from environments.oasis.agents.tools import get_tools_for_actions

            posts_result = self._platform_state.action_processor.process(user_id, "refresh", {})
            posts = posts_result.data.get("posts", []) if posts_result.data else []

            observation = build_observation_prompt(posts, step=self._platform_state.time_step, agent_name=persona.name)
            system_prompt = build_system_prompt(persona)

            llm = LLMClient(LLMConfig(
                base_url=self._config.llm_base_url,
                api_key=self._config.llm_api_key,
                model=self._config.llm_model,
                temperature=self._config.llm_temperature,
            ))

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": observation},
            ]
            tools = get_tools_for_actions(self._config.available_actions)
            llm_response = llm.chat(messages)

            actions_taken = []
            if llm_response.error:
                self._platform_state.process_action(user_id, "do_nothing", {})
                actions_taken.append({"action": "do_nothing", "params": {}, "result": {"success": True}})
            elif not llm_response.tool_calls:
                self._platform_state.process_action(user_id, "do_nothing", {})
                actions_taken.append({"action": "do_nothing", "params": {}, "result": {"success": True}})
            else:
                for tc in llm_response.tool_calls[:5]:
                    if tc.name in self._config.available_actions:
                        result = self._platform_state.process_action(user_id, tc.name, tc.arguments)
                        actions_taken.append({
                            "action": tc.name,
                            "params": tc.arguments,
                            "result": result.to_dict(),
                        })

            results.append(StepResult(
                step=self._platform_state.time_step,
                user_id=user_id,
                actions_taken=actions_taken,
                llm_response=llm_response,
            ))

        self._platform_state.advance_step()
        return results

    def run(self) -> SimulationResult:
        if self._platform_state is None:
            raise RuntimeError("Call setup() first")

        start = time.time()
        all_results: list[list[StepResult]] = []

        for step in range(self._config.num_steps):
            step_results = self.run_step_local()
            all_results.append(step_results)
            logger.info(f"Step {step + 1}/{self._config.num_steps} complete: {len(step_results)} agents acted")

        duration = time.time() - start
        stats = self._platform_state.db.stats()

        return SimulationResult(
            num_agents=len(self._personas),
            num_steps=self._config.num_steps,
            step_results=all_results,
            platform_stats=stats,
            duration_seconds=duration,
        )

    def get_traces(self) -> list[dict[str, Any]]:
        if self._platform_state is None:
            return []
        return self._platform_state.db.get_all_traces()

    def get_stats(self) -> dict[str, Any]:
        if self._platform_state is None:
            return {}
        return self._platform_state.db.stats()

    def close(self):
        if self._platform_state is not None:
            self._platform_state.close()
