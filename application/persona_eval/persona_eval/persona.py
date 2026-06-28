from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from persona_eval.types import Persona

#: A bare snake_case / lowercase enum token (``financial_manager``, ``graduate``)
#: — humanized for display. Anything with a space, hyphen, uppercase, or other
#: punctuation (cities, sentences, ids) is left exactly as authored.
_ENUM_VALUE_RE = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")

# Curated YAML personas are the single source of truth (336 personas), bundled
# in-app at ``data/personas/`` so the app is self-contained. Each loaded
# persona's ``source`` is the curated dataset it came from (e.g. ``Nemotron``,
# ``OASIS``). persona.py -> persona_eval -> application/persona_eval.
_CURATED_DIR = Path(__file__).resolve().parents[1] / "data" / "personas"

# Keys that are loader bookkeeping rather than persona content.
_SKIP_KEYS = {"id", "source", "source_file", "raw_fields"}


def _humanize(label: str) -> str:
    """Turn a snake_case / lowercase key into a "Humanized Label"."""
    text = str(label).replace("_", " ").strip()
    if not text:
        return text
    # Title-case only words that look like plain identifiers; leave full
    # sentence-style keys (already containing spaces/punctuation) mostly intact.
    return " ".join(w if (w[:1].isupper() or not w[:1].isalpha()) else w.capitalize()
                     for w in text.split(" "))


def _render(value: Any, indent: int = 0) -> List[str]:
    """Recursively render a scalar / list / dict into indented text lines."""
    pad = "  " * indent
    lines: List[str] = []
    if isinstance(value, dict):
        for key, val in value.items():
            label = _humanize(key)
            if isinstance(val, (dict, list)):
                lines.append("{}{}:".format(pad, label))
                lines.extend(_render(val, indent + 1))
            else:
                rendered = _render_scalar(val)
                if rendered:
                    lines.append("{}{}: {}".format(pad, label, rendered))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.extend(_render(item, indent))
            else:
                rendered = _render_scalar(item)
                if rendered:
                    lines.append("{}- {}".format(pad, rendered))
    else:
        rendered = _render_scalar(value)
        if rendered:
            lines.append("{}{}".format(pad, rendered))
    return lines


def _render_scalar(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return text
    # Humanize bare snake_case / lowercase enum tokens (``financial_manager`` ->
    # ``Financial Manager``) so the verbatim context reads cleanly; leave
    # already-cased words, multi-word free text, and ids untouched.
    if _ENUM_VALUE_RE.fullmatch(text):
        return _humanize(text)
    return text


def _render_context(data: Dict[str, Any]) -> str:
    """Render a curated persona dict into an indented humanized text block.

    The block is rendered in full (no length cap): it is both what the persona
    drawer shows and the user-simulator's persona prompt, so truncating it would
    crop the UI and degrade the eval. Curated profiles are bounded (a few KB).
    """
    filtered = {k: v for k, v in data.items() if k not in _SKIP_KEYS}
    return "\n".join(_render(filtered)).strip()


def _extract_name(source: str, data: Dict[str, Any]) -> str:
    """Derive a display name from a curated persona dict."""
    if source == "OASIS":
        user = data.get("user_data") or {}
        if isinstance(user, dict):
            name = user.get("realname") or user.get("username")
            if name:
                return str(name).strip()
    id_suffix = str(data.get("id", "")).strip()
    return "{} · {}".format(source, id_suffix)


def _load_curated() -> List[Persona]:
    personas: List[Persona] = []
    if not _CURATED_DIR.exists():
        return personas
    for path in sorted(_CURATED_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        source = str(data.get("source", "")).strip()
        persona = Persona(
            id=path.stem,
            name=_extract_name(source, data),
            source=source,
            context=_render_context(data),
        )
        personas.append(persona)
    return personas


def _load_all() -> Dict[str, Persona]:
    personas: Dict[str, Persona] = {}
    for persona in _load_curated():
        personas[persona.id] = persona
    return personas


def load_personas(query: str = "", limit: Optional[int] = None) -> List[Persona]:
    personas = sorted(_load_all().values(), key=lambda p: p.id)
    if query:
        needle = query.lower()
        personas = [
            p for p in personas if needle in (p.name + " " + p.context).lower()
        ]
    if limit is not None:
        personas = personas[:limit]
    return personas


def get_persona(persona_id: str) -> Persona:
    personas = _load_all()
    if persona_id not in personas:
        raise KeyError("unknown persona: {}".format(persona_id))
    return personas[persona_id]
