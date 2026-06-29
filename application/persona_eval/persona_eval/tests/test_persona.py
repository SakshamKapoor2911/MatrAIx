import pytest
from persona_eval.persona import load_personas, get_persona


def test_loads_curated_catalog():
    ps = load_personas()
    ids = [p.id for p in ps]
    assert len(ids) == len(set(ids))            # unique ids
    # The 336 curated personas are the whole catalog (no synthetic fixtures).
    assert len(ps) == 336
    # Every persona's source is the curated dataset it came from.
    assert all(p.source for p in ps)
    assert "synthetic" not in {p.source for p in ps}


def test_curated_persona_has_rich_context_and_no_domain():
    p = get_persona("Nemotron_01B0D4D4")
    assert "financial" in p.context.lower()     # from the YAML's persona text
    assert not hasattr(p, "domain")


def test_search_and_limit():
    hits = load_personas(query="software", limit=5)
    assert 0 < len(hits) <= 5
    assert all("software" in (h.name + h.context).lower() for h in hits)


def test_get_unknown_raises():
    with pytest.raises(KeyError):
        get_persona("nope")


def test_context_humanizes_enum_values():
    """Snake_case enum values render humanized for display, not raw.

    The curated YAML stores fields like ``occupation: financial_manager`` and
    ``marital_status: married_present``; the rendered context (shown verbatim in
    the persona drawer) must read as ``Financial Manager`` / ``Married Present``
    rather than leaking the raw tokens.
    """
    ctx = get_persona("Nemotron_01B0D4D4").context
    assert "Financial Manager" in ctx
    assert "Married Present" in ctx
    assert "financial_manager" not in ctx
    assert "married_present" not in ctx


def test_humanizing_preserves_free_text_and_proper_nouns():
    """Multi-word / already-cased values (cities, sentences) pass through as-is."""
    ctx = get_persona("Nemotron_01B0D4D4").context
    # "Bel Air" is a city value with a space — must not be mangled.
    assert "Bel Air" in ctx


def test_long_persona_context_is_complete_not_capped():
    """A persona whose profile exceeds the old 4000-char cap is rendered in full.

    `context` is both what the drawer shows *and* the user-simulator's persona
    prompt, so truncating it mid-word (which hit ~half the catalog) both crops
    the UI and degrades the eval. The rendered context must equal the complete
    profile, with no length cap.
    """
    import yaml

    from persona_eval import persona as P

    data = yaml.safe_load(
        (P._CURATED_DIR / "Nemotron_01B0D4D4.yaml").read_text(encoding="utf-8")
    )
    full = "\n".join(
        P._render({k: v for k, v in data.items() if k not in P._SKIP_KEYS})
    ).strip()
    assert len(full) > 4000  # this persona genuinely exceeds the old cap
    assert get_persona("Nemotron_01B0D4D4").context == full  # not truncated
