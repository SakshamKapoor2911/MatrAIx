import pytest
from persona_eval.sut_descriptions import sut_description_for


def test_descriptions_exist_per_domain():
    for d in ("game", "movie", "beauty_product"):
        text = sut_description_for(d)
        assert isinstance(text, str) and len(text) > 40


def test_description_mentions_domain_noun():
    assert "game" in sut_description_for("game").lower()
    assert "movie" in sut_description_for("movie").lower()


def test_unknown_domain_raises():
    with pytest.raises(KeyError):
        sut_description_for("nope")
