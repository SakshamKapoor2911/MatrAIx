"""Tests for :class:`backend.service.config.ConfigManager` options metadata."""

from __future__ import annotations


def test_domain_allows_all_three(config_manager):
    # ALLOWED still carries every domain; validation accepts each.
    assert set(config_manager.ALLOWED["domain"]) == {"movie", "beauty_product", "game"}
    for d in ("movie", "beauty_product", "game"):
        config_manager.validate({"domain": d})  # must not raise


def test_options_returns_enriched_knobs(config_manager):
    opts = config_manager.options()
    assert set(opts.keys()) == {"knobs", "defaults", "environment"}

    knobs = {k["key"]: k for k in opts["knobs"]}
    # Editable knobs only — rankerMode / resourceMode are environment facts.
    assert set(knobs.keys()) == {"engine", "domain", "botType"}

    for knob in opts["knobs"]:
        assert set(knob.keys()) >= {
            "key",
            "label",
            "description",
            "options",
            "rebuildsAgent",
        }
        assert knob["label"]  # non-empty human label
        assert isinstance(knob["rebuildsAgent"], bool)
        for option in knob["options"]:
            assert set(option.keys()) >= {"value", "label", "description"}
            assert option["label"]


def test_options_knob_values_match_allowed(config_manager):
    opts = config_manager.options()
    knobs = {k["key"]: k for k in opts["knobs"]}
    for key in ("engine", "domain", "botType"):
        values = [o["value"] for o in knobs[key]["options"]]
        assert values == config_manager.ALLOWED[key]


def test_options_rebuilds_agent_flag(config_manager):
    knobs = {k["key"]: k for k in config_manager.options()["knobs"]}
    # Every editable knob feeds the bridge's agent cache key, so each one
    # rebuilds (re-warms) the agent when changed — including botType, which is
    # part of INTERECAGENT_BOT_TYPE in the agent cache key.
    assert knobs["domain"]["rebuildsAgent"] is True
    assert knobs["botType"]["rebuildsAgent"] is True
    assert knobs["engine"]["rebuildsAgent"] is True


def test_bottype_change_requires_rebuild(config_manager):
    # Changing only botType must invalidate the cached agent (cold start),
    # because the bridge folds INTERECAGENT_BOT_TYPE into its agent cache key.
    old = {"botType": "chat"}
    new = {"botType": "completion"}
    assert config_manager.cache_invalidating(old, new) is True
    # botType is enumerated among the cache-invalidating keys.
    assert "botType" in config_manager.CACHE_INVALIDATING_KEYS
    # Sanity: an unchanged config does not force a rebuild.
    assert config_manager.cache_invalidating(old, dict(old)) is False


def test_options_defaults_are_full_config(config_manager):
    defaults = config_manager.options()["defaults"]
    # Full config: every key, including the fixed ranker/resource modes.
    assert set(defaults.keys()) == {
        "engine",
        "rankerMode",
        "resourceMode",
        "domain",
        "botType",
    }
    assert defaults["engine"] == "gpt-4o-mini"
    assert defaults["domain"] == "movie"


def test_options_environment_block(config_manager):
    env = config_manager.options()["environment"]
    assert set(env.keys()) == {"ranker", "resources", "agent"}
    assert "SASRec" in env["ranker"]
    assert env["resources"] == "all_resources"
    assert env["agent"] == "InteRecAgent"
