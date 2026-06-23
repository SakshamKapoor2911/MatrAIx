/**
 * Typed fetch client for the RecBot Studio API.
 *
 * One thin function per endpoint in the FastAPI contract (prefix `/api`).
 * In development, Vite proxies `/api` to the FastAPI app on port 8765
 * (see vite.config.ts); in production the SPA is served from the same origin,
 * so a relative base path works in both modes.
 *
 * All functions throw `ApiError` on a non-2xx response, carrying the HTTP
 * status and the server's error detail when available — React Query surfaces
 * these via its `error` state.
 */
import type {
  CatalogItem,
  CatalogSearchParams,
  CatalogSearchResponse,
  ConfigOptionsResponse,
  GoalContextsResponse,
  HealthResponse,
  JobView,
  PatchConfigResponse,
  PersonaEvalJobView,
  PersonaEvalPersonaDetail,
  PersonaEvalPersonasParams,
  PersonaEvalPersonasResponse,
  PersonaEvalResult,
  PersonaEvalRunsResponse,
  PreflightResponse,
  Session,
  SessionConfig,
  SessionSummary,
  StartPersonaEvalBody,
  SubmitTurnResponse,
} from "./types";

/** Base path for the API. Relative so it works behind the dev proxy and when bundled. */
export const API_BASE = "/api";

/** Error thrown for any non-2xx API response. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Extract a human-readable message from a FastAPI/pydantic error body. */
function messageFromBody(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      // pydantic validation errors: [{ loc, msg, type }, ...]
      const first = detail[0] as { msg?: unknown };
      if (first && typeof first.msg === "string") return first.msg;
    }
    if (detail != null) return JSON.stringify(detail);
  }
  return `Request failed with status ${status}`;
}

/** Core request helper: JSON in, typed JSON out, `ApiError` on failure. */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(init?.headers ?? {}),
      },
      ...init,
    });
  } catch (cause) {
    // Network-level failure (server down, CORS, offline).
    throw new ApiError(0, "Network request failed — is the API running on :8765?", cause);
  }

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, messageFromBody(res.status, body), body);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Build a query string from a params object, skipping null/undefined/empty. */
function qs(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const out = search.toString();
  return out ? `?${out}` : "";
}

// ---------------------------------------------------------------------------
// Health & preflight
// ---------------------------------------------------------------------------

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getPreflight(): Promise<PreflightResponse> {
  return request<PreflightResponse>("/preflight");
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

export function getConfigOptions(): Promise<ConfigOptionsResponse> {
  return request<ConfigOptionsResponse>("/config/options");
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

export function listSessions(): Promise<SessionSummary[]> {
  return request<SessionSummary[]>("/sessions");
}

export function getSession(id: string): Promise<Session> {
  return request<Session>(`/sessions/${encodeURIComponent(id)}`);
}

export function createSession(input?: {
  title?: string;
  config?: Partial<SessionConfig>;
}): Promise<Session> {
  return request<Session>("/sessions", {
    method: "POST",
    body: JSON.stringify(input ?? {}),
  });
}

export function patchSessionConfig(
  id: string,
  config: Partial<SessionConfig>,
): Promise<PatchConfigResponse> {
  return request<PatchConfigResponse>(`/sessions/${encodeURIComponent(id)}/config`, {
    method: "PATCH",
    body: JSON.stringify({ config }),
  });
}

/**
 * URL for the export endpoint (served with a `Content-Disposition: attachment`
 * header). Use as an `<a href>` or `window.location` target so the browser
 * handles the download.
 */
export function sessionExportUrl(id: string): string {
  return `${API_BASE}/sessions/${encodeURIComponent(id)}/export`;
}

// ---------------------------------------------------------------------------
// Turns & jobs (async)
// ---------------------------------------------------------------------------

/** Submit a turn; returns immediately with a `jobId` to poll. */
export function submitTurn(sessionId: string, message: string): Promise<SubmitTurnResponse> {
  return request<SubmitTurnResponse>(`/sessions/${encodeURIComponent(sessionId)}/turns`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

/** Poll a turn job for its current status / result. */
export function getJob(jobId: string): Promise<JobView> {
  return request<JobView>(`/jobs/${encodeURIComponent(jobId)}`);
}

// ---------------------------------------------------------------------------
// Catalog
// ---------------------------------------------------------------------------

export function searchCatalog(params: CatalogSearchParams = {}): Promise<CatalogSearchResponse> {
  const { q, genre, limit, domain } = params;
  return request<CatalogSearchResponse>(`/catalog/search${qs({ q, genre, limit, domain })}`);
}

export function getCatalogItem(itemId: string, domain?: string): Promise<CatalogItem> {
  return request<CatalogItem>(`/catalog/items/${encodeURIComponent(itemId)}${qs({ domain })}`);
}

// ---------------------------------------------------------------------------
// Persona Eval (persona-driven live evaluation)
// ---------------------------------------------------------------------------

/** Start a persona-eval run; returns immediately with a `jobId` to poll. */
export function startPersonaEval(body: StartPersonaEvalBody): Promise<{ jobId: string }> {
  return request<{ jobId: string }>("/persona-eval", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Poll a persona-eval job for its current (growing) state. */
export function getPersonaEvalJob(jobId: string): Promise<PersonaEvalJobView> {
  return request<PersonaEvalJobView>(`/persona-eval/jobs/${encodeURIComponent(jobId)}`);
}

/**
 * List the (domain-free) persona catalog, honoring an optional substring search
 * (`q`) and a result cap (`limit`). The catalog is searchable, not
 * domain-filtered.
 */
export function listPersonaEvalPersonas(
  params: PersonaEvalPersonasParams = {},
): Promise<PersonaEvalPersonasResponse> {
  const { q, limit } = params;
  return request<PersonaEvalPersonasResponse>(`/persona-eval/personas${qs({ q, limit })}`);
}

/** Fetch one persona's full humanized profile (the catalog "full persona" view). */
export function getPersonaEvalPersona(id: string): Promise<PersonaEvalPersonaDetail> {
  return request<PersonaEvalPersonaDetail>(`/persona-eval/personas/${encodeURIComponent(id)}`);
}

/** List the selectable goal/context prompts for a persona-eval run. */
export function listGoalContexts(): Promise<GoalContextsResponse> {
  return request<GoalContextsResponse>("/persona-eval/goal-contexts");
}

/** List persisted persona-eval runs (newest-first summaries). */
export function listPersonaEvalRuns(): Promise<PersonaEvalRunsResponse> {
  return request<PersonaEvalRunsResponse>("/persona-eval/runs");
}

/** Fetch the full stored result for one persisted persona-eval run (404 -> ApiError). */
export function getPersonaEvalRun(id: string): Promise<PersonaEvalResult> {
  return request<PersonaEvalResult>(`/persona-eval/runs/${encodeURIComponent(id)}`);
}

/**
 * Aggregate handle for ergonomic imports and easy mocking in tests/components:
 * `import { api } from "@/lib/api"; api.listSessions()`.
 */
export const api = {
  getHealth,
  getPreflight,
  getConfigOptions,
  listSessions,
  getSession,
  createSession,
  patchSessionConfig,
  sessionExportUrl,
  submitTurn,
  getJob,
  searchCatalog,
  getCatalogItem,
  startPersonaEval,
  getPersonaEvalJob,
  listPersonaEvalPersonas,
  getPersonaEvalPersona,
  listGoalContexts,
  listPersonaEvalRuns,
  getPersonaEvalRun,
} as const;
