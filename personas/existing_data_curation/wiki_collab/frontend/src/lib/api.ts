/**
 * Typed fetch client for the Persona Curation Cockpit backend (demo_app.py).
 *
 * One thin function per endpoint. In dev, Vite proxies `/api` and `/files` to
 * the http.server on :8765; in production demo_app.py serves the built SPA from
 * the same origin, so a relative base works in both modes.
 *
 * All functions throw `ApiError` on a non-2xx response (and on the demo's
 * `{"error": ...}` 400 bodies), carrying the status + server detail so React
 * Query surfaces them in-pane.
 */
import type {
  AppState,
  AssignmentRequest,
  AssignmentResponse,
  AuditResponse,
  DimensionCatalog,
  FullPageResult,
  MergeResponse,
  ReturnResponse,
  RunRequest,
  RunResponse,
} from "./types";

export const API_BASE = "/api";

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
    throw new ApiError(0, "Network request failed — is demo_app.py running on :8765?", cause);
  }

  let body: unknown = null;
  if (res.status !== 204) {
    try {
      body = await res.json();
    } catch {
      /* non-JSON body */
    }
  }

  // The demo returns 400 with `{"error": "..."}` for handled failures.
  if (!res.ok || (body && typeof body === "object" && "error" in body)) {
    const message =
      body && typeof body === "object" && "error" in body
        ? String((body as { error: unknown }).error)
        : `Request failed with status ${res.status}`;
    throw new ApiError(res.status || 400, message, body);
  }

  return body as T;
}

function post<T>(path: string, payload?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}

// --- reads ---------------------------------------------------------------

export function getState(): Promise<AppState> {
  return request<AppState>("/state");
}

export function getDimensions(): Promise<DimensionCatalog> {
  return request<DimensionCatalog>("/dimensions");
}

export function getFullPage(query: string): Promise<FullPageResult> {
  return post<FullPageResult>("/full-page", { query });
}

// --- workflow actions ----------------------------------------------------

export function createAssignment(body: AssignmentRequest): Promise<AssignmentResponse> {
  return post<AssignmentResponse>("/assignment", body);
}

export function runAssignment(body: RunRequest): Promise<RunResponse> {
  return post<RunResponse>("/run", body);
}

export function returnArchive(archive?: string): Promise<ReturnResponse> {
  return post<ReturnResponse>("/return", archive ? { archive } : {});
}

export function auditArchives(): Promise<AuditResponse> {
  return post<AuditResponse>("/audit", {});
}

export function mergeArchives(): Promise<MergeResponse> {
  return post<MergeResponse>("/merge", {});
}

export function resetOutputs(): Promise<{ ok: boolean }> {
  return post<{ ok: boolean }>("/reset", {});
}

/** Download URL for a /files artifact path (served as an attachment). */
export function fileUrl(rel: string): string {
  return `/files/${rel.replace(/^\/+/, "")}`;
}

export const api = {
  getState,
  getDimensions,
  getFullPage,
  createAssignment,
  runAssignment,
  returnArchive,
  auditArchives,
  mergeArchives,
  resetOutputs,
  fileUrl,
} as const;
