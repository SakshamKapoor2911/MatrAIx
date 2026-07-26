"""Embedding retrieval stage — the *semantic* half of the RAG retriever.

Where the regex matcher (``regex_matcher.py``) is literal — it only surfaces a
dimension when the prompt contains that dimension's value or topic *word* — this
retriever works by meaning. It embeds a short descriptor of every dimension
("<label>. <description>. options: <values>") once, caches the matrix, and at
query time returns the dimensions whose descriptor is closest to the prompt by
cosine similarity.

That closes the recall gap the regex stage can't: "she writes models at a hedge
fund" has no literal overlap with ``fam_quantitative_trading``'s values, but its
*embedding* is near that dimension's descriptor, so it still becomes a candidate
for the LLM judge to rule on.

Backend: local ``sentence-transformers`` (default ``all-MiniLM-L6-v2``) — offline,
free, no token. The model is loaded lazily and the dimension matrix is cached on
disk, so the first call pays the encode cost and later calls are instant.

If ``sentence-transformers`` is unavailable, this module degrades to a keyword
overlap scorer so the pipeline still runs (lower recall, zero dependency).
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass

from .schema import Dimension, DimensionSchema

_DEFAULT_MODEL = os.environ.get("TREIVER_EMBED_MODEL", "all-MiniLM-L6-v2")
_CACHE_DIR = os.path.join(os.path.dirname(__file__), ".embed_cache")


@dataclass
class EmbedHit:
    """One dimension retrieved by semantic similarity."""

    dimension_id: str
    score: float  # cosine similarity in [-1, 1] (or overlap ratio in fallback)


def _dimension_text(dim: Dimension) -> str:
    """The descriptor we embed for a dimension — label, gloss, and its values."""
    values = ", ".join(dim.values)
    return f"{dim.label}. {dim.description} Options: {values}."


class EmbedRetriever:
    """Semantic retriever over dimension descriptors.

    Parameters
    ----------
    schema:
        The dimension taxonomy.
    model_name:
        A sentence-transformers model id. Defaults to ``all-MiniLM-L6-v2`` (or
        ``$TREIVER_EMBED_MODEL``).
    encoder:
        Inject a pre-built encoder (anything with ``encode(list[str]) -> ndarray``)
        — used by tests to avoid loading a real model.
    """

    def __init__(
        self,
        schema: DimensionSchema,
        model_name: str = _DEFAULT_MODEL,
        encoder=None,
    ) -> None:
        self.schema = schema
        self.model_name = model_name
        self._encoder = encoder
        self._dim_ids: list[str] = [d.id for d in schema]
        self._matrix = None  # lazily built (num_dims, dim) unit vectors
        self._fallback = False  # True once we've dropped to keyword overlap

    # -- encoder / matrix -----------------------------------------------------

    def _get_encoder(self):
        if self._encoder is not None:
            return self._encoder
        from sentence_transformers import SentenceTransformer  # lazy, heavy

        self._encoder = SentenceTransformer(self.model_name)
        return self._encoder

    def _cache_path(self) -> str:
        # Key the cache by model + schema content so it invalidates on change.
        sig = hashlib.sha1(
            (self.model_name + "|" + "|".join(self._dim_ids)).encode("utf-8")
        ).hexdigest()[:16]
        return os.path.join(_CACHE_DIR, f"dims-{sig}.npy")

    def _build_matrix(self):
        import numpy as np

        # Only use the on-disk cache for the default model. An injected encoder
        # (tests, custom models) produces vectors the cache key can't identify,
        # so caching it would corrupt later runs — encode fresh instead.
        use_cache = self._encoder is None
        cache = self._cache_path() if use_cache else None
        if cache and os.path.exists(cache):
            return np.load(cache)

        texts = [_dimension_text(self.schema.get(i)) for i in self._dim_ids]
        vecs = self._get_encoder().encode(
            texts, batch_size=64, show_progress_bar=False, convert_to_numpy=True
        )
        vecs = _l2_normalize(np.asarray(vecs, dtype="float32"))
        if cache:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            try:
                np.save(cache, vecs)
            except OSError:
                pass  # cache is an optimization, not a requirement
        return vecs

    def _ensure_matrix(self):
        if self._matrix is not None:
            return
        try:
            self._matrix = self._build_matrix()
        except Exception:
            # sentence-transformers missing or model load failed → keyword mode.
            self._fallback = True

    # -- query ----------------------------------------------------------------

    def retrieve(
        self, prompt: str, top_k: int = 12, min_score: float = 0.25
    ) -> list[EmbedHit]:
        """Return up to ``top_k`` dimensions most similar to ``prompt``.

        Only hits at or above ``min_score`` are returned. Falls back to keyword
        overlap if embeddings are unavailable.
        """
        self._ensure_matrix()
        if self._fallback or self._matrix is None:
            return self._retrieve_keyword(prompt, top_k, min_score)

        import numpy as np

        q = self._get_encoder().encode(
            [prompt], show_progress_bar=False, convert_to_numpy=True
        )
        q = _l2_normalize(np.asarray(q, dtype="float32"))[0]
        sims = self._matrix @ q  # cosine, since both sides are unit vectors
        order = np.argsort(-sims)[:top_k]
        return [
            EmbedHit(self._dim_ids[i], float(sims[i]))
            for i in order
            if sims[i] >= min_score
        ]

    def candidate_dimension_ids(
        self, prompt: str, top_k: int = 12, min_score: float = 0.25
    ) -> list[str]:
        return [h.dimension_id for h in self.retrieve(prompt, top_k, min_score)]

    # -- keyword fallback -----------------------------------------------------

    def _retrieve_keyword(self, prompt: str, top_k: int, min_score: float):
        """Dependency-free fallback: Jaccard-ish overlap on content words."""
        p_words = _content_words(prompt)
        if not p_words:
            return []
        scored: list[EmbedHit] = []
        for dim_id in self._dim_ids:
            d_words = _content_words(_dimension_text(self.schema.get(dim_id)))
            if not d_words:
                continue
            overlap = len(p_words & d_words) / len(p_words)
            if overlap >= min_score:
                scored.append(EmbedHit(dim_id, overlap))
        scored.sort(key=lambda h: -h.score)
        return scored[:top_k]


def _l2_normalize(mat):
    import numpy as np

    norms = np.linalg.norm(mat, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


_STOP = frozenset(
    "a an the of in on at to for with and or is are be by who works work lives "
    "this that person options based their her his".split()
)


def _content_words(text: str) -> set[str]:
    return {w for w in re.split(r"\W+", text.lower()) if w and w not in _STOP and len(w) > 2}
