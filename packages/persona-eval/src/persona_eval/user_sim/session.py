"""Tool-driven user simulator session with messages[] memory."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from persona_eval.task_content_bundle import TaskContentBundle
from persona_eval.types import Persona
from persona_eval.user_sim.prompt import assemble_system_prompt
from persona_eval.user_sim.tool_client import ToolStepClient
from persona_eval.user_sim.tools import TurnAction, extract_stop_token, parse_tool_calls


_START_OBSERVATION = (
    "The conversation is starting. The application chatbot has not replied yet. "
    "Send your opening message with send_message."
)


class UserSimSession:
    """Tool-driven simulated user with real multi-turn ``messages[]`` memory."""

    def __init__(
        self,
        client: ToolStepClient,
        persona: Persona,
        *,
        persona_yaml_path: Optional[str] = None,
        task_bundle: Optional[TaskContentBundle] = None,
    ) -> None:
        self._client = client
        self._persona = persona
        self._persona_yaml_path = persona_yaml_path
        system = assemble_system_prompt(
            persona,
            persona_yaml_path=persona_yaml_path,
            task_bundle=task_bundle,
        )
        self._messages: List[Dict[str, Any]] = [{"role": "system", "content": system}]
        self.system_prompt = system

    @property
    def messages(self) -> List[Dict[str, Any]]:
        return list(self._messages)

    def next_action(self, observation: str) -> TurnAction:
        self._messages.append({"role": "user", "content": observation})
        calls = self._client.complete_with_tools(self._messages)
        action = parse_tool_calls(calls)
        assistant_notes: List[str] = []
        if action.message:
            stop = extract_stop_token(action.message)
            if stop and not action.end_reason:
                action.end_reason = stop
            assistant_notes.append("Tool send_message: {}".format(action.message))
        if action.end_reason:
            assistant_notes.append(
                "Tool end_conversation: {} ({})".format(action.end_reason, action.note or "no note")
            )
        self._messages.append(
            {
                "role": "assistant",
                "content": "\n".join(assistant_notes) or "(no tool action)",
            }
        )
        return action

    def opening_action(self) -> TurnAction:
        return self.next_action(_START_OBSERVATION)
