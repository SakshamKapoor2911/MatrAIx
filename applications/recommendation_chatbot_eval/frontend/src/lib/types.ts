/**
 * TypeScript mirror of the RecBot Studio API contract.
 *
 * These types track the FastAPI pydantic models in `harness/api/schemas.py`
 * and the service-layer view objects (TurnView, Session, CatalogItem). Keep
 * this file in sync with the backend contract; the typed fetch client in
 * `./api.ts` returns these shapes directly.
 */

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

/** Allowed value for the `engine` knob (the chat LLM). */
export type Engine = "gpt-4o-mini" | "gpt-4o";

/** Candidate ranking strategy. */
export type RankerMode = "semantic_profile" | "native";

/** Where the agent's catalog / resources come from. */
export type ResourceMode = "matraix_catalog" | "recai_resources";

/** Recommendation domain. The backend supports all three. */
export type Domain = "movie" | "beauty_product" | "game";

/** RecAI bot driver. */
export type BotType = "chat" | "completion";

/**
 * Full session configuration. Mirrors `ConfigManager` defaults/allowed values.
 * `camelCase` on the wire to match the rest of the JSON contract.
 */
export interface SessionConfig {
  engine: Engine;
  rankerMode: RankerMode;
  resourceMode: ResourceMode;
  domain: Domain;
  botType: BotType;
}

/**
 * One selectable value for an editable config knob, with display metadata.
 * Mirrors the backend `ConfigOptionValue`.
 */
export interface ConfigOptionValue {
  value: string;
  label: string;
  description: string;
}

/**
 * One user-editable config knob and its allowed values. Mirrors the backend
 * `ConfigKnob`. `key` is a `SessionConfig` field name (e.g. `engine`, `domain`,
 * `botType`); `rebuildsAgent` is true when changing it cold-starts the cached
 * agent (a slower next turn), so the UI can warn the operator.
 */
export interface ConfigKnob {
  key: string;
  label: string;
  description: string;
  options: ConfigOptionValue[];
  rebuildsAgent: boolean;
}

/**
 * Read-only facts about the fixed parts of the stack (the "Environment" facts
 * popover). Mirrors the backend `ConfigEnvironment`: the ranker (native SASRec),
 * the resource bundle (`all_resources`), and the agent (`InteRecAgent`) are not
 * user-configurable.
 */
export interface ConfigEnvironment {
  ranker: string;
  resources: string;
  agent: string;
}

/**
 * `GET /api/config/options` payload (enriched shape). Mirrors the backend
 * `ConfigOptionsResponse`:
 *   - `knobs`       — the user-editable knobs, each with per-value labels and a
 *                     `rebuildsAgent` flag.
 *   - `defaults`    — the *full* canonical default config (every key, including
 *                     the fixed ranker/resource modes), keyed by the same
 *                     camelCase `SessionConfig` field names.
 *   - `environment` — the read-only fixed-stack facts.
 */
export interface ConfigOptionsResponse {
  knobs: ConfigKnob[];
  defaults: SessionConfig;
  environment: ConfigEnvironment;
}

// ---------------------------------------------------------------------------
// Health / preflight
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: "ok";
}

/** One environment/resource check from the preflight probe. */
export interface PreflightCheck {
  name: string;
  ok: boolean;
  detail: string;
}

/** `GET /api/preflight` payload. */
export interface PreflightResponse {
  ready: boolean;
  checks: PreflightCheck[];
}

// ---------------------------------------------------------------------------
// Chat / messages
// ---------------------------------------------------------------------------

export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

// ---------------------------------------------------------------------------
// Turn view (TraceView.build output)
// ---------------------------------------------------------------------------

/** Lifecycle status of an individual tool-plan step. */
export type PlanStepStatus = "ok" | "pending" | "error";

/**
 * A single parsed step of the agent's tool plan
 * (BufferStore / HardFilter / Rank / Map, best-effort).
 */
export interface PlanStep {
  tool: string;
  detail: string;
  status: PlanStepStatus;
}

/** A recommended item, resolved against the catalog where possible. */
export interface RecommendedItem {
  itemId: string;
  /** 1-based rank in the recommendation list (as emitted by `TraceView`). */
  rank: number;
  title: string | null;
  meta: string | null;
  score?: number | null;
}

/**
 * The fully-built view of one conversational turn — what the inspector and
 * chat thread render. Produced by `TraceView.build`.
 */
export interface TurnView {
  turnId: string;
  /** Backend conversation id (mirrors `result.conversation_id`). */
  conversationId?: string | null;
  /** Backend identifier, e.g. `"interecagent"`. */
  backend?: string | null;
  userMessage: string;
  assistantMessage: string;
  plan: PlanStep[];
  recommendedItems: RecommendedItem[];
  /** Raw `native_action.raw` text (model-native output), for the raw panel. */
  nativeRaw: string | null;
  /** Raw tool outputs, opaque structure, shown collapsed. */
  rawToolOutputs: unknown;
  /** Optional wall-clock duration of the turn, in seconds. */
  durationSeconds?: number | null;
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

/** Full session record. Mirrors `RecBotSession`. */
export interface Session {
  id: string;
  title: string;
  config: SessionConfig;
  messages: ChatMessage[];
  turns: TurnView[];
  createdAt: string;
}

/** Lightweight session entry for the left rail (`GET /api/sessions`). */
export interface SessionSummary {
  id: string;
  title: string;
  config: SessionConfig;
  turnCount: number;
  /** Number of chat messages (mirrors `session.summary()`). */
  messageCount?: number;
  createdAt: string;
}

/** Response of `PATCH /api/sessions/{id}/config`. */
export interface PatchConfigResponse {
  session: Session;
  cacheInvalidated: boolean;
}

// ---------------------------------------------------------------------------
// Jobs (async turns)
// ---------------------------------------------------------------------------

/**
 * Async-turn job lifecycle.
 * `building` -> warming/initialising the agent (cold start),
 * `running`  -> executing the turn,
 * `done`     -> `turn` is populated,
 * `error`    -> `error` carries the message.
 */
export type JobStatus = "building" | "running" | "done" | "error";

/** `POST /api/sessions/{id}/turns` response. */
export interface SubmitTurnResponse {
  jobId: string;
}

/** `GET /api/jobs/{jobId}` response. */
export interface JobView {
  jobId: string;
  status: JobStatus;
  turn?: TurnView | null;
  error?: string | null;
}

// ---------------------------------------------------------------------------
// Catalog
// ---------------------------------------------------------------------------

/** A normalized catalog item (subset of the JSONL schema we surface). */
export interface CatalogItem {
  itemId: string;
  title: string;
  description?: string | null;
  displayText?: string | null;
  categories: string[];
  metadata: Record<string, unknown>;
}

/** `GET /api/catalog/search` response. */
export interface CatalogSearchResponse {
  items: CatalogItem[];
  total: number;
}

/** Query parameters accepted by the catalog search endpoint. */
export interface CatalogSearchParams {
  q?: string;
  genre?: string;
  limit?: number;
  /** Which domain's catalog to browse (the real per-domain bundle). */
  domain?: Domain;
}

// ---------------------------------------------------------------------------
// Persona Eval (persona-driven live evaluation)
// ---------------------------------------------------------------------------

/**
 * A persona offered for a persona-eval run. Mirrors the backend `PersonaSummary`
 * (the domain-free trimmed projection of `persona_eval.types.Persona`).
 *
 * `source` distinguishes synthetic fixtures from curated datasets; `blurb` is a
 * short preview of the persona context.
 */
export interface PersonaEvalPersona {
  id: string;
  name: string;
  source: string;
  blurb: string;
}

/**
 * `GET /api/persona-eval/personas/{id}` payload — one persona's full record.
 * Mirrors the backend `PersonaEvalPersonaDetail`. `context` is the complete,
 * humanized, multi-line profile (far richer than the list `blurb`).
 */
export interface PersonaEvalPersonaDetail {
  id: string;
  name: string;
  source: string;
  context: string;
}

/**
 * `GET /api/persona-eval/personas?q=&limit=` payload. The catalog is domain-free
 * (searchable, not domain-filtered). `sutDescription` is returned only when an
 * optional `domain` query param is supplied, so it is optional here.
 */
export interface PersonaEvalPersonasResponse {
  personas: PersonaEvalPersona[];
  /** The system-under-test description, present only when `domain` was passed. */
  sutDescription?: string;
}

/** Query parameters accepted by `GET /api/persona-eval/personas`. */
export interface PersonaEvalPersonasParams {
  q?: string;
  limit?: number;
}

/**
 * A selectable goal/context prompt for a persona-eval run. Mirrors the backend
 * `GoalContext` schema (`GET /api/persona-eval/goal-contexts`).
 */
export interface GoalContext {
  id: string;
  label: string;
  description: string;
}

/** `GET /api/persona-eval/goal-contexts` payload. */
export interface GoalContextsResponse {
  goalContexts: GoalContext[];
}

/** Body for `POST /api/persona-eval`. */
export interface StartPersonaEvalBody {
  domain: Domain;
  personaId: string;
  maxTurns?: number;
  goalContextId?: string;
  /**
   * The OpenAI chat model driving BOTH the recommender and the user-simulator.
   * Omitted -> the backend falls back to its canonical config default.
   */
  engine?: Engine;
}

/**
 * Coarse-grained progress label the runner reports via `on_event` (e.g. which
 * agent is "thinking"). Free-form string on the wire; `null` between phases.
 */
export type PersonaEvalPhase = string | null;

/**
 * The evaluator's structured questionnaire. Mirrors
 * `persona_eval.types.Questionnaire.to_dict()` (camelCase wire shape).
 */
export interface PersonaEvalQuestionnaire {
  constraintSatisfaction: number;
  constraintRationale: string;
  preferenceSatisfaction: number;
  preferenceRationale: string;
  overallRating: number;
  ratingReason: string;
  askedUsefulClarifyingQuestions: boolean;
  clarifyingNotes: string;
}

/**
 * Objective per-run metrics. Mirrors `persona_eval.types.MetricScores.to_dict()`.
 * `turnsToRecommendation` is `null` when the agent never recommended.
 */
export interface PersonaEvalMetricScores {
  turnsToRecommendation: number | null;
  numTurns: number;
  recommendedItemCount: number;
}

/**
 * Live view of a persona-eval job. Mirrors `PersonaEvalProgress.to_view()` on
 * the backend. `turns` are full `TurnView`s (same shape the manual chat
 * renders), so the chat thread can be reused unchanged.
 * `questionnaire`/`metricScores` populate once `status === "done"`.
 */
export interface PersonaEvalJobView {
  jobId: string;
  domain: Domain;
  personaId: string;
  personaName: string;
  sutDescription: string;
  /** The goal-context the run was started with, if any. */
  goalContextId?: string | null;
  status: JobStatus;
  phase: PersonaEvalPhase;
  turns: TurnView[];
  questionnaire: PersonaEvalQuestionnaire | null;
  metricScores: PersonaEvalMetricScores | null;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Persisted persona-eval runs (durable artifacts)
// ---------------------------------------------------------------------------

/**
 * One entry in `GET /api/persona-eval/runs` — a newest-first summary of a
 * persisted run, built from the stored `<jobId>.json` artifact. Mirrors the
 * backend `PersonaEvalRunSummary`; fields beyond `id` may be absent on legacy
 * artifacts.
 */
export interface PersonaEvalRunSummary {
  id: string;
  createdAt?: string | null;
  domain?: Domain | null;
  personaName?: string | null;
  source?: string | null;
  goalContextId?: string | null;
  overallRating?: number | null;
  numTurns?: number | null;
}

/** `GET /api/persona-eval/runs` payload. */
export interface PersonaEvalRunsResponse {
  runs: PersonaEvalRunSummary[];
}

/**
 * The full stored result for one persona-eval run
 * (`GET /api/persona-eval/runs/{id}`). Mirrors the backend
 * `PersonaEvalResultView` (`persona_eval.types.PersonaEvalResult` plus the
 * top-level `id`/`createdAt` injected at persist time).
 */
export interface PersonaEvalResult {
  id: string;
  createdAt?: string | null;
  config: Record<string, unknown>;
  persona: Record<string, unknown>;
  sutDescription?: string | null;
  transcript: TurnView[];
  recommendedItemIds: Record<string, unknown>;
  questionnaire: PersonaEvalQuestionnaire | null;
  metricScores: PersonaEvalMetricScores | null;
}
