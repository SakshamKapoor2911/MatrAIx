"""Pydantic v2 request/response models for the PersonaEval API.

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

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    "SurveyQuestion",
    "SurveyInstrument",
    "SurveyInstrumentsResponse",
    "StartSurveyEvalRequest",
    "SurveyEvalJobView",
    "WebEvalTask",
    "WebEvalTasksResponse",
    "StartWebEvalRequest",
    "WebEvalJobView",
    "CuaEvalTask",
    "CuaEvalTasksResponse",
    "AppWorldEvalTask",
    "AppWorldEvalTasksResponse",
    "StartAppWorldEvalRequest",
    "AppWorldEvalJobView",
]

#: Domains the persona-eval (and the rest of the Studio) supports. Mirrors the
#: ``domain`` option enumerated by
#: :class:`~backend.service.config.ConfigManager` (movie / beauty_product /
#: game) so a bad domain is rejected here with a clean 422.
SUPPORTED_DOMAINS = ("movie", "beauty_product", "game")
SUPPORTED_APPLICATION_IDS = ("recai", "finance_openbb", "medical_assistant")
DEFAULT_APPLICATION_CONTEXTS = {
    "finance_openbb": "financial_research",
    "medical_assistant": "medical_consultation",
}
SUPPORTED_PERSONA_MODELS = (
    "anthropic/claude-haiku-4-5",
    "anthropic/claude-sonnet-4-6",
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
)


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
    #: Coarse area this check belongs to ("Core" / "Chatbot" / "Survey" / "Web")
    #: so the UI can group the overall-readiness checklist. Optional for back-compat.
    group: Optional[str] = None
    #: Optional adapters (the finance/medical sidecars) report their status but
    #: do not gate overall readiness, and render muted rather than as an error.
    optional: bool = False
    #: When set, maps this probe to a chatbot application card in the cockpit.
    applicationId: Optional[str] = None


class PreflightResponse(BaseModel):
    """``GET /api/preflight`` payload."""

    ready: bool
    checks: List[PreflightCheck]


class ChatbotSidecarStatus(BaseModel):
    """Reachability of one chatbot HTTP sidecar."""

    applicationId: str
    ok: bool
    healthUrl: str
    canStart: bool = True
    detail: str


class ChatbotSidecarsResponse(BaseModel):
    """``GET /api/chatbot-sidecars`` payload."""

    sidecars: List[ChatbotSidecarStatus]


class StartChatbotSidecarResponse(BaseModel):
    """``POST /api/chatbot-sidecars/{application_id}/start`` payload."""

    sidecar: ChatbotSidecarStatus
    started: bool = True


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

    ``runtime`` / ``personaAgent`` / ``personaModel`` / ``applicationApi`` /
    ``scorer`` report the local PersonaEval execution boundary. The ranker,
    resources, and agent are adapter-specific and not user-configurable.
    ``promptOwnership`` reports the prompt boundary for local runs.
    """

    model_config = ConfigDict(extra="allow")

    runtime: str
    personaAgent: str
    personaModel: str
    applicationApi: str
    scorer: str
    cache: str
    ranker: str
    resources: str
    agent: str
    promptOwnership: Dict[str, str]


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

    ``applicationId`` selects the chatbot application adapter. ``domain`` is the
    legacy RecAI context; non-RecAI applications use ``applicationContext`` for
    their own context and normalize ``domain`` to that value.
    ``maxTurns`` is bounded to a sensible 1..20 so a demo run cannot wedge the
    process-global persona-eval lock for an unbounded number of turns.
    """

    domain: Optional[str] = None
    applicationId: str = "recai"
    applicationContext: Optional[str] = None
    personaId: str
    maxTurns: int = Field(default=8, ge=1, le=20)
    goalContextId: Optional[str] = None
    #: The OpenAI chat model that drives the recommender (per-run
    #: ``INTERECAGENT_ENGINE``). ``None`` falls back to the service default
    #: (``ConfigManager.DEFAULTS['engine']``).
    engine: Optional[str] = None
    #: Persona-agent base model. ``None`` falls back to the local persona model
    #: default / env override.
    personaModel: Optional[str] = None

    @field_validator("applicationId")
    @classmethod
    def _validate_application_id(cls, value: str) -> str:
        if value not in SUPPORTED_APPLICATION_IDS:
            raise ValueError(
                "applicationId must be one of {}".format(
                    list(SUPPORTED_APPLICATION_IDS)
                )
            )
        return value

    @model_validator(mode="after")
    def _normalize_application_context(self) -> "StartPersonaEvalRequest":
        if self.applicationId == "recai":
            self.domain = self.domain or "movie"
            if self.domain not in SUPPORTED_DOMAINS:
                raise ValueError(
                    "domain must be one of {}".format(list(SUPPORTED_DOMAINS))
                )
            if self.applicationContext is None:
                self.applicationContext = self.domain
            return self

        default_context = DEFAULT_APPLICATION_CONTEXTS.get(self.applicationId)
        self.applicationContext = self.applicationContext or default_context
        if not self.applicationContext:
            raise ValueError("applicationContext is required")
        self.domain = self.applicationContext
        return self

    @field_validator("personaModel")
    @classmethod
    def _validate_persona_model(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in SUPPORTED_PERSONA_MODELS:
            raise ValueError(
                "personaModel must be one of {}".format(list(SUPPORTED_PERSONA_MODELS))
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
    applicationId: Optional[str] = None
    applicationContext: Optional[str] = None
    personaId: str
    personaName: str
    sutDescription: str
    goalContextId: Optional[str] = None
    status: str
    phase: Optional[str] = None
    turns: List[TurnView] = Field(default_factory=list)
    questionnaire: Optional[Dict[str, Any]] = None
    metricScores: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, str]] = None
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Survey eval
# --------------------------------------------------------------------------- #
class SurveyQuestion(BaseModel):
    """One survey question in a task-owned survey instrument."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    prompt: str
    type: str
    options: List[str] = Field(default_factory=list)
    minValue: Optional[int] = None
    maxValue: Optional[int] = None
    construct_: str = Field(default="", alias="construct")
    required: bool = True


class SurveyInstrument(BaseModel):
    """A survey instrument available for persona-agent completion."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    description: str = ""
    questions: List[SurveyQuestion] = Field(default_factory=list)


class SurveyInstrumentsResponse(BaseModel):
    """``GET /api/survey-eval/instruments`` payload."""

    instruments: List[SurveyInstrument]


class SurveyHarborTask(BaseModel):
    """A Harbor example-survey task available for persona-agent testing."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    description: str = ""
    taskPath: str
    instrumentId: str = ""
    profileMarkdown: str = ""
    instructionMarkdown: str = ""
    surveyKind: Literal["example", "contributing"] = "contributing"


class SurveyHarborTasksResponse(BaseModel):
    """``GET /api/survey-eval/harbor-tasks`` payload."""

    tasks: List[SurveyHarborTask]


class StartSurveyEvalRequest(BaseModel):
    """Body for ``POST /api/survey-eval``."""

    personaId: str
    instrumentId: str = "chatgpt_images_market_research_v1"
    personaModel: Optional[str] = None

    @field_validator("personaModel")
    @classmethod
    def _validate_persona_model(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in SUPPORTED_PERSONA_MODELS:
            raise ValueError(
                "personaModel must be one of {}".format(list(SUPPORTED_PERSONA_MODELS))
            )
        return value


class SurveyEvalJobView(BaseModel):
    """Live view of a local survey run.

    ``surveyResult`` is the evaluation artifact. There is no additional
    chatbot-style scorecard layer for survey tasks.
    """

    model_config = ConfigDict(extra="allow")

    jobId: str
    applicationType: str = "survey"
    taskId: str = "survey_form"
    instrumentId: str
    instrumentTitle: str
    personaId: str
    personaName: str
    status: str
    phase: Optional[str] = None
    surveyResult: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, str]] = None
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Web eval
# --------------------------------------------------------------------------- #
class WebEvalTask(BaseModel):
    """A hosted website task available for persona-agent testing."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    siteName: str
    siteUrl: str
    description: str = ""
    taskPath: str = ""
    outputArtifact: str = "ecommerce_interaction.json"
    submissionProfile: str = "ecommerce_interaction"


class WebEvalTasksResponse(BaseModel):
    """``GET /api/web-eval/tasks`` payload."""

    tasks: List[WebEvalTask]


class StartWebEvalRequest(BaseModel):
    """Body for ``POST /api/web-eval``."""

    personaId: str
    taskId: str = "web-ecommerce-platform_product-discovery"
    personaModel: Optional[str] = None

    @field_validator("personaModel")
    @classmethod
    def _validate_persona_model(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in SUPPORTED_PERSONA_MODELS:
            raise ValueError(
                "personaModel must be one of {}".format(list(SUPPORTED_PERSONA_MODELS))
            )
        return value


class WebEvalJobView(BaseModel):
    """Live view of a local website run."""

    model_config = ConfigDict(extra="allow")

    jobId: str
    applicationType: str = "web"
    taskId: str
    taskTitle: str
    siteName: str
    siteUrl: str
    personaId: str
    personaName: str
    status: str
    phase: Optional[str] = None
    webResult: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, str]] = None
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# CUA (computer-use) eval
# --------------------------------------------------------------------------- #
class CuaEvalTask(BaseModel):
    """A Harbor computer-use task available for persona-agent testing."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    platform: str
    description: str = ""
    taskPath: str
    outputArtifact: str = "decision.json"
    cuaSubmissionProfile: Optional[str] = None
    environmentLabel: str = "persona-computer-1"
    cuaBackend: str = "docker"


class CuaEvalTasksResponse(BaseModel):
    """``GET /api/cua-eval/tasks`` payload."""

    tasks: List[CuaEvalTask]


# --------------------------------------------------------------------------- #
# AppWorld eval
# --------------------------------------------------------------------------- #
class AppWorldEvalTask(BaseModel):
    """An AppWorld API task available for persona-agent testing."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    appName: str
    description: str = ""
    outputArtifact: str = "appworld_result.json"
    submissionProfile: str = "appworld_result"


class AppWorldEvalTasksResponse(BaseModel):
    """``GET /api/appworld-eval/tasks`` payload."""

    tasks: List[AppWorldEvalTask]


class StartAppWorldEvalRequest(BaseModel):
    """Body for ``POST /api/appworld-eval``."""

    personaId: str
    taskId: str = "appworld-demo-personal-admin"
    personaModel: Optional[str] = None

    @field_validator("personaModel")
    @classmethod
    def _validate_persona_model(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in SUPPORTED_PERSONA_MODELS:
            raise ValueError(
                "personaModel must be one of {}".format(list(SUPPORTED_PERSONA_MODELS))
            )
        return value


class AppWorldEvalJobView(BaseModel):
    """Live view of an AppWorld run."""

    model_config = ConfigDict(extra="allow")

    jobId: str
    applicationType: str = "appworld"
    taskId: str
    taskTitle: str
    appName: str
    personaId: str
    personaName: str
    status: str
    phase: Optional[str] = None
    appworldResult: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, str]] = None
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Harbor batch jobs (jobs_dir — canonical artifact root)
# --------------------------------------------------------------------------- #
class HarborJobLaunchRequest(BaseModel):
    """Body for ``POST /api/harbor/jobs``."""

    taskPath: str
    sampleSize: int = 1
    seed: int = 42
    personaPool: str = "persona/datasets/bench-dev-sample"
    personaIds: Optional[List[str]] = None
    personaSources: Optional[List[str]] = None
    personaFilters: Optional[Dict[str, str]] = None
    cohortId: Optional[str] = None
    agentName: Optional[str] = None
    personaModel: Optional[str] = None
    nConcurrentTrials: int = 2
    mode: str = "auto"
    jobName: Optional[str] = None
    surveyInstrumentId: Optional[str] = None
    cuaSubmissionProfile: Optional[str] = None
    cuaBackend: Optional[str] = None
    chatDomain: Optional[str] = None
    chatApplicationId: Optional[str] = None
    chatApplicationContext: Optional[str] = None
    chatGoalContextId: Optional[str] = None
    chatMaxTurns: Optional[int] = None

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"auto", "force_docker", "smoke"}:
            raise ValueError("mode must be one of auto, force_docker, smoke")
        return normalized

    @field_validator("personaModel")
    @classmethod
    def _validate_persona_model(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in SUPPORTED_PERSONA_MODELS:
            raise ValueError(
                "personaModel must be one of {}".format(list(SUPPORTED_PERSONA_MODELS))
            )
        return value


class HarborJobLaunchResponse(BaseModel):
    jobName: str
    configPath: Optional[str] = None
    jobsDir: Optional[str] = None
    agentName: Optional[str] = None
    taskType: Optional[str] = None
    trialProfile: Optional[str] = None
    mode: Optional[str] = None


class HarborJobsListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    jobs: List[Dict[str, Any]]


class HarborJobDetailView(BaseModel):
    model_config = ConfigDict(extra="allow")

    jobName: str
    jobsDir: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    trials: List[Dict[str, Any]] = Field(default_factory=list)
    launch: Optional[Dict[str, Any]] = None


class PersonaPoolCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    pool: str
    count: int
    smokePersonaId: Optional[str] = None
    sourceCounts: Dict[str, int] = Field(default_factory=dict)
    schemaVersion: Optional[str] = None
    dimensionCategoriesPath: Optional[str] = None
    dimensionCategories: Dict[str, Any] = Field(default_factory=dict)


class PersonaPoolSampleRequest(BaseModel):
    pool: str = "persona/datasets/bench-dev-sample"
    sampleSize: int = 4
    seed: int = 42
    sources: Optional[List[str]] = None
    dimensionFilters: Optional[Dict[str, Any]] = None
    stratifyFields: Optional[List[str]] = None
    sampleSizePerValueGroup: Optional[int] = None


class PersonaPoolPersonaCard(BaseModel):
    model_config = ConfigDict(extra="allow")

    personaId: str
    name: Optional[str] = None
    source: Optional[str] = None
    path: Optional[str] = None
    dimensions: Dict[str, str] = Field(default_factory=dict)


class PersonaPoolCardsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    pool: str
    personas: List[PersonaPoolPersonaCard] = Field(default_factory=list)


class PersonaPoolPersonaDetailResponse(PersonaPoolPersonaCard):
    model_config = ConfigDict(extra="allow")

    pool: str
    yaml: str = ""
    profileMarkdown: str = ""


class TaskDetailResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    taskPath: str
    title: str = ""
    description: str = ""
    metaType: str = ""
    taskName: str = ""
    instructionMarkdown: str = ""
    profileMarkdown: str = ""


class PersonaPoolSampleResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    pool: str
    matchedCount: int
    sampleSize: int
    seed: int
    personaIds: List[str]
    personas: List[Dict[str, Any]] = Field(default_factory=list)


class PersonaCohortSaveRequest(BaseModel):
    cohortId: str
    name: Optional[str] = None
    description: Optional[str] = None
    pool: str = "persona/datasets/bench-dev-sample"
    kind: str = "recipe"
    seed: int = 42
    sampleSize: int = 4
    sources: Optional[List[str]] = None
    dimensionFilters: Optional[Dict[str, str]] = None
    personaIds: Optional[List[str]] = None

    @field_validator("kind")
    @classmethod
    def _validate_kind(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"recipe", "frozen"}:
            raise ValueError("kind must be recipe or frozen")
        return normalized


class PersonaCohortSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    cohortId: str
    name: str
    kind: str
    pool: str
    sampleSize: int
    matchedCount: int
    personaCount: int
    createdAt: Optional[str] = None


class PersonaCohortListResponse(BaseModel):
    cohorts: List[PersonaCohortSummary] = Field(default_factory=list)


class PersonaCohortDetailResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    cohortId: str
    name: str
    description: str = ""
    createdAt: Optional[str] = None
    pool: str
    kind: str
    seed: int
    sampleSize: int
    sources: List[str] = Field(default_factory=list)
    dimensionFilters: Dict[str, str] = Field(default_factory=dict)
    matchedCount: int
    personaIds: List[str] = Field(default_factory=list)
    personas: List[Dict[str, Any]] = Field(default_factory=list)
