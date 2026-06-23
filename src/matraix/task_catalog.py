"""Canonical metadata for MatrAIx example tasks (application + persona bench).

Domain / vertical (first focus set):
  software | finance | healthcare | commerce-retail

Tags are **task topic** labels (what the scenario is about). Use short
human-readable phrases (spaces allowed). Do not repeat ``type`` / ``domain``.

Harbor also supports ``[task].keywords`` for registry package search; MatrAIx
example tasks omit it and use ``metadata.tags`` only.

Harbor ``[task].name`` (exactly one ``/``):

- Application tasks: ``matraix/application-{slug}``
- Persona bench (1 dim): ``matraix/persona-bench-dim-{NNN}-{slug}`` when ``bench_dim_index`` is set in catalog
- Persona bench (no dim): ``matraix/persona-bench-{slug}``
"""

from __future__ import annotations

DOMAIN_SOFTWARE = "software"
DOMAIN_FINANCE = "finance"
DOMAIN_HEALTHCARE = "healthcare"
DOMAIN_COMMERCE_RETAIL = "commerce-retail"

EXAMPLE_TASK_METADATA: dict[str, dict[str, object]] = {
    "example-survey_product-feedback": {
        "type": "survey",
        "domain": DOMAIN_SOFTWARE,
        "bench_dim_index": 47,
        "bench_dim_id": "economic_motivation",
        "tags": [
            "ClearQueue",
            "product concept",
            "subscription pricing",
            "tier selection",
            "spending posture",
        ],
        "grounding": {
            "probe_dimension": "dimensions.economic_motivation",
            "confounders": {
                "socioeconomic_band": {
                    "value": "Middle",
                    "rationale": (
                        "Income band directly shifts price acceptability on billing and "
                        "overall pricing items (q2, q3, q6); extremes pull toward premium "
                        "or cost-sensitive MCQs independent of spending posture."
                    ),
                    "affects_questions": ["q2", "q3", "q6"],
                },
                "age_bracket": {
                    "value": "25-34",
                    "rationale": (
                        "Teens vs adults differ on subscriptions and promos (q0, q3); "
                        "mid-adult band reduces life-stage confounding with the probe."
                    ),
                    "affects_questions": ["q0", "q3"],
                },
                "risk_tolerance": {
                    "value": "Balanced",
                    "rationale": (
                        "Extreme risk appetite skews annual prepay and promo uptake "
                        "(q2, q3) without reflecting economic_motivation alone."
                    ),
                    "affects_questions": ["q2", "q3"],
                },
                "tech_savviness": {
                    "value": "Comfortable",
                    "rationale": (
                        "Very low or avoidant tech comfort changes willingness to try "
                        "paid tiers (q0, q1) separately from spending posture."
                    ),
                    "affects_questions": ["q0", "q1"],
                },
            },
        },
    },
    "example-chat-api_support_chatbot": {
        "type": "chat",
        "domain": DOMAIN_COMMERCE_RETAIL,
        "tags": [
            "acme support",
            "missing delivery",
            "order 4521",
            "multi turn support",
            "delivery investigation",
        ],
    },
    "example-chat-mcp_support_chatbot": {
        "type": "chat",
        "domain": DOMAIN_COMMERCE_RETAIL,
        "tags": [
            "acme support",
            "missing delivery",
            "order 4521",
            "multi turn support",
            "delivery investigation",
        ],
    },
    "example-web-playwright_books-interest": {
        "type": "web",
        "domain": DOMAIN_COMMERCE_RETAIL,
        "tags": [
            "books toscrape",
            "fiction catalog",
            "book purchase intent",
            "online bookshop",
        ],
    },
    "example-web-browser-use_books-interest": {
        "type": "web",
        "domain": DOMAIN_COMMERCE_RETAIL,
        "tags": [
            "books toscrape",
            "fiction catalog",
            "book purchase intent",
            "online bookshop",
        ],
    },
    "example-web-cocoa_books-interest": {
        "type": "web",
        "domain": DOMAIN_COMMERCE_RETAIL,
        "tags": [
            "books toscrape",
            "fiction catalog",
            "book purchase intent",
            "online bookshop",
        ],
    },
    "example-web-cua_books-interest": {
        "type": "web",
        "domain": DOMAIN_COMMERCE_RETAIL,
        "tags": [
            "books toscrape",
            "fiction catalog",
            "book purchase intent",
            "online bookshop",
        ],
    },
    "example-computer-use-macos_notification-preferences": {
        "type": "desktop",
        "domain": DOMAIN_SOFTWARE,
        "tags": [
            "notification permissions",
            "do not disturb",
            "app notifications",
            "system settings",
        ],
    },
    "example-computer-use-ios_notification-preferences": {
        "type": "mobile",
        "domain": DOMAIN_SOFTWARE,
        "tags": [
            "notification permissions",
            "do not disturb",
            "app notifications",
            "system settings",
        ],
    },
    "example-computer-use-linux_notification-preferences": {
        "type": "desktop",
        "domain": DOMAIN_SOFTWARE,
        "tags": [
            "notification permissions",
            "do not disturb",
            "app notifications",
            "system settings",
        ],
    },
}


def _example_slug(dirname: str) -> str:
    slug = dirname.replace("_", "-")
    if slug.startswith("example-"):
        slug = slug[len("example-") :]
    return slug


def application_harbor_name(dirname: str) -> str:
    """Harbor registry name for an application/tasks/<dirname> folder."""
    return f"matraix/application-{_example_slug(dirname)}"


def persona_bench_harbor_name(dirname: str, *, bench_dim_index: int | None = None) -> str:
    """Harbor registry name for a persona/tasks/<dirname> folder."""
    slug = _example_slug(dirname)
    if bench_dim_index is not None:
        return f"matraix/persona-bench-dim-{bench_dim_index:03d}-{slug}"
    return f"matraix/persona-bench-{slug}"


def build_application_task_toml_dict(dirname: str, *, difficulty: str = "easy") -> dict:
    """Build task.toml content from ``task_catalog`` for an application task."""
    if dirname not in EXAMPLE_TASK_METADATA:
        raise KeyError(
            f"No catalog entry for {dirname!r}; add it to EXAMPLE_TASK_METADATA first"
        )
    data: dict = {
        "version": "1.0",
        "artifacts": ["/app/output"],
        "task": {"name": application_harbor_name(dirname)},
        "metadata": {"difficulty": difficulty},
        "verifier": {"timeout_sec": 120.0},
        "agent": {"timeout_sec": 600.0},
        "environment": {
            "build_timeout_sec": 600.0,
            "cpus": 1,
            "memory_mb": 2048,
            "storage_mb": 10240,
            "gpus": 0,
        },
    }
    apply_example_metadata(data, dirname)
    return data


def build_persona_task_toml_dict(dirname: str, *, difficulty: str = "easy") -> dict:
    """Build task.toml content from ``task_catalog`` for *dirname*."""
    if dirname not in EXAMPLE_TASK_METADATA:
        raise KeyError(
            f"No catalog entry for {dirname!r}; add it to EXAMPLE_TASK_METADATA first"
        )
    spec = EXAMPLE_TASK_METADATA[dirname]
    dim_index = spec.get("bench_dim_index")
    bench_dim_index = int(dim_index) if dim_index is not None else None
    data: dict = {
        "version": "1.0",
        "artifacts": ["/app/output"],
        "task": {
            "name": persona_bench_harbor_name(
                dirname, bench_dim_index=bench_dim_index
            )
        },
        "metadata": {"difficulty": difficulty},
        "verifier": {"timeout_sec": 120.0},
        "agent": {"timeout_sec": 600.0},
        "environment": {
            "build_timeout_sec": 600.0,
            "cpus": 1,
            "memory_mb": 2048,
            "storage_mb": 10240,
            "gpus": 0,
        },
    }
    apply_example_metadata(data, dirname)
    return data


def apply_example_metadata(data: dict, dirname: str) -> None:
    """Merge catalog metadata into a parsed task.toml dict."""
    spec = EXAMPLE_TASK_METADATA.get(dirname)
    if spec is None:
        return
    task = data.setdefault("task", {})
    task.pop("keywords", None)

    meta = data.setdefault("metadata", {})
    meta.pop("category", None)
    extra = {
        k: v
        for k, v in meta.items()
        if k not in {"difficulty", "type", "domain", "tags", "bench_dim_index"}
    }
    ordered: dict[str, object] = {
        "difficulty": meta.get("difficulty", "easy"),
        "type": spec["type"],
        "domain": spec["domain"],
        "tags": list(spec["tags"]),
    }
    ordered.update(extra)
    data["metadata"] = ordered


def task_dirname_from_harbor_path(task_path: str) -> str:
    """``persona/tasks/example-survey_product-feedback`` → ``example-survey_product-feedback``."""
    name = task_path.rstrip("/").split("/")[-1]
    if not name.startswith("example-"):
        raise ValueError(f"Expected an example task path, got {task_path!r}")
    return name


def get_task_catalog_entry(task_path: str) -> dict[str, object] | None:
    dirname = task_dirname_from_harbor_path(task_path)
    spec = EXAMPLE_TASK_METADATA.get(dirname)
    return dict(spec) if spec is not None else None


def get_task_grounding_spec(task_path: str) -> dict[str, object] | None:
    """Return grounding config for a persona bench task, if defined in catalog."""
    entry = get_task_catalog_entry(task_path)
    if entry is None:
        return None
    grounding = entry.get("grounding")
    if not isinstance(grounding, dict):
        return None
    return dict(grounding)


def confounder_values_from_grounding(
    grounding: dict[str, object],
) -> dict[str, str]:
    """Extract dimension_id → fixed value from catalog confounder entries."""
    raw = grounding.get("confounders")
    if not isinstance(raw, dict):
        return {}
    values: dict[str, str] = {}
    for dim_id, spec in raw.items():
        if isinstance(spec, str):
            values[str(dim_id)] = spec
            continue
        if isinstance(spec, dict) and spec.get("value") is not None:
            values[str(dim_id)] = str(spec["value"])
    return values


def probe_dimension_from_grounding(grounding: dict[str, object]) -> str | None:
    probe = grounding.get("probe_dimension")
    return str(probe) if probe else None

