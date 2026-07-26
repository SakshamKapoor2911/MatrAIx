"""Regex retrieval stage.

For each dimension we compile one case-insensitive pattern per allowed *value*.
A value matches when it appears in the prompt as a whole word/phrase (word
boundaries, so ``"Man"`` does not fire inside ``"management"``). A dimension
whose value(s) match becomes a candidate, and each matched value is emitted as a
regex :class:`~persona.treiver.treiver.Attribute` with the matched span as
evidence.

This does double duty:

* **as the RAG retriever** — the set of matched dimension ids is exactly the
  candidate set handed to the LLM judge.
* **as a standalone algorithm** — its emitted attributes are usable on their
  own when you don't want to call an LLM (offline, deterministic, free).

The matching is intentionally literal: high precision, low recall. Paraphrases
("she") won't match the value ``"Woman"``; that recall gap is what the LLM
judge stage is for.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .schema import Dimension, DimensionSchema

# If a value tuple is shared by at least this many dimensions, its values are
# generic scale labels (Expert/Proficient/…, Love/Like/…, High/Low/…) that say
# nothing about *which* dimension. For those dimensions we additionally require
# the dimension's topic word(s) to appear in the prompt before proposing it.
# ~1040 of 1290 dimensions fall in this bucket; the ~250 with distinctive value
# sets (age_bracket, region, …) match on the value alone.
_SHARED_VALUESET_THRESHOLD = 5

# Topic words too generic to gate on — a topic reduced to only these is treated
# as ungated (fall back to value-only matching) rather than firing on filler.
_TOPIC_STOPWORDS = frozenset(
    {"and", "of", "the", "a", "an", "for", "in", "on", "to", "with", "or"}
)

# A short, curated set of synonym aliases for a few high-value demographic
# dimensions. Kept deliberately tiny — the regex stage is meant to stay literal
# and auditable; broad paraphrase coverage is the LLM judge's job. Keys are
# (dimension_id, canonical_value); values are extra surface forms to match.
_VALUE_ALIASES: dict[tuple[str, str], tuple[str, ...]] = {
    ("gender_identity", "Woman"): ("women", "female", "she", "her"),
    ("gender_identity", "Man"): ("men", "male", "he", "him"),
    ("gender_identity", "Non-binary"): ("nonbinary", "enby"),
    ("urbanicity", "Dense urban"): ("urban", "city", "downtown", "metropolitan"),
    ("urbanicity", "Rural"): ("countryside", "farm", "village"),
    ("urbanicity", "Suburban"): ("suburb", "suburbs"),
}


@dataclass
class RegexHit:
    """One value of one dimension matched against the prompt."""

    dimension_id: str
    value: str
    evidence: str  # the exact substring of the prompt that matched
    start: int
    end: int


def _surface_forms(dim: Dimension, value: str) -> list[str]:
    """All strings that, if found in the prompt, imply this value."""
    forms = [value]
    forms.extend(_VALUE_ALIASES.get((dim.id, value), ()))
    return forms


def _compile(form: str) -> re.Pattern[str]:
    """Whole-word/phrase, case-insensitive pattern for one surface form.

    ``\\b`` on both sides where the edge char is a word char; multi-word forms
    match with flexible internal whitespace. Non-word edges (e.g. ``"85+"``)
    fall back to a plain escaped match so the ``+`` isn't lost to ``\\b``.
    """
    escaped = re.escape(form.strip())
    # Allow any run of whitespace between tokens of a multi-word value.
    escaped = re.sub(r"\\ ", r"\\s+", escaped)
    left = r"\b" if form[:1].isalnum() else ""
    right = r"\b" if form[-1:].isalnum() else ""
    return re.compile(left + escaped + right, re.IGNORECASE)


def _topic_of(dim: Dimension) -> str:
    """The distinguishing topic of a dimension, drawn from its label.

    Labels are typically ``"Familiarity: Machine learning"`` or
    ``"Interest: Astronomy"``; the part after the last colon is the topic. When
    there's no colon we use the whole label. Used only for gating generic-value
    dimensions.
    """
    label = dim.label
    topic = label.rsplit(":", 1)[-1].strip() if ":" in label else label.strip()
    return topic


def _topic_pattern(topic: str) -> re.Pattern[str] | None:
    """Whole-word pattern for a topic, or None if it reduces to stopwords."""
    words = [w for w in re.split(r"\W+", topic) if w and w.lower() not in _TOPIC_STOPWORDS]
    if not words:
        return None
    # Match the topic phrase with flexible whitespace between its content words.
    body = r"\s+".join(re.escape(w) for w in words)
    return re.compile(r"\b" + body + r"\b", re.IGNORECASE)


class RegexMatcher:
    """Compile-once, match-many regex retriever over a dimension schema."""

    def __init__(self, schema: DimensionSchema) -> None:
        self.schema = schema
        # Dimensions that share a value tuple with many others have generic
        # scale values; gate those on their topic word appearing in the prompt.
        valueset_counts = Counter(dim.values for dim in schema)
        # dimension_id -> list of (value, compiled_pattern)
        self._patterns: dict[str, list[tuple[str, re.Pattern[str]]]] = {}
        # dimension_id -> compiled topic pattern (only for gated dimensions)
        self._topic_gate: dict[str, re.Pattern[str]] = {}
        for dim in schema:
            entries: list[tuple[str, re.Pattern[str]]] = []
            for value in dim.values:
                for form in _surface_forms(dim, value):
                    entries.append((value, _compile(form)))
            if entries:
                self._patterns[dim.id] = entries
            if valueset_counts[dim.values] >= _SHARED_VALUESET_THRESHOLD:
                gate = _topic_pattern(_topic_of(dim))
                if gate is not None:
                    self._topic_gate[dim.id] = gate

    def match(self, prompt: str) -> list[RegexHit]:
        """Return every value-level hit across all dimensions.

        Deduplicated per ``(dimension_id, value)`` — the first (leftmost)
        occurrence wins, so evidence points at where the trait was first stated.
        """
        hits: list[RegexHit] = []
        seen: set[tuple[str, str]] = set()
        for dim_id, entries in self._patterns.items():
            # Generic-value dimensions only fire if their topic is present, so a
            # bare "expert" doesn't light up all 143 familiarity dimensions.
            gate = self._topic_gate.get(dim_id)
            if gate is not None and not gate.search(prompt):
                continue
            for value, pattern in entries:
                key = (dim_id, value)
                if key in seen:
                    continue
                m = pattern.search(prompt)
                if m:
                    hits.append(
                        RegexHit(
                            dimension_id=dim_id,
                            value=value,
                            evidence=m.group(0),
                            start=m.start(),
                            end=m.end(),
                        )
                    )
                    seen.add(key)
        hits.sort(key=lambda h: h.start)
        return hits

    def topic_candidates(self, prompt: str) -> list[tuple[str, int]]:
        """Gated dimensions whose *topic* appears, even with no value-word hit.

        "senior python developer" mentions the Python topic but no proficiency
        word, so :meth:`match` emits nothing for ``prog_python``. This surfaces
        it anyway (with the topic-match position) so the LLM judge can still be
        asked to rule on it. Returns ``(dimension_id, position)`` pairs.
        """
        out: list[tuple[str, int]] = []
        for dim_id, gate in self._topic_gate.items():
            m = gate.search(prompt)
            if m:
                out.append((dim_id, m.start()))
        return out

    def candidate_dimension_ids(
        self, prompt: str, include_topic_only: bool = False
    ) -> list[str]:
        """Dimension ids the prompt plausibly touches (the RAG candidate set).

        Order-preserving unique list, ordered by first evidence position so the
        judge sees the most prompt-forward dimensions first.

        With ``include_topic_only=True`` also includes gated dimensions whose
        topic is mentioned without a matching value word — widening recall for
        the judge at the cost of more candidates to rule on.
        """
        positioned: list[tuple[str, int]] = [
            (hit.dimension_id, hit.start) for hit in self.match(prompt)
        ]
        if include_topic_only:
            positioned.extend(self.topic_candidates(prompt))

        ordered: list[str] = []
        seen: set[str] = set()
        for dim_id, _pos in sorted(positioned, key=lambda t: t[1]):
            if dim_id not in seen:
                ordered.append(dim_id)
                seen.add(dim_id)
        return ordered
