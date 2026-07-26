"""LLM judge stage — Claude picks the best value per candidate dimension.

Given the prompt and the candidate dimensions surfaced by the regex retriever,
Claude decides, for each dimension, whether the prompt supports assigning a
value and if so which one — quoting the evidence span and rating its confidence.
It may leave a dimension unassigned (``value = null``) when the prompt gives no
real support, which keeps the "no over-claiming" property the extraction rubric
(``note/persona-extraction-note.md``, metric M4) rewards.

Backends
--------
* ``"anthropic"`` — Claude via the ``anthropic`` SDK, using structured outputs
  (``output_config.format``) so the response is guaranteed to validate against
  our schema. Adaptive thinking is on so the model reasons about ambiguous
  evidence before committing.
* ``"openai"`` — any OpenAI-compatible ``/chat/completions`` endpoint, configured
  with ``OPENAI_API_KEY`` and (optionally) ``OPENAI_BASE_URL``. Such gateways
  have no json-schema mode, so we ask for raw JSON in the prompt and validate the
  closed-value contract on our side. Works with a self-hosted or proxied gateway
  by pointing ``OPENAI_BASE_URL`` at it.
* ``"auto"`` (default) — use the OpenAI endpoint when ``OPENAI_API_KEY`` is set,
  else fall back to the anthropic SDK.

Both backends are imported lazily, so the regex stage (and a judge on the other
backend) needs neither package.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from .schema import Dimension, DimensionSchema

_MODEL = "claude-opus-4-8"


def _openai_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


class _OpenAIChatClient:
    """Minimal OpenAI-compatible ``/chat/completions`` client returning a dict.

    Zero SDK dependency — plain ``urllib`` — so it works against the public
    OpenAI API or any compatible gateway by setting ``OPENAI_BASE_URL``. Extra
    request headers can be supplied via ``OPENAI_EXTRA_HEADERS`` (JSON object),
    which some gateways require.
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 180.0,
        max_tokens: int = 8192,
    ) -> None:
        self.model = model
        self.api_key = (api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
        self.base_url = (
            base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        ).strip().rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the openai judge backend")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        extra = os.environ.get("OPENAI_EXTRA_HEADERS", "").strip()
        if extra:
            try:
                headers.update(json.loads(extra))
            except json.JSONDecodeError:
                pass
        return headers

    def complete_json(self, system: str, user: str) -> dict:
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": user
                    + "\n\nReturn only a valid JSON object. Do not include markdown.",
                },
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers=self._headers(),
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"openai judge request failed: HTTP {exc.code} {detail[:400]}"
            ) from exc
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"openai judge request failed: {exc}") from exc

        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError(f"openai judge returned no choices: {str(payload)[:200]}")
        text = str((choices[0].get("message") or {}).get("content") or "")
        return _coerce_json(text)


def _coerce_json(text: str) -> dict:
    """Parse a JSON object out of a possibly-noisy model reply."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip ```json fences / prose and retry on the outermost {...}.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}

_SYSTEM = """\
You assign persona attributes from a short free-text description of a person.

You are given the description and a list of candidate DIMENSIONS. Each dimension \
has an id, a question it answers, and a closed list of allowed VALUES. For every \
candidate dimension, decide whether the description gives real support for one of \
its allowed values.

Rules:
- Pick a value ONLY if the description supports it. When it does not, return the \
dimension with "value": null — do not guess to be helpful. Leaving a weakly \
supported dimension unassigned is correct, not a failure.
- The value MUST be copied verbatim from that dimension's allowed values. Never \
invent a value or use a synonym.
- "evidence" must be an exact substring quoted from the description that supports \
the value. If value is null, evidence is null.
- "confidence" is 0.0-1.0: how strongly the description supports this specific \
value versus the other allowed values of the same dimension.
- Judge each dimension independently against the description; do not let one \
assignment force another.
"""

# Structured-output schema for the judge's response.
_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "assignments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimension_id": {"type": "string"},
                    "value": {"type": ["string", "null"]},
                    "evidence": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": [
                    "dimension_id",
                    "value",
                    "evidence",
                    "confidence",
                    "reason",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["assignments"],
    "additionalProperties": False,
}


@dataclass
class JudgeAssignment:
    """One dimension the judge ruled on. ``value is None`` => not assigned."""

    dimension_id: str
    value: str | None
    evidence: str | None
    confidence: float
    reason: str


def _render_candidates(dims: list[Dimension]) -> str:
    """Compact, cache-stable rendering of the candidate dimensions."""
    lines = []
    for dim in dims:
        allowed = " | ".join(dim.values)
        lines.append(
            f"- id: {dim.id}\n"
            f"  question: {dim.label} — {dim.description}\n"
            f"  allowed_values: [{allowed}]"
        )
    return "\n".join(lines)


class LLMJudge:
    """Claude-backed judge over candidate dimensions.

    Parameters
    ----------
    schema:
        The dimension taxonomy (used to validate returned values).
    client:
        A pre-built client. For the ``anthropic`` backend this is an
        ``anthropic.Anthropic`` instance; for ``openai`` it is any object with a
        ``complete_json(system, user) -> dict`` method (e.g. the built-in
        :class:`_OpenAIChatClient`). If omitted, one is built lazily on first
        use, resolving credentials from the environment.
    model:
        Override the model id. Defaults to ``claude-opus-4-8``.
    backend:
        ``"anthropic"``, ``"openai"``, or ``"auto"`` (default — ``openai`` when
        ``OPENAI_API_KEY`` is set, else ``anthropic``).
    """

    def __init__(
        self,
        schema: DimensionSchema,
        client=None,
        model: str = _MODEL,
        backend: str = "auto",
    ) -> None:
        self.schema = schema
        self._client = client
        self.model = model
        self.backend = self._resolve_backend(backend)

    @staticmethod
    def _resolve_backend(backend: str) -> str:
        if backend != "auto":
            return backend
        return "openai" if _openai_available() else "anthropic"

    def _get_client(self):
        if self._client is not None:
            return self._client
        if self.backend == "openai":
            # Some gateways use a different model-id spelling (e.g. dotted
            # versions); OPENAI_MODEL overrides without touching the schema id.
            model = os.environ.get("OPENAI_MODEL", "").strip() or self.model
            self._client = _OpenAIChatClient(model)
        else:
            import anthropic  # lazy: only needed when the judge actually runs

            self._client = anthropic.Anthropic()
        return self._client

    def judge(self, prompt: str, candidate_dimension_ids: list[str]) -> list[JudgeAssignment]:
        """Ask Claude to assign values for the candidate dimensions.

        Returns one :class:`JudgeAssignment` per candidate the model ruled on.
        Assignments whose value is not in the dimension's allowed set, or whose
        dimension is unknown, are dropped defensively — the closed-value
        guarantee is enforced here regardless of backend.
        """
        dims = [d for d in (self.schema.get(i) for i in candidate_dimension_ids) if d]
        if not dims:
            return []

        user = (
            f"DESCRIPTION:\n{prompt}\n\n"
            f"CANDIDATE DIMENSIONS:\n{_render_candidates(dims)}\n\n"
            "Return a JSON object {\"assignments\": [...]} with one assignment "
            "object for every candidate dimension above."
        )

        data = (
            self._judge_openai(user)
            if self.backend == "openai"
            else self._judge_anthropic(user)
        )
        if data is None:
            return []

        out: list[JudgeAssignment] = []
        for item in data.get("assignments", []):
            # The anthropic backend is schema-bound to "dimension_id", but an
            # OpenAI-compatible endpoint has no json-schema enforcement, so the
            # model sometimes shortens it to "id" (or "dim_id"). Accept any.
            dim_id = (
                item.get("dimension_id")
                or item.get("id")
                or item.get("dim_id")
            )
            value = item.get("value")
            # Enforce the closed-value contract: keep null (unassigned) rulings,
            # but drop any non-null value that isn't actually allowed.
            if value is not None and not self.schema.is_valid_value(dim_id, value):
                continue
            out.append(
                JudgeAssignment(
                    dimension_id=dim_id,
                    value=value,
                    evidence=item.get("evidence"),
                    confidence=float(item.get("confidence", 0.0)),
                    reason=item.get("reason", ""),
                )
            )
        return out

    def _judge_anthropic(self, user: str) -> dict | None:
        """Run the judge through the anthropic SDK with structured outputs."""
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": _OUTPUT_SCHEMA}},
        )
        if response.stop_reason == "refusal":
            return None
        text = next((b.text for b in response.content if b.type == "text"), "")
        return json.loads(text)

    def _judge_openai(self, user: str) -> dict | None:
        """Run the judge through an OpenAI-compatible endpoint (raw-JSON prompt).

        These endpoints have no json-schema mode, so the client appends a
        "return only JSON" instruction and coerces the reply to a dict for us.
        """
        client = self._get_client()
        return client.complete_json(_SYSTEM, user)
