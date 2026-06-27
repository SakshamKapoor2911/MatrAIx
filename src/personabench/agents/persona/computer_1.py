"""Persona-backed computer-use agent with platform-aware CUA routing."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.agent.name import AgentName

from personabench.agents.persona.cua_submission import materialize_cua_submission_profile
from personabench.agents.persona.ios_submission import materialize_ios_decision_file
from personabench.agents.persona.mixin import PersonaMixin

CuaBackendKind = Literal["use_computer_desktop", "ios", "docker_computer1"]


def resolve_cua_backend_kind(
    environment: BaseEnvironment,
    *,
    override: str | None = None,
) -> CuaBackendKind:
    """Pick the CUA runtime for this environment."""
    if override:
        normalized = override.strip().lower().replace("-", "_")
        if normalized in {"ios", "ios_cua"}:
            return "ios"
        if normalized in {
            "use_computer",
            "use_computer_desktop",
            "desktop",
            "anthropic",
            "anthropic_cua",
            "macos",
            "ubuntu",
        }:
            return "use_computer_desktop"
        if normalized in {
            "docker",
            "docker_computer1",
            "computer1",
            "computer_1",
            "linux",
        }:
            return "docker_computer1"
        raise ValueError(
            f"Unknown cua_backend {override!r}; use ios, use-computer, or docker."
        )

    from harbor.environments.use_computer import UseComputerEnvironment

    if isinstance(environment, UseComputerEnvironment):
        platform = getattr(environment, "_platform", "macos")
        if platform == "ios":
            return "ios"
        return "use_computer_desktop"

    return "docker_computer1"


def _build_cua_delegate(
    kind: CuaBackendKind,
    *,
    logs_dir: Path,
    model_name: str | None,
    logger,
    mcp_servers,
    skills_dir: str | None,
    delegate_kwargs: dict[str, Any],
) -> BaseAgent:
    common: dict[str, Any] = {
        "logs_dir": logs_dir,
        "model_name": model_name,
        "logger": logger,
        "mcp_servers": mcp_servers,
        "skills_dir": skills_dir,
        **delegate_kwargs,
    }

    if kind == "ios":
        try:
            from use_computer.harbor.agents import IOSAgent
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "persona-computer-1 iOS CUA requires "
                "`uv sync --extra use-computer` (installs use-computer[harbor,agents])."
            ) from exc
        return IOSAgent(**common)

    if kind == "use_computer_desktop":
        try:
            from use_computer.harbor.agents import AnthropicCUAAgent
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "persona-computer-1 use.computer CUA requires "
                "`uv sync --extra use-computer` (installs use-computer[harbor,agents])."
            ) from exc
        return AnthropicCUAAgent(**common)

    from harbor.agents.computer_1 import Computer1

    try:
        return Computer1(**common)
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "persona-computer-1 Docker CUA requires "
            "`uv sync --extra computer-1` for native Anthropic computer-use."
        ) from exc


class PersonaComputer1(PersonaMixin, BaseAgent):
    """Route persona CUA to use.computer (macOS/iOS) or Docker Computer1."""

    SUPPORTS_ATIF = True

    @staticmethod
    def name() -> str:
        return AgentName.PERSONA_COMPUTER_1.value

    def __init__(
        self,
        logs_dir: Path,
        model_name: str | None = None,
        persona_path: str | None = None,
        persona_template_path: str | None = None,
        cua_backend: str | None = None,
        cua_submission_profile: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            logs_dir=logs_dir,
            model_name=model_name,
            mcp_servers=kwargs.get("mcp_servers"),
            skills_dir=kwargs.get("skills_dir"),
        )
        self._init_persona(
            persona_path,
            AgentName.PERSONA_COMPUTER_1.value,
            persona_template_path=persona_template_path,
        )
        self._cua_backend_override = cua_backend
        self._cua_submission_profile = cua_submission_profile
        self._delegate_kwargs = dict(kwargs)
        self._delegate: BaseAgent | None = None
        self._delegate_kind: CuaBackendKind | None = None

    def version(self) -> str | None:
        if self._delegate is not None:
            return self._delegate.version()
        return "1.0.0"

    def _get_delegate(self, environment: BaseEnvironment) -> BaseAgent:
        kind = resolve_cua_backend_kind(
            environment,
            override=self._cua_backend_override,
        )
        if self._delegate is None or self._delegate_kind != kind:
            self._delegate = _build_cua_delegate(
                kind,
                logs_dir=self.logs_dir,
                model_name=self.model_name,
                logger=self.logger,
                mcp_servers=self.mcp_servers,
                skills_dir=self.skills_dir,
                delegate_kwargs=self._delegate_kwargs,
            )
            self._delegate_kind = kind
            self.logger.info(
                "persona-computer-1 backend=%s for environment %s",
                kind,
                type(environment).__name__,
            )
        return self._delegate

    async def setup(self, environment: BaseEnvironment) -> None:
        await self._get_delegate(environment).setup(environment)

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        await self._prepare_persona_trial(environment)
        rendered = self._render_persona_instruction(instruction)
        delegate = self._get_delegate(environment)
        await delegate.run(rendered, environment, context)
        if self._delegate_kind == "ios":
            await materialize_ios_decision_file(
                environment,
                self.logs_dir,
                logger=self.logger,
            )
        elif self._delegate_kind == "docker_computer1" and self._cua_submission_profile:
            await materialize_cua_submission_profile(
                self._cua_submission_profile,
                environment,
                self.logs_dir,
                logger=self.logger,
            )
