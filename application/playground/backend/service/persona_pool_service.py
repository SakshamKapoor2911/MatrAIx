"""Persona pool catalog and sampling for Harbor job launch."""

from __future__ import annotations

import hashlib
import json
import re
import yaml
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from matraix.persona_dimension_catalog import values_for_dimension
from matraix.persona_job import (
    _stratify_bucket_key,
    load_manifest,
    sample_personas,
    sample_personas_stratified,
)

PERSONA_CARD_DIMENSIONS = (
    "age_bracket",
    "region",
    "domain",
    "intent",
    "life_stage",
    "source",
)

DEFAULT_PERSONA_POOL = "persona/datasets/bench-dev-sample"
GENERATED_DATASETS_DIR = "persona/datasets/_generated"
COHORTS_DIR = "persona/datasets/cohorts"
DIMENSION_CATEGORIES_PATH = "persona/schema/dimension_categories.json"
# Soft guard against accidental filter explosions during auto top-up /
# strategy-pool generation. Large cohort tasks (hundreds–thousands of
# strata cells) are supported; raise further if a strategy needs it.
MAX_FILTER_STRATA = 2048
DEFAULT_STRATEGY_STRATUM_MIN = 2
CohortKind = Literal["recipe", "frozen"]


def is_pool_coverage_error(message: str) -> bool:
    text = message or ""
    return (
        "exceeds matched pool size" in text
        or "No personas with stratify fields" in text
        or "sample_size_per_value_group=" in text
        or "Incomplete stratify coverage" in text
    )


def coverage_recovery_hint(*, task_path: str | None = None) -> str:
    cleaned = (task_path or "").strip().rstrip("/")
    strategy = (
        f"{cleaned}/persona_strategy.json"
        if cleaned
        else "application/tasks/<task>/persona_strategy.json"
    )
    return (
        "Auto pool top-up was unavailable or failed. Generate a local strategy "
        "pool manually, then retry:\n"
        f"  uv run python persona/scripts/generate_dev_personas.py --strategy {strategy}\n"
        'Point persona_strategy.json "pool" at the printed '
        "persona/datasets/_generated/... path (gitignored), or pass that pool when sampling."
    )


def with_coverage_hint(message: str, *, task_path: str | None = None) -> str:
    text = (message or "").strip()
    if not text or "generate_dev_personas.py --strategy" in text:
        return text
    if not is_pool_coverage_error(text):
        return text
    return f"{text}\n\n{coverage_recovery_hint(task_path=task_path)}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cohort_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ValueError("cohort id must not be empty")
    return slug


def _repo_root() -> Path:
    from playground.harbor.playground import _repo_root as harbor_root

    return harbor_root()



def _resolve_persona_yaml_path(
    repo_root: Path,
    entry: dict[str, Any],
    persona_id: str,
    pool_dir: Path,
) -> Path:
    candidates: list[Path] = []
    rel_path = str(entry.get("path") or "").strip()
    if rel_path:
        path = Path(rel_path)
        candidates.append(path if path.is_absolute() else repo_root / rel_path)
    pid = persona_id.strip()
    candidates.append(pool_dir / "persona_{}.yaml".format(pid))
    if pid.isdigit():
        candidates.append(pool_dir / "persona_{}.yaml".format(pid.zfill(4)))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0] if candidates else pool_dir / "persona_{}.yaml".format(pid)


def _persona_profile_markdown(
    *,
    persona_id: str,
    source: str,
    path: str,
    yaml_text: str,
) -> str:
    lines = ["**Persona ID:** `{}`".format(persona_id)]
    if source:
        lines.append("**Source:** {}".format(source))
    if path:
        lines.append("**Path:** `{}`".format(path))
    if yaml_text.strip():
        lines.extend(["", "```yaml", yaml_text.rstrip(), "```"])
    return "\n".join(lines)


@dataclass
class PersonaPoolService:
    repo_root: Path

    @classmethod
    def from_repo(cls, *, repo_root: Path | None = None) -> "PersonaPoolService":
        return cls(repo_root=Path(repo_root) if repo_root is not None else _repo_root())

    def _pool_dir(self, persona_pool: str) -> Path:
        return self.repo_root / persona_pool

    def _read_json(self, path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("{} must contain a JSON object".format(path.name))
        return payload

    def load_manifest_summary(self, persona_pool: str = DEFAULT_PERSONA_POOL) -> dict[str, Any]:
        pool_dir = self._pool_dir(persona_pool)
        manifest_path = pool_dir / "manifest.json"
        if not manifest_path.is_file():
            entries = load_manifest(pool_dir, repo_root=self.repo_root)
            return {
                "pool": persona_pool,
                "count": len(entries),
                "smokePersonaId": None,
                "sourceCounts": {},
                "schemaVersion": None,
                "dimensionCategoriesPath": DIMENSION_CATEGORIES_PATH,
            }
        manifest = self._read_json(manifest_path)
        return {
            "pool": persona_pool,
            "count": int(manifest.get("count") or len(manifest.get("personas") or [])),
            "smokePersonaId": manifest.get("smoke_persona_id"),
            "sourceCounts": dict(manifest.get("source_counts") or {}),
            "schemaVersion": manifest.get("schema_version"),
            "dimensionCategoriesPath": str(
                manifest.get("dimension_categories") or DIMENSION_CATEGORIES_PATH
            ),
        }

    def load_dimension_categories(
        self, *, path: str | None = None
    ) -> dict[str, Any]:
        rel = path or DIMENSION_CATEGORIES_PATH
        categories_path = Path(rel)
        if not categories_path.is_absolute():
            categories_path = self.repo_root / rel
        if not categories_path.is_file():
            return {
                "schemaVersion": "1.0",
                "personaSources": [],
                "devProfile": {"dimensionCount": None, "groups": []},
            }
        payload = self._read_json(categories_path)
        dev_profile = payload.get("devProfile")
        groups: list[dict[str, Any]] = []
        if isinstance(dev_profile, dict) and isinstance(dev_profile.get("groups"), list):
            for group in dev_profile["groups"]:
                if not isinstance(group, dict):
                    continue
                dimension_ids = list(group.get("dimensionIds") or [])
                dimensions = []
                for dim_id in dimension_ids:
                    dimensions.append(
                        {
                            "id": dim_id,
                            "values": values_for_dimension(str(dim_id)),
                        }
                    )
                groups.append(
                    {
                        "id": str(group.get("id") or ""),
                        "label": str(group.get("label") or ""),
                        "dimensionIds": dimension_ids,
                        "dimensions": dimensions,
                    }
                )
        return {
            "schemaVersion": payload.get("schemaVersion"),
            "personaSources": list(payload.get("personaSources") or []),
            "devProfile": {
                "dimensionCount": (
                    int(dev_profile.get("dimensionCount"))
                    if isinstance(dev_profile, dict) and dev_profile.get("dimensionCount")
                    else None
                ),
                "groups": groups,
            },
        }

    def get_catalog(self, persona_pool: str = DEFAULT_PERSONA_POOL) -> dict[str, Any]:
        summary = self.load_manifest_summary(persona_pool)
        categories = self.load_dimension_categories(
            path=str(summary.get("dimensionCategoriesPath") or DIMENSION_CATEGORIES_PATH)
        )
        return {**summary, "dimensionCategories": categories}

    def _normalize_dimension_filters(
        self, dimension_filters: dict[str, str | list[str]] | None
    ) -> dict[str, str | list[str]]:
        if not dimension_filters:
            return {}
        normalized: dict[str, str | list[str]] = {}
        for key, value in dimension_filters.items():
            if isinstance(value, list):
                cleaned = [str(item).strip() for item in value if str(item).strip()]
                if cleaned:
                    normalized[str(key)] = cleaned
            elif str(value).strip():
                normalized[str(key)] = str(value).strip()
        return normalized

    def _entry_dimensions(self, entry: dict[str, Any]) -> dict[str, Any] | None:
        dims = entry.get("dimensions")
        if isinstance(dims, dict):
            return dims
        from matraix.persona_job import _persona_dimensions

        loaded = _persona_dimensions(entry, repo_root=self.repo_root)
        return loaded if isinstance(loaded, dict) else None

    def _entry_matches_dimension_filters(
        self,
        entry: dict[str, Any],
        dimension_filters: dict[str, str | list[str]],
    ) -> bool:
        if not dimension_filters:
            return True
        dims = self._entry_dimensions(entry)
        if not dims:
            return False
        for key, value in dimension_filters.items():
            actual = dims.get(key)
            if isinstance(value, list):
                if actual not in value:
                    return False
            elif actual != value:
                return False
        return True

    def filter_pool(
        self,
        *,
        persona_pool: str = DEFAULT_PERSONA_POOL,
        sources: list[str] | None = None,
        dimension_filters: dict[str, str | list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        pool_dir = self._pool_dir(persona_pool)
        entries = load_manifest(pool_dir, repo_root=self.repo_root)
        matched = list(entries)
        if sources:
            allowed = {source.strip() for source in sources if source.strip()}
            matched = [
                entry
                for entry in matched
                if str(entry.get("source") or "").strip() in allowed
            ]
        filters = self._normalize_dimension_filters(dimension_filters)
        if filters:
            matched = [
                entry
                for entry in matched
                if self._entry_matches_dimension_filters(entry, filters)
            ]
        return matched

    def _persona_card(self, entry: dict[str, Any]) -> dict[str, Any]:
        dims = entry.get("dimensions")
        if not isinstance(dims, dict):
            from matraix.persona_job import _persona_dimensions

            dims = _persona_dimensions(entry, repo_root=self.repo_root) or {}
        display = {
            key: str(dims[key])
            for key in PERSONA_CARD_DIMENSIONS
            if isinstance(dims, dict) and dims.get(key)
        }
        persona_id = str(entry.get("persona_id") or "")
        display_name = str(entry.get("display_name") or "").strip()
        if not display_name:
            rel_path = str(entry.get("path") or "").strip()
            if rel_path:
                yaml_path = self.repo_root / rel_path
                if yaml_path.is_file():
                    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        display_name = str(raw.get("display_name") or "").strip()
        if not display_name:
            from matraix.persona_display_name import synthetic_display_name

            display_name = synthetic_display_name(
                persona_id,
                dims if isinstance(dims, dict) else {},
            )
        return {
            "personaId": persona_id,
            "name": display_name,
            "source": str(entry.get("source") or ""),
            "path": str(entry.get("path") or ""),
            "dimensions": display,
        }

    def list_persona_cards(
        self,
        *,
        persona_pool: str = DEFAULT_PERSONA_POOL,
        limit: int = 10,
        offset: int = 0,
        persona_ids: list[str] | None = None,
        seed: int = 42,
        all_personas: bool = False,
    ) -> dict[str, Any]:
        import random

        pool_dir = self._pool_dir(persona_pool)
        entries = load_manifest(pool_dir, repo_root=self.repo_root)
        if persona_ids:
            wanted = {pid.strip() for pid in persona_ids if pid.strip()}
            chosen = [
                entry
                for entry in entries
                if str(entry.get("persona_id") or "") in wanted
            ]
        elif all_personas:
            sorted_entries = sorted(
                entries,
                key=lambda entry: str(entry.get("persona_id") or ""),
            )
            start = max(0, offset)
            end = start + max(1, limit)
            chosen = sorted_entries[start:end]
        else:
            summary = self.load_manifest_summary(persona_pool)
            smoke_id = str(summary.get("smokePersonaId") or "").strip()
            smoke_entry = next(
                (entry for entry in entries if str(entry.get("persona_id") or "") == smoke_id),
                None,
            )
            rest = [
                entry
                for entry in entries
                if str(entry.get("persona_id") or "") != smoke_id
            ]
            rng = random.Random(seed)
            rng.shuffle(rest)
            chosen = ([smoke_entry] if smoke_entry else []) + rest[: max(0, limit - 1)]
        cards = [self._persona_card(entry) for entry in chosen]
        if not all_personas:
            cards = cards[:limit]
        return {
            "pool": persona_pool,
            "personas": cards,
            "offset": max(0, offset) if all_personas else 0,
            "limit": limit,
        }

    def get_persona_detail(
        self,
        persona_id: str,
        *,
        persona_pool: str = DEFAULT_PERSONA_POOL,
    ) -> dict[str, Any]:
        pool_dir = self._pool_dir(persona_pool)
        entries = load_manifest(pool_dir, repo_root=self.repo_root)
        entry = next(
            (item for item in entries if str(item.get("persona_id") or "") == persona_id.strip()),
            None,
        )
        if entry is None and persona_id.strip().isdigit():
            padded = persona_id.strip().zfill(4)
            entry = next(
                (item for item in entries if str(item.get("persona_id") or "") == padded),
                None,
            )
        if entry is None:
            raise FileNotFoundError("persona not found: {}".format(persona_id))
        card = self._persona_card(entry)
        dims = entry.get("dimensions")
        if not isinstance(dims, dict):
            from matraix.persona_job import _persona_dimensions

            dims = _persona_dimensions(entry, repo_root=self.repo_root) or {}
        full_dimensions = {str(key): str(value) for key, value in dict(dims).items() if value}
        yaml_path = _resolve_persona_yaml_path(
            self.repo_root, entry, persona_id, pool_dir
        )
        yaml_text = yaml_path.read_text(encoding="utf-8") if yaml_path.is_file() else ""
        rel_path = str(entry.get("path") or card.get("path") or "")
        if not rel_path and yaml_path.is_file():
            try:
                rel_path = str(yaml_path.relative_to(self.repo_root))
            except ValueError:
                rel_path = str(yaml_path)
        profile_markdown = _persona_profile_markdown(
            persona_id=str(card.get("personaId") or persona_id),
            source=str(card.get("source") or ""),
            path=rel_path,
            yaml_text=yaml_text,
        )
        return {
            **card,
            "pool": persona_pool,
            "path": rel_path,
            "dimensions": full_dimensions,
            "yaml": yaml_text,
            "profileMarkdown": profile_markdown,
        }

    @staticmethod
    def _filters_as_lists(
        dimension_filters: dict[str, str | list[str]] | None,
    ) -> dict[str, list[str]]:
        if not dimension_filters:
            return {}
        out: dict[str, list[str]] = {}
        for key, value in dimension_filters.items():
            dim = str(key).removeprefix("dimensions.").strip()
            if not dim:
                continue
            if isinstance(value, list):
                cleaned = [str(item).strip() for item in value if str(item).strip()]
            else:
                text = str(value).strip()
                cleaned = [text] if text else []
            if cleaned:
                out[dim] = cleaned
        return out

    def _strategy_pool_relpath(
        self,
        *,
        task_path: str | None,
        list_filters: dict[str, list[str]],
        sources: list[str] | None,
    ) -> str:
        cleaned_task = (task_path or "").strip().rstrip("/")
        if cleaned_task:
            slug = re.sub(r"[^a-z0-9]+", "-", Path(cleaned_task).name.lower()).strip("-")
            return f"{GENERATED_DATASETS_DIR}/strategy-{slug or 'task'}"
        digest = hashlib.sha1(
            json.dumps(
                {"filters": list_filters, "sources": list(sources or [])},
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:10]
        return f"{GENERATED_DATASETS_DIR}/filters-{digest}"

    def ensure_filter_coverage_pool(
        self,
        *,
        dimension_filters: dict[str, str | list[str]] | None,
        sources: list[str] | None = None,
        sample_size: int = 1,
        stratify_fields: list[str] | None = None,
        sample_size_per_value_group: int | None = None,
        task_path: str | None = None,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Generate (or reuse) a local ``_generated`` pool that covers the filters."""
        from matraix.persona_generator import (
            PERSONA_SOURCES,
            build_filter_strata,
            filter_feasible_strata,
            generate_persona_pool,
            write_persona_dataset,
        )

        list_filters = self._filters_as_lists(self._normalize_dimension_filters(dimension_filters))
        if not list_filters:
            raise ValueError(
                "Cannot auto-generate a strategy pool without dimensionFilters"
            )

        try:
            strata = build_filter_strata(list_filters, max_strata=MAX_FILTER_STRATA)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        strata, dropped = filter_feasible_strata(strata)
        if not strata:
            raise ValueError(
                "dimensionFilters produced zero feasible strata after consistency filtering"
            )

        if isinstance(sample_size_per_value_group, int) and sample_size_per_value_group >= 1:
            stratum_min = max(DEFAULT_STRATEGY_STRATUM_MIN, sample_size_per_value_group)
        elif sample_size >= 1:
            stratum_min = max(
                DEFAULT_STRATEGY_STRATUM_MIN,
                (sample_size + len(strata) - 1) // len(strata),
            )
        else:
            stratum_min = DEFAULT_STRATEGY_STRATUM_MIN

        out_rel = self._strategy_pool_relpath(
            task_path=task_path,
            list_filters=list_filters,
            sources=sources,
        )
        out_dir = self.repo_root / out_rel

        if out_dir.is_dir():
            try:
                self._sample_pool_inner(
                    persona_pool=out_rel,
                    sample_size=max(1, sample_size),
                    seed=seed,
                    sources=sources,
                    dimension_filters=dimension_filters,
                    stratify_fields=stratify_fields,
                    sample_size_per_value_group=sample_size_per_value_group,
                )
                matched = self.filter_pool(
                    persona_pool=out_rel,
                    sources=sources,
                    dimension_filters=dimension_filters,
                )
                return {
                    "pool": out_rel,
                    "count": len(matched),
                    "strataCount": len(strata),
                    "droppedStrata": len(dropped),
                    "reused": True,
                }
            except ValueError as exc:
                if not is_pool_coverage_error(str(exc)):
                    raise

        source_tuple: tuple[str, ...]
        if sources:
            cleaned_sources = tuple(s.strip() for s in sources if str(s).strip())
            source_tuple = cleaned_sources or PERSONA_SOURCES
        else:
            source_tuple = PERSONA_SOURCES

        personas = generate_persona_pool(
            count=0,
            seed=seed,
            stratum_top_up=strata,
            min_per_stratum=stratum_min,
            sources=source_tuple,
            include_smoke=False,
        )
        kind = Path(out_rel).name
        manifest = write_persona_dataset(
            out_dir=out_dir,
            personas=personas,
            repo_root=self.repo_root,
            kind=kind,
            seed=seed,
            smoke_persona_id="0042",
        )
        manifest["stratum_top_up"] = {
            "min_per_stratum": stratum_min,
            "strata_count": len(strata),
            "dropped_strata": len(dropped),
            "task_path": (task_path or "").strip() or None,
            "dimensionFilters": list_filters,
            "stratifyFields": [
                str(field).removeprefix("dimensions.").strip()
                for field in (stratify_fields or [])
                if str(field).strip()
            ],
        }
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "pool": out_rel,
            "count": int(manifest.get("count") or len(personas)),
            "strataCount": len(strata),
            "droppedStrata": len(dropped),
            "reused": False,
        }

    def _expected_stratify_strata(
        self,
        dimension_filters: dict[str, str | list[str]] | None,
        stratify_fields: list[str] | None,
    ) -> list[dict[str, str]] | None:
        """Feasible stratify cells implied by filters, or None when unknown.

        Requires every stratify field to appear in dimensionFilters so the
        cartesian product of allowed values is well-defined.
        """
        if not stratify_fields:
            return None
        list_filters = self._filters_as_lists(self._normalize_dimension_filters(dimension_filters))
        stratify_filters: dict[str, list[str]] = {}
        for raw_field in stratify_fields:
            field = str(raw_field).removeprefix("dimensions.").strip()
            if not field:
                continue
            values = list_filters.get(field)
            if not values:
                return None
            stratify_filters[field] = values
        if len(stratify_filters) != len(
            [f for f in stratify_fields if str(f).removeprefix("dimensions.").strip()]
        ):
            return None
        from matraix.persona_generator import build_filter_strata, filter_feasible_strata

        try:
            strata = build_filter_strata(stratify_filters, max_strata=MAX_FILTER_STRATA)
        except ValueError:
            return None
        feasible, _dropped = filter_feasible_strata(strata)
        return feasible

    def _stratify_coverage_gap_message(
        self,
        matched: list[dict[str, Any]],
        *,
        stratify_fields: list[str],
        sample_size_per_value_group: int,
        expected_strata: list[dict[str, str]],
    ) -> str | None:
        """Return an error when any expected stratify cell has fewer than N personas."""
        bare_fields = [
            str(field).removeprefix("dimensions.").strip() for field in stratify_fields
        ]
        bare_fields = [field for field in bare_fields if field]
        buckets: dict[str, int] = {}
        for entry in matched:
            key = _stratify_bucket_key(entry, bare_fields, repo_root=self.repo_root)
            if key is None:
                continue
            buckets[key] = buckets.get(key, 0) + 1

        short: list[str] = []
        for stratum in expected_strata:
            key = "\x1f".join(str(stratum[field]) for field in bare_fields)
            have = buckets.get(key, 0)
            if have < sample_size_per_value_group:
                label = ", ".join(f"{field}={stratum[field]}" for field in bare_fields)
                short.append(
                    f"{label!r} has {have}, need sample_size_per_value_group="
                    f"{sample_size_per_value_group}"
                )
        if not short:
            return None
        preview = "; ".join(short[:6])
        more = f" (+{len(short) - 6} more)" if len(short) > 6 else ""
        return f"Incomplete stratify coverage: {preview}{more}"

    def sample_pool(
        self,
        *,
        persona_pool: str = DEFAULT_PERSONA_POOL,
        sample_size: int,
        seed: int = 42,
        sources: list[str] | None = None,
        dimension_filters: dict[str, str | list[str]] | None = None,
        stratify_fields: list[str] | None = None,
        sample_size_per_value_group: int | None = None,
        task_path: str | None = None,
        auto_ensure_strategy_pool: bool = True,
    ) -> dict[str, Any]:
        list_filters = self._filters_as_lists(self._normalize_dimension_filters(dimension_filters))
        can_auto_ensure = auto_ensure_strategy_pool and bool(list_filters)

        # Stratified quotas:
        # - sampleSizePerValueGroup set → N per cell (primary); sampleSize is not a clip.
        # - only sampleSize → ensure ≥1/cell, then stratified sample capped at sampleSize.
        #   sampleSize must be ≥ # expected cells when that product is known.
        explicit_per_cell = (
            isinstance(sample_size_per_value_group, int) and sample_size_per_value_group >= 1
        )
        expected = (
            self._expected_stratify_strata(dimension_filters, stratify_fields)
            if stratify_fields
            else None
        )
        if (
            stratify_fields
            and not explicit_per_cell
            and expected is not None
            and sample_size < len(expected)
        ):
            raise ValueError(
                "sampleSize={} is below the stratified cell count={} "
                "(need ≥1 persona per combination). Raise sampleSize, or set "
                "sampleSizePerValueGroup and omit sampleSize.".format(
                    sample_size, len(expected)
                )
            )

        # Coverage quota used when synthesizing thin cells.
        # sampleSize-only: share total N across cells (ceil), then sample/cap.
        if explicit_per_cell:
            ensure_per_cell = int(sample_size_per_value_group)
        elif expected:
            ensure_per_cell = max(1, (sample_size + len(expected) - 1) // len(expected))
        else:
            ensure_per_cell = 1

        # Empty/thin stratify cells are skipped or fail at sample time — detect
        # shortfalls up front and synthesize a local pool before sampling.
        if can_auto_ensure and stratify_fields and expected is not None:
            matched = self.filter_pool(
                persona_pool=persona_pool,
                sources=sources,
                dimension_filters=dimension_filters,
            )
            gap = self._stratify_coverage_gap_message(
                matched,
                stratify_fields=list(stratify_fields),
                sample_size_per_value_group=ensure_per_cell,
                expected_strata=expected,
            )
            if gap:
                try:
                    ensured = self.ensure_filter_coverage_pool(
                        dimension_filters=dimension_filters,
                        sources=sources,
                        sample_size=sample_size,
                        stratify_fields=stratify_fields,
                        sample_size_per_value_group=ensure_per_cell,
                        task_path=task_path,
                        seed=seed,
                    )
                    result = self._sample_pool_inner(
                        persona_pool=str(ensured["pool"]),
                        sample_size=sample_size,
                        seed=seed,
                        sources=sources,
                        dimension_filters=dimension_filters,
                        stratify_fields=stratify_fields,
                        sample_size_per_value_group=sample_size_per_value_group,
                    )
                    result["poolEnsured"] = True
                    result["poolReused"] = bool(ensured.get("reused"))
                    return result
                except Exception as ensure_exc:  # noqa: BLE001
                    raise ValueError(
                        with_coverage_hint(
                            f"{gap}\n\nAuto pool top-up failed: {ensure_exc}",
                            task_path=task_path,
                        )
                    ) from ensure_exc

        try:
            return self._sample_pool_inner(
                persona_pool=persona_pool,
                sample_size=sample_size,
                seed=seed,
                sources=sources,
                dimension_filters=dimension_filters,
                stratify_fields=stratify_fields,
                sample_size_per_value_group=sample_size_per_value_group,
            )
        except ValueError as exc:
            message = str(exc)
            can_ensure = can_auto_ensure and is_pool_coverage_error(message)
            if not can_ensure:
                raise ValueError(with_coverage_hint(message, task_path=task_path)) from exc
            try:
                ensured = self.ensure_filter_coverage_pool(
                    dimension_filters=dimension_filters,
                    sources=sources,
                    sample_size=sample_size,
                    stratify_fields=stratify_fields,
                    sample_size_per_value_group=sample_size_per_value_group,
                    task_path=task_path,
                    seed=seed,
                )
                result = self._sample_pool_inner(
                    persona_pool=str(ensured["pool"]),
                    sample_size=sample_size,
                    seed=seed,
                    sources=sources,
                    dimension_filters=dimension_filters,
                    stratify_fields=stratify_fields,
                    sample_size_per_value_group=sample_size_per_value_group,
                )
                result["poolEnsured"] = True
                result["poolReused"] = bool(ensured.get("reused"))
                return result
            except Exception as ensure_exc:  # noqa: BLE001 — surface as sample failure
                raise ValueError(
                    with_coverage_hint(
                        f"{message}\n\nAuto pool top-up failed: {ensure_exc}",
                        task_path=task_path,
                    )
                ) from ensure_exc

    def _sample_pool_inner(
        self,
        *,
        persona_pool: str = DEFAULT_PERSONA_POOL,
        sample_size: int,
        seed: int = 42,
        sources: list[str] | None = None,
        dimension_filters: dict[str, str | list[str]] | None = None,
        stratify_fields: list[str] | None = None,
        sample_size_per_value_group: int | None = None,
    ) -> dict[str, Any]:
        matched = self.filter_pool(
            persona_pool=persona_pool,
            sources=sources,
            dimension_filters=dimension_filters,
        )
        if sample_size < 1:
            raise ValueError("sample_size must be >= 1")
        if stratify_fields:
            bare_fields = [
                str(field).removeprefix("dimensions.").strip() for field in stratify_fields
            ]
            bare_fields = [field for field in bare_fields if field]
            bucket_counts: dict[str, int] = {}
            for entry in matched:
                key = _stratify_bucket_key(entry, bare_fields, repo_root=self.repo_root)
                if key is None:
                    continue
                bucket_counts[key] = bucket_counts.get(key, 0) + 1
            n_buckets = len(bucket_counts)
            if n_buckets < 1:
                label = ", ".join(bare_fields)
                raise ValueError(f"No personas with stratify fields ({label})")

            if sample_size_per_value_group is not None:
                per_group = sample_size_per_value_group
            else:
                # Spread total sampleSize across cells: ceil(N / cells), then clip.
                if sample_size < n_buckets:
                    raise ValueError(
                        "sampleSize={} is below the stratified cell count={} "
                        "(need ≥1 persona per combination)".format(sample_size, n_buckets)
                    )
                per_group = max(1, (sample_size + n_buckets - 1) // n_buckets)

            chosen = sample_personas_stratified(
                matched,
                stratify_fields=list(stratify_fields),
                sample_size_per_value_group=per_group,
                seed=seed,
                repo_root=self.repo_root,
            )
            # Explicit per-cell quota: take N×cells; ignore sampleSize (mutually
            # exclusive strategies — strategy files must set only one).
            # sampleSize-only stratified: take ceil(N/cells) then truncate to N.
            if sample_size_per_value_group is None and len(chosen) > sample_size:
                chosen = chosen[:sample_size]
        else:
            if sample_size > len(matched):
                raise ValueError(
                    "sample_size={} exceeds matched pool size={}".format(sample_size, len(matched))
                )
            chosen = sample_personas(matched, sample_size=sample_size, seed=seed)
        personas = [self._persona_card(entry) for entry in chosen]
        return {
            "pool": persona_pool,
            "matchedCount": len(matched),
            "sampleSize": len(personas),
            "seed": seed,
            "personaIds": [row["personaId"] for row in personas if row["personaId"]],
            "personas": personas,
            "stratifyFields": list(stratify_fields or []),
            "poolEnsured": False,
            "poolReused": False,
        }

    def _cohorts_root(self) -> Path:
        return self.repo_root / COHORTS_DIR

    def _cohort_path(self, cohort_id: str) -> Path:
        return self._cohorts_root() / _cohort_slug(cohort_id) / "cohort.json"

    def list_cohorts(self) -> list[dict[str, Any]]:
        root = self._cohorts_root()
        if not root.is_dir():
            return []
        summaries: list[dict[str, Any]] = []
        for path in sorted(root.glob("*/cohort.json")):
            try:
                payload = self._read_json(path)
            except Exception:  # noqa: BLE001
                continue
            summaries.append(self._cohort_summary(payload, path.parent.name))
        return summaries

    def get_cohort(self, cohort_id: str) -> dict[str, Any]:
        path = self._cohort_path(cohort_id)
        if not path.is_file():
            raise FileNotFoundError("cohort not found: {}".format(cohort_id))
        payload = self._read_json(path)
        return self._cohort_view(payload)

    def save_cohort(
        self,
        *,
        cohort_id: str,
        name: str | None = None,
        description: str | None = None,
        pool: str = DEFAULT_PERSONA_POOL,
        kind: CohortKind = "recipe",
        seed: int = 42,
        sample_size: int = 1,
        sources: list[str] | None = None,
        dimension_filters: dict[str, str] | None = None,
        persona_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        slug = _cohort_slug(cohort_id)
        matched = self.filter_pool(
            persona_pool=pool,
            sources=sources,
            dimension_filters=dimension_filters,
        )
        resolved_kind: CohortKind = kind
        resolved_persona_ids = list(persona_ids or [])
        personas: list[dict[str, str]] = []

        if resolved_kind == "frozen":
            if not resolved_persona_ids:
                if sample_size < 1:
                    raise ValueError("sample_size must be >= 1 for frozen cohort")
                if sample_size > len(matched):
                    raise ValueError(
                        "sample_size={} exceeds matched pool size={}".format(
                            sample_size, len(matched)
                        )
                    )
                chosen = sample_personas(matched, sample_size=sample_size, seed=seed)
                resolved_persona_ids = [
                    str(entry.get("persona_id") or "") for entry in chosen
                ]
            by_id = {str(entry.get("persona_id") or ""): entry for entry in matched}
            for pid in resolved_persona_ids:
                entry = by_id.get(pid)
                if entry is None:
                    raise ValueError("persona {} not in matched pool".format(pid))
                personas.append(
                    {
                        "personaId": pid,
                        "source": str(entry.get("source") or ""),
                        "path": str(entry.get("path") or ""),
                    }
                )
        else:
            resolved_persona_ids = []
            personas = []

        payload = {
            "cohortId": slug,
            "name": (name or slug).strip(),
            "description": (description or "").strip(),
            "createdAt": _utc_now(),
            "pool": pool,
            "kind": resolved_kind,
            "seed": int(seed),
            "sampleSize": int(sample_size),
            "sources": list(sources or []),
            "dimensionFilters": dict(dimension_filters or {}),
            "matchedCount": len(matched),
            "personaIds": resolved_persona_ids,
            "personas": personas,
        }
        cohort_dir = self._cohorts_root() / slug
        cohort_dir.mkdir(parents=True, exist_ok=True)
        path = cohort_dir / "cohort.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self._cohort_view(payload)

    def resolve_cohort_launch(
        self,
        cohort_id: str,
        *,
        sample_size_override: int | None = None,
    ) -> dict[str, Any]:
        cohort = self.get_cohort(cohort_id)
        pool = str(cohort.get("pool") or DEFAULT_PERSONA_POOL)
        if cohort.get("kind") == "frozen":
            persona_ids = list(cohort.get("personaIds") or [])
            if not persona_ids:
                raise ValueError("frozen cohort has no personaIds")
            return {
                "pool": pool,
                "personaIds": persona_ids,
                "seed": cohort.get("seed"),
                "sources": cohort.get("sources") or [],
                "dimensionFilters": cohort.get("dimensionFilters") or {},
                "cohortId": cohort.get("cohortId"),
            }
        sample_size = int(
            sample_size_override if sample_size_override is not None else cohort.get("sampleSize") or 1
        )
        sampled = self.sample_pool(
            persona_pool=pool,
            sample_size=sample_size,
            seed=int(cohort.get("seed") or 42),
            sources=list(cohort.get("sources") or []) or None,
            dimension_filters=dict(cohort.get("dimensionFilters") or {}) or None,
        )
        return {
            "pool": pool,
            "personaIds": list(sampled["personaIds"]),
            "seed": cohort.get("seed"),
            "sources": cohort.get("sources") or [],
            "dimensionFilters": cohort.get("dimensionFilters") or {},
            "cohortId": cohort.get("cohortId"),
        }

    def _cohort_summary(self, payload: dict[str, Any], fallback_id: str) -> dict[str, Any]:
        return {
            "cohortId": str(payload.get("cohortId") or fallback_id),
            "name": str(payload.get("name") or fallback_id),
            "kind": str(payload.get("kind") or "recipe"),
            "pool": str(payload.get("pool") or DEFAULT_PERSONA_POOL),
            "sampleSize": int(payload.get("sampleSize") or 0),
            "matchedCount": int(payload.get("matchedCount") or 0),
            "personaCount": len(payload.get("personaIds") or []),
            "createdAt": payload.get("createdAt"),
        }

    def _cohort_view(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "cohortId": str(payload.get("cohortId") or ""),
            "name": str(payload.get("name") or ""),
            "description": str(payload.get("description") or ""),
            "createdAt": payload.get("createdAt"),
            "pool": str(payload.get("pool") or DEFAULT_PERSONA_POOL),
            "kind": str(payload.get("kind") or "recipe"),
            "seed": int(payload.get("seed") or 42),
            "sampleSize": int(payload.get("sampleSize") or 1),
            "sources": list(payload.get("sources") or []),
            "dimensionFilters": dict(payload.get("dimensionFilters") or {}),
            "matchedCount": int(payload.get("matchedCount") or 0),
            "personaIds": list(payload.get("personaIds") or []),
            "personas": list(payload.get("personas") or []),
        }
