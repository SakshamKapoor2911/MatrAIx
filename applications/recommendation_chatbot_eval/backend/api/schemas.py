"""Pydantic v2 request/response models for the RecBot Studio API.

These models mirror the wire contract one-to-one with the TypeScript types in
``web/src/lib/types.ts`` and the service-layer view objects
(:class:`~backend.service.trace_view.TraceView` output,
:class:`~backend.service.session.RecBotSession`, catalog items). The JSON wire
format is ``camelCase`` throughout, matching the rest of the contract and the
SPA.

Design notes:

* The service layer already produces plain ``dict`` views in exactly this shape
  (e.g. ``TurnView``, ``Session``, ``SessionSummary``). The response models are
  therefore deliberately permissive: they ``model_validate`` those dicts to
  validate / document the contract without forcing the service to construct
  pydantic objects. ``model_config = ConfigDict(extra="allow")`` lets
  forward-compatible extra fields (should the service add any) pass through
  rather than being silently dropped.
* Request models are strict where it matters (``message`` is required and
  trimmed-non-empty; ``config`` keys are validated downstream by
  :class:`~backend.service.config.ConfigManager`), but tolerant of partial
  configs so the PATCH/POST bodies stay ergonomic.
* No backend (RecAI / numpy) import happens here; this module is stdlib +
  pydantic only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "HealthResponse",
    "PreflightCheck",
    "PreflightResponse",
    "ConfigOptionValue",
    "ConfigKnob",
    "ConfigEnvironment",
    "ConfigOptionsResponse",
    "ChatMessageModel",
    "PlanStep",
    "RecommendedItem",
    "TurnView",
    "SessionConfig",
    "Session",
    "SessionSummary",
    "CreateSessionRequest",
    "PatchConfigRequest",
    "PatchConfigResponse",
    "SubmitTurnRequest",
    "SubmitTurnResponse",
    "JobView",
    "CatalogItem",
    "CatalogSearchResponse",
    "StartPersonaEvalRequest",
    "SubmitPersonaEvalResponse",
    "PersonaSummary",
    "PersonaEvalPersonasResponse",
    "GoalContext",
    "GoalContextsResponse",
    "PersonaEvalJobView",
    "PersonaEvalRunSummary",
    "PersonaEvalRunsResponse",
    "PersonaEvalResultView",
]

#: Domains the persona-eval (and the rest of the Studio) supports. Mirrors the
#: ``domain`` option enumerated by
#: :class:`~backend.service.config.ConfigManager` (movie / beauty_product /
#: game) so a bad domain is rejected here with a clean 422.
SUPPORTED_DOMAINS = ("movie", "beauty_product", "game")


# --------------------------------------------------------------------------- #
# Health / preflight
# --------------------------------------------------------------------------- #
class HealthResponse(BaseModel):
    """``GET /api/health`` payload."""

    status: str = "ok"


class PreflightCheck(BaseModel):
    """One environment/resource readiness probe."""

    name: str
    ok: bool
    detail: str


class PreflightResponse(BaseModel):
    """``GET /api/preflight`` payload."""

    ready: bool
    checks: List[PreflightCheck]


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
class ConfigOptionValue(BaseModel):
    """One selectable value for an editable config knob, with display metadata."""

    model_config = ConfigDict(extra="allow")

    value: str
    label: str
    description: str = ""


class ConfigKnob(BaseModel):
    """One user-editable config knob and its allowed values.

    ``rebuildsAgent`` is ``True`` when changing this knob cold-starts the cached
    agent (a slower next turn); the UI surfaces that so the operator is not
    surprised.
    """

    model_config = ConfigDict(extra="allow")

    key: str
    label: str
    description: str = ""
    options: List[ConfigOptionValue] = Field(default_factory=list)
    rebuildsAgent: bool = False


class ConfigEnvironment(BaseModel):
    """Read-only facts about the fixed parts of the stack.

    The ranker (native SASRec), the resource bundle (``all_resources``), and the
    agent (``InteRecAgent``) are not user-configurable; they are reported so the
    UI can show what is fixed and why.
    """

    model_config = ConfigDict(extra="allow")

    ranker: str
    resources: str
    agent: str


class ConfigOptionsResponse(BaseModel):
    """``GET /api/config/options`` payload.

    ``knobs`` is the list of user-editable config knobs (each with per-value
    labels/descriptions and a ``rebuildsAgent`` flag); ``defaults`` is the full
    canonical default config (every key, including the fixed ranker/resource
    modes); ``environment`` reports the fixed parts of the stack. All come
    straight from :meth:`~backend.service.config.ConfigManager.options`.
    """

    model_config = ConfigDict(extra="allow")

    knobs: List[ConfigKnob] = Field(default_factory=list)
    defaults: Dict[str, str]
    environment: ConfigEnvironment


# --------------------------------------------------------------------------- #
# Chat / turn view (TraceView.build output)
# --------------------------------------------------------------------------- #
class ChatMessageModel(BaseModel):
    """A single chat message in a session transcript."""

    role: str
    content: str


class PlanStep(BaseModel):
    """A parsed step of the agent's tool plan (best-effort)."""

    model_config = ConfigDict(extra="allow")

    tool: str
    detail: Optional[str] = None
    status: str = "ok"

    @field_validator("tool", mode="before")
    @classmethod
    def _coerce_tool(cls, value: Any) -> str:
        # Legacy artifacts may carry a non-string / missing tool name; coerce so
        # an old persisted session still opens (see ``TurnView.turnId``).
        if value is None:
            return "step"
        return value if isinstance(value, str) else str(value)


class RecommendedItem(BaseModel):
    """A recommended item, resolved against the catalog where possible."""

    model_config = ConfigDict(extra="allow")

    itemId: str
    rank: Optional[int] = None
    title: Optional[str] = None
    meta: Optional[str] = None
    score: Optional[float] = None

    @field_validator("itemId", mode="before")
    @classmethod
    def _coerce_item_id(cls, value: Any) -> str:
        # The native backend keys items by int id; legacy artifacts may persist
        # that int. Coerce to the contract's string id so old runs still open.
        if value is None:
            return ""
        return value if isinstance(value, str) else str(value)


class TurnView(BaseModel):
    """The fully-built view of one conversational turn.

    Mirrors :meth:`backend.service.trace_view.TraceView.build`. Extra fields are
    allowed so the service can enrich the view without breaking the schema.
    """

    model_config = ConfigDict(extra="allow")

    turnId: Optional[str] = None
    conversationId: Optional[str] = None
    backend: Optional[str] = None
    userMessage: Optional[str] = None
    assistantMessage: Optional[str] = None
    plan: List[PlanStep] = Field(default_factory=list)
    recommendedItems: List[RecommendedItem] = Field(default_factory=list)
    nativeRaw: Optional[str] = None
    rawToolOutputs: Any = None

    @field_validator("turnId", "conversationId", mode="before")
    @classmethod
    def _coerce_optional_str(cls, value: Any) -> Optional[str]:
        # Legacy persisted turns store ``turnId`` as an int (the native backend's
        # 0-based turn index); the wire/UI contract treats it as a string.
        # Coerce int -> str here so an old session opens instead of 500-ing on
        # response validation. ``None`` stays ``None``.
        if value is None or isinstance(value, str):
            return value
        return str(value)


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #
class SessionConfig(BaseModel):
    """Full session configuration (camelCase on the wire)."""

    model_config = ConfigDict(extra="allow")

    engine: str
    rankerMode: str
    resourceMode: str
    domain: str
    botType: str


class Session(BaseModel):
    """Full session record. Mirrors
    :meth:`backend.service.session.RecBotSession.to_dict`."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    config: Dict[str, Any]
    messages: List[ChatMessageModel] = Field(default_factory=list)
    turns: List[TurnView] = Field(default_factory=list)
    createdAt: str


class SessionSummary(BaseModel):
    """Lightweight session entry for the left rail. Mirrors
    :meth:`backend.service.session.RecBotSession.summary`."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    config: Dict[str, Any]
    turnCount: int = 0
    messageCount: int = 0
    createdAt: Optional[str] = None


class CreateSessionRequest(BaseModel):
    """Body for ``POST /api/sessions``. Both fields optional."""

    title: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class PatchConfigRequest(BaseModel):
    """Body for ``PATCH /api/sessions/{id}/config``."""

    config: Dict[str, Any]


class PatchConfigResponse(BaseModel):
    """Response of ``PATCH /api/sessions/{id}/config``."""

    session: Session
    cacheInvalidated: bool


# --------------------------------------------------------------------------- #
# Turns & jobs (async)
# --------------------------------------------------------------------------- #
class SubmitTurnRequest(BaseModel):
    """Body for ``POST /api/sessions/{id}/turns``."""

    message: str


class SubmitTurnResponse(BaseModel):
    """Response of ``POST /api/sessions/{id}/turns``."""

    jobId: str


class JobView(BaseModel):
    """``GET /api/jobs/{jobId}`` payload.

    ``status`` is one of ``building | running | done | error``. ``turn`` is
    populated only on ``done``; ``error`` only on ``error``.
    """

    model_config = ConfigDict(extra="allow")

    jobId: str
    status: str
    turn: Optional[TurnView] = None
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Catalog
# --------------------------------------------------------------------------- #
class CatalogItem(BaseModel):
    """A normalized catalog item (the subset the UI surfaces).

    Built from a raw ``items.jsonl`` line, which uses snake_case keys
    (``item_id`` / ``display_text``); :func:`~backend.api.routes` adapts those to
    the camelCase wire shape before validation, but ``extra="allow"`` keeps the
    adapter forgiving.
    """

    model_config = ConfigDict(extra="allow")

    itemId: str
    title: Optional[str] = None
    description: Optional[str] = None
    displayText: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CatalogSearchResponse(BaseModel):
    """``GET /api/catalog/search`` payload."""

    items: List[CatalogItem]
    total: int


# --------------------------------------------------------------------------- #
# Persona eval (persona-driven evaluation)
# --------------------------------------------------------------------------- #
class StartPersonaEvalRequest(BaseModel):
    """Body for ``POST /api/persona-eval``.

    ``domain`` must be one of the supported domains (:data:`SUPPORTED_DOMAINS`);
    ``maxTurns`` is bounded to a sensible 1..20 so a demo run cannot wedge the
    process-global persona-eval lock for an unbounded number of turns.
    """

    domain: str
    personaId: str
    maxTurns: int = Field(default=8, ge=1, le=20)
    goalContextId: Optional[str] = None
    #: The OpenAI chat model that drives BOTH the recommender (per-run
    #: ``INTERECAGENT_ENGINE``) and the user-simulator. ``None`` falls back to the
    #: service default (``ConfigManager.DEFAULTS['engine']``).
    engine: Optional[str] = None

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, value: str) -> str:
        if value not in SUPPORTED_DOMAINS:
            raise ValueError(
                "domain must be one of {}".format(list(SUPPORTED_DOMAINS))
            )
        return value


class SubmitPersonaEvalResponse(BaseModel):
    """Response of ``POST /api/persona-eval``."""

    jobId: str


class PersonaSummary(BaseModel):
    """A persona as surfaced by ``GET /api/persona-eval/personas``.

    Domain-free: the lightweight subset the PersonaPicker needs, built from
    :class:`persona_eval.types.Persona`. ``source`` is the curated dataset the
    persona came from (e.g. ``Nemotron``); ``blurb`` is a short preview of the
    persona context.
    """

    id: str
    name: str
    source: str
    blurb: str


class PersonaEvalPersonasResponse(BaseModel):
    """``GET /api/persona-eval/personas`` payload.

    The full (un-filtered) persona catalog, honoring optional ``q``/``limit``
    search. ``sutDescription`` is returned only when an optional ``domain`` is
    supplied (the system-under-test blurb for that domain); otherwise omitted.
    """

    model_config = ConfigDict(extra="allow")

    personas: List[PersonaSummary]
    sutDescription: Optional[str] = None


class PersonaEvalPersonaDetail(BaseModel):
    """``GET /api/persona-eval/personas/{id}`` payload — one full persona.

    Carries the complete, humanized ``context`` block (multi-line, far richer
    than the list ``blurb``) so the catalog's "full persona" view can show
    everything without waiting for a run.
    """

    id: str
    name: str
    source: str
    context: str


class GoalContext(BaseModel):
    """A selectable goal/context prompt. Mirrors
    :meth:`persona_eval.goal_contexts.GoalContext.to_dict` (sans ``template``)."""

    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    description: str


class GoalContextsResponse(BaseModel):
    """``GET /api/persona-eval/goal-contexts`` payload."""

    goalContexts: List[GoalContext]


class PersonaEvalJobView(BaseModel):
    """``GET /api/persona-eval/jobs/{jobId}`` payload.

    Mirrors :meth:`backend.service.persona_eval_service.PersonaEvalProgress.to_view`.
    ``status`` is one of ``building | running | done | error``. ``questionnaire``
    / ``metricScores`` populate only on ``done``; ``error`` only on ``error``.
    ``turns`` are full ``TurnView`` dicts (identical to manual chat) so the SPA
    can render them with the same component. Permissive so the service can
    enrich the view without breaking the schema.
    """

    model_config = ConfigDict(extra="allow")

    jobId: str
    domain: str
    personaId: str
    personaName: str
    sutDescription: str
    goalContextId: Optional[str] = None
    status: str
    phase: Optional[str] = None
    turns: List[TurnView] = Field(default_factory=list)
    questionnaire: Optional[Dict[str, Any]] = None
    metricScores: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Persisted persona-eval runs (durable artifacts)
# --------------------------------------------------------------------------- #
class PersonaEvalRunSummary(BaseModel):
    """One entry in ``GET /api/persona-eval/runs``.

    A newest-first summary of a persisted run, built from the stored
    ``<jobId>.json`` artifact by
    :meth:`backend.service.persona_eval_service.PersonaEvalService.list_runs`.
    Permissive so the service can enrich the summary without breaking the schema.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    createdAt: Optional[str] = None
    domain: Optional[str] = None
    personaName: Optional[str] = None
    source: Optional[str] = None
    goalContextId: Optional[str] = None
    overallRating: Optional[int] = None
    numTurns: Optional[int] = None


class PersonaEvalRunsResponse(BaseModel):
    """``GET /api/persona-eval/runs`` payload."""

    runs: List[PersonaEvalRunSummary]


class PersonaEvalResultView(BaseModel):
    """``GET /api/persona-eval/runs/{id}`` payload — the full stored run.

    Mirrors :meth:`persona_eval.types.PersonaEvalResult.to_dict` plus the top-level
    ``id`` injected at persist time. Permissive (``extra="allow"``) so the stored
    artifact round-trips without forcing the service to construct pydantic
    objects.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    createdAt: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    persona: Dict[str, Any] = Field(default_factory=dict)
    sutDescription: Optional[str] = None
    transcript: List[Dict[str, Any]] = Field(default_factory=list)
    recommendedItemIds: Dict[str, Any] = Field(default_factory=dict)
    questionnaire: Optional[Dict[str, Any]] = None
    metricScores: Optional[Dict[str, Any]] = None
