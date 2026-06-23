"""Studio run configuration and its mapping to ``INTERECAGENT_*`` env vars.

A Studio "config" is a small dict that controls how the in-process RecAI agent
is built and how it ranks/serves recommendations. :class:`ConfigManager` is the
single source of truth for:

* the **allowed** values for each config key (``options``),
* the **defaults**,
* **validation** of a candidate config,
* the translation of a config to the ``INTERECAGENT_*`` environment variables
  that :func:`recbot.interecagent_bridge.run_turn` reads, and
* whether a config change **invalidates the cached agent** (so the API can warn
  the user that the next turn will pay a cold start again).

The module imports only the stdlib so it is safe to import anywhere.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

__all__ = ["ConfigError", "ConfigManager"]


class ConfigError(ValueError):
    """Raised when a Studio config fails validation."""


class ConfigManager:
    """Validate Studio configs and map them to backend environment variables.

    The class is effectively a namespace of class attributes / class methods;
    there is no per-instance state, but it is instantiated by the API so it can
    be swapped or extended in tests.
    """

    #: Allowed values for each config key. Order is meaningful: the first entry
    #: of each list is the canonical default surfaced in :attr:`DEFAULTS`.
    ALLOWED: Dict[str, List[str]] = {
        "engine": ["gpt-4o-mini", "gpt-4o"],
        "rankerMode": ["native"],
        "resourceMode": ["recai_resources"],
        "domain": ["movie", "beauty_product", "game"],
        "botType": ["chat", "completion"],
    }

    #: Default config used for brand-new sessions.
    DEFAULTS: Dict[str, str] = {
        "engine": "gpt-4o-mini",
        "rankerMode": "native",
        "resourceMode": "recai_resources",
        "domain": "movie",
        "botType": "chat",
    }

    #: Config keys whose change requires rebuilding (re-warming) the cached
    #: agent, because they alter agent construction / resources rather than
    #: just per-turn behavior.
    CACHE_INVALIDATING_KEYS: List[str] = [
        "engine",
        "rankerMode",
        "resourceMode",
        "domain",
        "botType",
    ]

    #: The user-editable knobs surfaced in the config bar, in display order.
    #: ``rankerMode`` / ``resourceMode`` are intentionally excluded — each has a
    #: single allowed value and is reported instead as a read-only fact in
    #: :attr:`ENVIRONMENT` (the native SASRec ranker / the ``all_resources``
    #: bundle), so the UI does not present a choice where none exists.
    EDITABLE_KEYS: List[str] = ["engine", "domain", "botType"]

    #: Human-readable metadata per editable knob: a label, a one-line
    #: description, and per-value labels/descriptions. Keyed by config key; the
    #: allowed values come from :attr:`ALLOWED` so the two cannot drift.
    KNOB_META: Dict[str, Dict[str, object]] = {
        "engine": {
            "label": "Model",
            "description": "The OpenAI chat model that plans tool use and writes "
            "the assistant's replies.",
            "values": {
                "gpt-4o-mini": {
                    "label": "GPT-4o mini",
                    "description": "Faster and cheaper; the default.",
                },
                "gpt-4o": {
                    "label": "GPT-4o",
                    "description": "Higher quality, slower and pricier.",
                },
            },
        },
        "domain": {
            "label": "Domain",
            "description": "Which catalog the recommender draws from. Changing it "
            "rebuilds the agent against that domain's resources.",
            "values": {
                "movie": {
                    "label": "Movies",
                    "description": "The movie recommendation catalog.",
                },
                "beauty_product": {
                    "label": "Beauty products",
                    "description": "The beauty-product recommendation catalog.",
                },
                "game": {
                    "label": "Games",
                    "description": "The video-game recommendation catalog.",
                },
            },
        },
        "botType": {
            "label": "Reply style",
            "description": "How the agent is prompted to converse. Changing it "
            "rebuilds the agent (it is part of the agent's cache key).",
            "values": {
                "chat": {
                    "label": "Chat",
                    "description": "Conversational, multi-turn replies.",
                },
                "completion": {
                    "label": "Completion",
                    "description": "Single-shot completion-style replies.",
                },
            },
        },
    }

    #: Read-only facts about the fixed parts of the stack, surfaced alongside the
    #: editable knobs so the UI can show what is *not* configurable and why.
    ENVIRONMENT: Dict[str, str] = {
        "ranker": "SASRec (native)",
        "resources": "all_resources",
        "agent": "InteRecAgent",
    }

    def options(self) -> Dict[str, object]:
        """Return the config metadata the UI renders.

        Shape::

            {
              "knobs": [
                {
                  "key": "engine",
                  "label": "Model",
                  "description": "...",
                  "options": [
                    {"value": "gpt-4o-mini", "label": "...", "description": "..."},
                    ...
                  ],
                  "rebuildsAgent": false
                },
                ...
              ],
              "defaults": {<full config defaults>},
              "environment": {"ranker": "...", "resources": "...", "agent": "..."}
            }

        ``knobs`` covers only the user-editable keys (:attr:`EDITABLE_KEYS`), each
        enriched from :attr:`KNOB_META` with per-value labels/descriptions and a
        ``rebuildsAgent`` flag (whether changing it cold-starts the agent —
        :attr:`CACHE_INVALIDATING_KEYS`). ``defaults`` is the *full* canonical
        config (all keys, including the fixed ranker/resource modes) so callers
        can still seed a complete session. ``environment`` reports the fixed
        parts of the stack as read-only facts.
        """
        knobs: List[Dict[str, object]] = []
        for key in self.EDITABLE_KEYS:
            meta = self.KNOB_META.get(key, {})
            value_meta = meta.get("values", {})
            value_meta = value_meta if isinstance(value_meta, dict) else {}
            option_views: List[Dict[str, str]] = []
            for value in self.ALLOWED.get(key, []):
                vm = value_meta.get(value, {})
                vm = vm if isinstance(vm, dict) else {}
                option_views.append(
                    {
                        "value": value,
                        "label": str(vm.get("label", value)),
                        "description": str(vm.get("description", "")),
                    }
                )
            knobs.append(
                {
                    "key": key,
                    "label": str(meta.get("label", key)),
                    "description": str(meta.get("description", "")),
                    "options": option_views,
                    "rebuildsAgent": key in self.CACHE_INVALIDATING_KEYS,
                }
            )
        return {
            "knobs": knobs,
            "defaults": dict(self.DEFAULTS),
            "environment": dict(self.ENVIRONMENT),
        }

    def normalize(self, cfg: Optional[Dict[str, object]]) -> Dict[str, str]:
        """Return a full, validated config, filling missing keys from defaults.

        Unknown keys are rejected (raises :class:`ConfigError`). The returned
        dict is a fresh copy containing exactly the keys in :attr:`DEFAULTS`.
        """
        merged: Dict[str, str] = dict(self.DEFAULTS)
        if cfg:
            for key, value in cfg.items():
                if key not in self.ALLOWED:
                    raise ConfigError("Unknown config key: {!r}".format(key))
                merged[key] = value  # type: ignore[assignment]
        self.validate(merged)
        return merged

    def validate(self, cfg: Dict[str, object]) -> None:
        """Validate a (possibly partial) config; raise on the first problem.

        Each present key must be one of :attr:`ALLOWED`; each value must be in
        the allowed list for that key. Missing keys are permitted here so the
        method can be used on patches; use :meth:`normalize` to also fill
        defaults.
        """
        if not isinstance(cfg, dict):
            raise ConfigError("config must be an object/dict")
        for key, value in cfg.items():
            if key not in self.ALLOWED:
                raise ConfigError("Unknown config key: {!r}".format(key))
            allowed = self.ALLOWED[key]
            if value not in allowed:
                raise ConfigError(
                    "Invalid value {!r} for {!r}; allowed: {}".format(
                        value, key, ", ".join(allowed)
                    )
                )

    def to_env(self, cfg: Dict[str, object]) -> Dict[str, str]:
        """Translate a config to the ``INTERECAGENT_*`` environment variables.

        The input is normalized first (defaults filled, validated), so callers
        may pass a partial config. ``INTERECAGENT_CACHE_AGENT`` is always set to
        ``'1'`` so the backend reuses its module-global agent cache.
        """
        full = self.normalize(cfg)
        return {
            "INTERECAGENT_ENGINE": str(full["engine"]),
            "INTERECAGENT_RANKER_MODE": str(full["rankerMode"]),
            "INTERECAGENT_RESOURCE_MODE": str(full["resourceMode"]),
            "INTERECAGENT_DOMAIN": str(full["domain"]),
            "INTERECAGENT_BOT_TYPE": str(full["botType"]),
            "INTERECAGENT_CACHE_AGENT": "1",
        }

    def apply(
        self,
        cfg: Dict[str, object],
        environ: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Write the config's ``INTERECAGENT_*`` variables into the environment.

        Computes :meth:`to_env` (which normalizes + validates ``cfg``) and sets
        each variable on ``environ`` (defaulting to :data:`os.environ`). This is
        called by the session right before invoking the backend so the cached
        agent is (re)built with the active knobs. Returns the env dict applied.
        """
        target = os.environ if environ is None else environ
        env = self.to_env(cfg)
        for key, value in env.items():
            target[key] = value
        return env

    def cache_invalidating(
        self, old: Optional[Dict[str, object]], new: Optional[Dict[str, object]]
    ) -> bool:
        """Return ``True`` if moving from ``old`` to ``new`` rebuilds the agent.

        A change to any of :attr:`CACHE_INVALIDATING_KEYS`
        (engine / rankerMode / resourceMode / domain / botType) invalidates the
        cached agent — ``botType`` is included because the bridge folds
        ``INTERECAGENT_BOT_TYPE`` into its agent cache key. Both configs are
        normalized first so that "default vs. explicit-default" comparisons do
        not register as changes.
        """
        old_full = self.normalize(old)
        new_full = self.normalize(new)
        for key in self.CACHE_INVALIDATING_KEYS:
            if old_full.get(key) != new_full.get(key):
                return True
        return False
