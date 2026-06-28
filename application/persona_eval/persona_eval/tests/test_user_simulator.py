from persona_eval.goal_contexts import get_goal_context
from persona_eval.persona import get_persona
from persona_eval.user_simulator import UserSimulator
from persona_eval.types import Persona, Questionnaire, SimulatorTurn, PersonaEvalTurn


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete_json(self, system, user):
        self.calls.append((system, user))
        return self.payload

    @property
    def last_system(self):
        return self.calls[-1][0]

    @property
    def last_user(self):
        return self.calls[-1][1]


def _curated_persona():
    return get_persona("Nemotron_01B0D4D4")


def _fixture_persona():
    return Persona(id="p", name="Marco", summary="lapsed co-op gamer",
                   preferences=["co-op"], dislikes=["grind"], constraints=["PC"],
                   goal="find a co-op game", communication_style="casual")


def _gc():
    return get_goal_context("scenario_default")


def _transcript():
    return [PersonaEvalTurn(turn_index=0, user_message="hi", assistant_message="what platform?")]


def _final_items():
    return [{"id": "1", "title": "A"}]


def test_kickoff_uses_goal_context_template():
    fake = FakeClient({"message": "hi there"})
    sim = UserSimulator(fake, _gc())
    msg = sim.kickoff(_curated_persona(), "a movie recommender")
    assert msg == "hi there"
    assert "{persona_context}" not in fake.last_system  # template was formatted
    assert "movie" in fake.last_system


def test_final_feedback_returns_questionnaire():
    fake = FakeClient({"constraintSatisfaction": 4, "preferenceSatisfaction": 5,
                       "overallRating": 9, "ratingReason": "great",
                       "askedUsefulClarifyingQuestions": True, "clarifyingNotes": "asked budget"})
    sim = UserSimulator(fake, _gc())
    q = sim.final_feedback(_curated_persona(), "sut", _transcript(), _final_items())
    assert isinstance(q, Questionnaire)
    assert q.overall_rating == 9 and q.constraint_satisfaction == 4


def test_kickoff_returns_message_string():
    client = FakeClient({"message": "Hey, looking for a co-op game for me and two friends."})
    sim = UserSimulator(client, _gc())
    msg = sim.kickoff(_fixture_persona(), "You are chatting with a game recommender.")
    assert "co-op" in msg
    # kickoff prompt must carry persona context + the instruction to not reveal everything at once
    sys_prompt, _ = client.calls[0]
    assert "Marco" in sys_prompt and "not reveal everything" in sys_prompt.lower()


def test_respond_returns_simulator_turn_with_decision():
    client = FakeClient({"message": "That sounds good, thanks!", "decision": "satisfied",
                         "note": "the second pick fits"})
    sim = UserSimulator(client, _gc())
    turn = sim.respond(_fixture_persona(), "desc", [("hi", "what platform?")],
                       "Here are two co-op games: A; B", [{"id": "1", "title": "A"}])
    assert isinstance(turn, SimulatorTurn)
    assert turn.decision == "satisfied" and "thanks" in turn.message


def test_respond_defaults_bad_decision_to_continue():
    client = FakeClient({"message": "more please", "decision": "weird"})
    sim = UserSimulator(client, _gc())
    turn = sim.respond(_fixture_persona(), "desc", [], "anything else?", [])
    assert turn.decision == "continue"


def test_final_feedback_clamps_out_of_range_numbers():
    fake = FakeClient({"constraintSatisfaction": 99, "preferenceSatisfaction": -3,
                       "overallRating": 50})
    sim = UserSimulator(fake, _gc())
    q = sim.final_feedback(_fixture_persona(), "sut", _transcript(), _final_items())
    assert q.constraint_satisfaction == 5
    assert q.preference_satisfaction == 1
    assert q.overall_rating == 10
