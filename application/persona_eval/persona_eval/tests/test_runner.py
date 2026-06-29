from persona_eval.runner import run_persona_eval
from persona_eval.types import Persona, PersonaEvalConfig, Questionnaire, SimulatorTurn


class FakeSession:
    def __init__(self, turns):
        self._turns = list(turns)
        self.calls = []

    def run_turn_sync(self, message):
        self.calls.append(message)
        return self._turns.pop(0)


class FakeSimulator:
    def __init__(self, kickoff, responses, q):
        self._kickoff = kickoff
        self._responses = list(responses)
        self._q = q
        self.feedback_calls = 0
        self.seen = None

    def kickoff(self, persona, sut):
        return self._kickoff

    def respond(self, persona, sut, pairs, last, items):
        return self._responses.pop(0)

    def final_feedback(self, persona, sut, transcript, final_items):
        self.feedback_calls += 1
        self.seen = (transcript, final_items)
        return self._q


class FakeSimulatorWithPrompts(FakeSimulator):
    def prompt_bundle(self, persona, sut):
        return {"personaPrompt": "persona prompt", "taskPrompt": "task prompt"}


def _persona():
    return Persona(id="p", name="Marco", summary="s", preferences=[],
                   dislikes=[], constraints=[], goal="g", communication_style="c")


def _q():
    return Questionnaire(4, "", 4, "", 8, "", True, "")


def test_runner_stops_when_satisfied_and_computes_metrics():
    session = FakeSession([
        {"assistantMessage": "what platform?", "recommendedItems": []},
        {"assistantMessage": "try these", "recommendedItems": [{"itemId": "6574", "title": "A"}]},
    ])
    sim = FakeSimulator("hi", [
        SimulatorTurn("PC, co-op", "continue"),
        SimulatorTurn("great thanks", "satisfied"),
    ], _q())
    res = run_persona_eval(session, _persona(), "desc",
                        PersonaEvalConfig(domain="game", max_turns=8), sim,
                        created_at="2026-06-21T00:00:00Z")
    assert len(res.transcript) == 2
    assert res.transcript[0].user_message == "hi"        # kickoff is turn 1's user message
    assert res.metric_scores.turns_to_recommendation == 2
    assert res.metric_scores.num_turns == 2
    assert res.transcript[-1].recommended_items[0]["title"] == "A"
    assert res.questionnaire.overall_rating == 8
    # the simulator gave self-feedback exactly once and saw the final items
    assert sim.feedback_calls == 1
    assert sim.seen[1] == [{"id": "6574", "title": "A"}]


def test_runner_respects_max_turns():
    session = FakeSession([{"assistantMessage": "hm", "recommendedItems": []} for _ in range(5)])
    sim = FakeSimulator("hi", [SimulatorTurn("more", "continue") for _ in range(5)], _q())
    res = run_persona_eval(session, _persona(), "desc",
                        PersonaEvalConfig(domain="game", max_turns=3), sim,
                        created_at="t")
    assert res.metric_scores.num_turns == 3
    assert res.metric_scores.turns_to_recommendation is None


def test_runner_emits_persona_feedback_phase():
    session = FakeSession([{"assistantMessage": "x", "recommendedItems": [{"itemId": "1", "title": "T"}]}])
    sim = FakeSimulator("hi", [SimulatorTurn("done", "satisfied")], _q())
    events = []
    run_persona_eval(session, _persona(), "desc", PersonaEvalConfig(domain="game", max_turns=2),
                  sim, created_at="t", on_event=events.append)
    assert any(e.get("type") == "turn" for e in events)
    assert any(e.get("phase") == "persona_feedback" for e in events)


def test_runner_emits_and_persists_prompts():
    session = FakeSession([{"assistantMessage": "x", "recommendedItems": []}])
    sim = FakeSimulatorWithPrompts("hi", [SimulatorTurn("done", "satisfied")], _q())
    events = []
    res = run_persona_eval(
        session,
        _persona(),
        "desc",
        PersonaEvalConfig(domain="game", max_turns=1),
        sim,
        created_at="t",
        on_event=events.append,
    )

    assert res.prompts == {"personaPrompt": "persona prompt", "taskPrompt": "task prompt"}
    assert res.to_dict()["prompts"] == res.prompts
    assert events[0] == {"type": "prompts", "prompts": res.prompts}
