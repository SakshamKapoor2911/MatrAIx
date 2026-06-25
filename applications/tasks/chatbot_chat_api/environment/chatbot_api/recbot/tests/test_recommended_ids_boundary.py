"""Regression for BUG #10: recommendations must not leak across turns.

``_recommended_item_ids`` scans the agent's cross-turn ``candidate_buffer.tracker``
for the last Map output. Without a per-turn boundary, a turn that only asks a
clarifying question (no Map executed this turn) re-returns the PREVIOUS turn's
recommendations. The ``start`` index bounds the scan to entries appended during
the current turn.
"""

from recbot.interecagent_bridge import (
    _choose_recommended_item_ids,
    _recommended_item_ids,
    _recommended_item_ids_from_response_text,
)


class _FakeCorpus:
    """Resolves recommended titles to ids the way BaseGallery does."""

    def __init__(self, title_to_id: dict[str, str]) -> None:
        self._title_to_id = title_to_id
        self._id_to_title = {item_id: title for title, item_id in title_to_id.items()}

    def fuzzy_match(self, titles, col_name):
        assert col_name == "title"
        matches = []
        for title in titles:
            title_lower = title.lower()
            for known in self._title_to_id:
                if title_lower in known.lower() or known.lower() in title_lower:
                    matches.append(known)
                    break
            else:
                matches.append(next(iter(self._title_to_id)))
        return matches

    def convert_title_2_info(self, titles, col_names):
        return {col_names: [self._title_to_id[t] for t in titles]}

    def convert_id_2_info(self, ids, col_names):
        return {col_names: [self._id_to_title[str(item_id)] for item_id in ids]}


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


def test_response_text_grounding_extracts_catalog_titles():
    agent = _FakeAgent(
        [],
        {
            "In the Mood For Love (Fa yeung nin wa)": "3313",
            "Goya in Bordeaux (Goya en Burdeos)": "7848",
            "Yi Yi": "3695",
        },
    )
    response = """
    Here are my top picks:
    1. **In the Mood for Love** - atmospheric and visually rich.
    2. **Goya in Bordeaux** - art and historical biography.
    3. **Yi Yi** - patient family drama.
    """

    assert _recommended_item_ids_from_response_text(agent, response) == [
        "3313",
        "7848",
        "3695",
    ]


def test_response_text_grounding_handles_trailing_article_titles():
    agent = _FakeAgent([], {"Debut, The": "8765"})

    assert _recommended_item_ids_from_response_text(
        agent, "1. **The Debut** - a cultural coming-of-age story."
    ) == ["8765"]


def test_response_text_grounding_rejects_unsafe_one_word_article_match():
    agent = _FakeAgent([], {"Farewell My Concubine (Ba wang bie ji)": "151"})

    assert _recommended_item_ids_from_response_text(
        agent, "1. **The Farewell** - family and cultural identity."
    ) == []


def test_response_text_grounding_replaces_map_ids_not_mentioned_in_answer():
    agent = _FakeAgent(
        [],
        {
            "Ransom": "1135",
            "In the Mood For Love (Fa yeung nin wa)": "3313",
        },
    )

    assert _choose_recommended_item_ids(
        agent,
        ["1135"],
        "My strongest pick is **In the Mood for Love** for its atmosphere.",
    ) == ["3313"]


def test_response_text_grounding_keeps_map_ids_mentioned_in_answer():
    agent = _FakeAgent(
        [],
        {
            "Ransom": "1135",
            "In the Mood For Love (Fa yeung nin wa)": "3313",
        },
    )

    assert _choose_recommended_item_ids(
        agent,
        ["1135"],
        "1. **Ransom** - a tense drama.",
    ) == ["1135"]
