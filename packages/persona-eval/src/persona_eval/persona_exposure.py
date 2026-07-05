"""Build and normalize task-configured persona-visible turn fields."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence


def lookup_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def build_persona_exposure(
    source: Dict[str, Any],
    fields: Sequence[Any] | None,
) -> List[Dict[str, Any]]:
    exposure: List[Dict[str, Any]] = []
    for field in fields or ():
        selector = str(getattr(field, "selector", "") or "")
        if not selector:
            continue
        value = lookup_path(source, selector)
        if value in (None, "", []):
            continue
        exposure.append(
            {
                "key": str(getattr(field, "key", "") or selector),
                "label": str(getattr(field, "label", "") or selector),
                "format": str(getattr(field, "format", "") or "text"),
                "value": value,
            }
        )
    return exposure


def item_list_from_exposure(exposure: Any) -> List[Dict[str, Any]]:
    if not isinstance(exposure, list):
        return []
    for field in exposure:
        if not isinstance(field, dict):
            continue
        if str(field.get("format") or "") != "item_list":
            continue
        value = field.get("value")
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]
    return []


def coerce_turn_view(view: Any) -> Dict[str, Any]:
    """Normalize a persisted or live turn dict to the wire contract."""
    if not isinstance(view, dict):
        return {}
    out = dict(view)
    turn_id = out.get("turnId")
    if turn_id is not None and not isinstance(turn_id, str):
        out["turnId"] = str(turn_id)
    conv_id = out.get("conversationId")
    if conv_id is not None and not isinstance(conv_id, str):
        out["conversationId"] = str(conv_id)
    if not isinstance(out.get("plan"), list):
        out["plan"] = []
    exposure = out.get("personaExposure")
    if not isinstance(exposure, list):
        exposure = []
    legacy_items = out.pop("recommendedItems", None)
    if not exposure and isinstance(legacy_items, list) and legacy_items:
        exposure = [
            {
                "key": "items",
                "label": "Structured details",
                "format": "item_list",
                "value": legacy_items,
            }
        ]
    out["personaExposure"] = exposure
    return out


def normalize_transcript_payload(
    transcript: Dict[str, Any],
    *,
    fields: Sequence[Any] | None = None,
) -> Dict[str, Any]:
    """Normalize transcript turns to the platform wire contract."""
    if not isinstance(transcript, dict):
        return {}
    out = dict(transcript)
    turns = out.get("turns")
    if not isinstance(turns, list):
        return out
    normalized: List[Dict[str, Any]] = []
    for index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            continue
        coerced = coerce_turn_view(turn)
        if not coerced.get("personaExposure"):
            exposure = build_persona_exposure({**out, **turn}, fields)
            coerced["personaExposure"] = exposure
        if coerced.get("turnId") is None:
            coerced["turnId"] = str(turn.get("turnIndex", index))
        normalized.append(coerced)
    out["turns"] = normalized
    return out
