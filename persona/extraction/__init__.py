"""treiver — match a free-text prompt to persona attributes.

A *treiver* (trait-retriever) turns one natural-language prompt describing a
person into a set of structured **attributes** — ``(dimension_id, value)`` pairs
drawn from the PersonaWorld dimension taxonomy (``persona/schema/dimensions.json``).

It is a small RAG pipeline with two algorithms, run as two stages:

1. **regex retrieval** — for every dimension, test the prompt against regex
   patterns built from that dimension's values/label/phrase. Any dimension that
   matches becomes a *candidate*. This is the "R" in RAG: it narrows 1290
   dimensions down to a handful the prompt could plausibly be talking about.
2. **LLM judge** — Claude sees the prompt and only the candidate dimensions
   (plus their allowed values) and, per dimension, picks the single best value,
   quotes the evidence span, and gives a confidence. This is the generation /
   scoring stage.

Each stage emits :class:`Attribute` records — ``dimension_id``, ``value``,
``evidence``, ``method`` (``"regex"`` or ``"llm"``), ``confidence`` — mirroring
the field shape in ``note/persona-extraction-note.md`` so the output feeds the
extraction-quality rubric directly.

Typical use::

    from persona.extraction import Treiver

    t = Treiver()                       # loads the bundled schema
    result = t.match("a retired nurse in rural Kentucky, born 1950")
    for attr in result.attributes:
        print(attr.dimension_id, "=", attr.value, f"({attr.method})")

By default only the regex stage runs (offline, deterministic). Pass
``use_llm=True`` to add the Claude judge over the regex candidates.
"""

from .schema import Dimension, DimensionSchema, load_schema
from .treiver import Attribute, MatchResult, Treiver

__all__ = [
    "Attribute",
    "Dimension",
    "DimensionSchema",
    "MatchResult",
    "Treiver",
    "load_schema",
]
