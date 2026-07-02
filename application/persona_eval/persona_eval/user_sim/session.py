"""UserSim v2 session — messages[] memory and tool-driven turns."""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from persona_eval.types import Persona
from persona_eval.user_sim.prompt import assemble_system_prompt
from persona_eval.user_sim.scenario import UserScenario
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
        scenario: UserScenario,
        *,
        persona_yaml_path: Optional[str] = None,
    ) -> None:
        self._client = client
        self._persona = persona
        self._scenario = scenario
        self._persona_yaml_path = persona_yaml_path
        self._revealed_facts: Set[str] = set()
        system = assemble_system_prompt(
            persona,
            scenario,
            persona_yaml_path=persona_yaml_path,
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
        for fact_id in action.revealed_facts:
            self._revealed_facts.add(fact_id)
        assistant_notes: List[str] = []
        if action.revealed_facts:
            assistant_notes.append(
                "Revealed facts: {}".format(", ".join(action.revealed_facts))
            )
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
