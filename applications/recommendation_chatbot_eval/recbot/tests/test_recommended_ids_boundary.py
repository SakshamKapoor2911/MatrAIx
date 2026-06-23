"""Regression for BUG #10: recommendations must not leak across turns.

``_recommended_item_ids`` scans the agent's cross-turn ``candidate_buffer.tracker``
for the last Map output. Without a per-turn boundary, a turn that only asks a
clarifying question (no Map executed this turn) re-returns the PREVIOUS turn's
recommendations. The ``start`` index bounds the scan to entries appended during
the current turn.
"""

from recbot.interecagent_bridge import _recommended_item_ids


class _FakeCorpus:
    """Resolves recommended titles to ids the way BaseGallery does."""

    def __init__(self, title_to_id: dict[str, str]) -> None:
        self._title_to_id = title_to_id

    def convert_title_2_info(self, titles, col_names):
        return {col_names: [self._title_to_id[t] for t in titles]}


class _FakeBuffer:
    def __init__(self, tracker: list[dict]) -> None:
        self.tracker = tracker


class _FakeAgent:
    def __init__(self, tracker: list[dict], title_to_id: dict[str, str]) -> None:
        self.candidate_buffer = _FakeBuffer(tracker)
        self.item_corups = _FakeCorpus(title_to_id)


def _map_entry(titles: list[str]) -> dict:
    return {"tool": "Map Tool", "output": "Here are recommendations:" + ";".join(titles)}


def test_clarifying_turn_does_not_leak_previous_recommendations():
    # Turn 1 ran a Map (index 0); turn 2 only asked a question (no Map at >= start).
    tracker = [_map_entry(["Halo"])]
    agent = _FakeAgent(tracker, {"Halo": "111"})

    # Turn-1 view (start=0) sees the Map output.
    assert _recommended_item_ids(agent, start=0) == ["111"]

    # Turn-2 view starts after the turn-1 Map entry: no Map this turn -> [].
    assert _recommended_item_ids(agent, start=len(tracker)) == []


def test_uses_only_current_turn_map_when_a_newer_one_exists():
    # Turn 1 Map at index 0, then turn 2 appends its own Map at index 1.
    tracker = [_map_entry(["Halo"]), _map_entry(["Doom"])]
    agent = _FakeAgent(tracker, {"Halo": "111", "Doom": "222"})

    # Scanning from the start of turn 2 returns only turn 2's recommendation.
    assert _recommended_item_ids(agent, start=1) == ["222"]


def test_default_start_scans_whole_tracker():
    tracker = [_map_entry(["Halo"])]
    agent = _FakeAgent(tracker, {"Halo": "111"})
    assert _recommended_item_ids(agent) == ["111"]


def test_robust_to_missing_attributes():
    class _Bare:
        pass

    assert _recommended_item_ids(_Bare(), start=0) == []
