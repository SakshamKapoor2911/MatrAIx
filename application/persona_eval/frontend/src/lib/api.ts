import type {
  AppWorldEvalJobView,
  AppWorldEvalTasksResponse,
  ConfigOptionsResponse,
  GoalContextsResponse,
  PersonaEvalJobView,
  PersonaEvalPersonasResponse,
  PersonaEvalResult,
  HarborJobDetail,
  HarborJobLaunchResponse,
  HarborJobsListResponse,
  HarborJobLiveResponse,
  HarborTrialEventsResponse,
  PersonaPoolCatalog,
  PersonaPoolCardsResponse,
  PersonaPoolPersonaDetail,
  PersonaPoolSampleResult,
  TaskDetail,
  PersonaCohortDetail,
  PersonaCohortSummary,
  PreflightResponse,
  ChatbotSidecarsResponse,
  StartChatbotSidecarResponse,
  Session,
  SessionConfig,
  SessionSummary,
  SurveyEvalJobView,
  SurveyInstrumentsResponse,
  SurveyHarborTasksResponse,
  WebEvalJobView,
  WebEvalTasksResponse,
  WebTrace,
  CuaEvalTasksResponse,
} from "./types";
import { PERSONA_BENCH_POOL } from "./types";

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
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : data;
    const message = typeof detail === "string" ? detail : response.statusText;
    throw new ApiError(response.status, message || "Request failed", detail);
  }
  return data as T;
}

function qs(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export const api = {
  getPreflight: () => request<PreflightResponse>("/api/preflight"),
  getChatbotSidecars: () => request<ChatbotSidecarsResponse>("/api/chatbot-sidecars"),
  startChatbotSidecar: (applicationId: string) =>
    request<StartChatbotSidecarResponse>(
      `/api/chatbot-sidecars/${encodeURIComponent(applicationId)}/start`,
      { method: "POST" },
    ),
  getConfigOptions: () => request<ConfigOptionsResponse>("/api/config/options"),

  listSessions: () => request<SessionSummary[]>("/api/sessions"),
  getSession: (id: string) => request<Session>(`/api/sessions/${encodeURIComponent(id)}`),
  createSession: (body?: { title?: string; config?: Partial<SessionConfig> }) =>
    request<Session>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
  patchSessionConfig: (id: string, config: Partial<SessionConfig>) =>
    request<{ session: Session; cacheInvalidated: boolean }>(
      `/api/sessions/${encodeURIComponent(id)}/config`,
      {
        method: "PATCH",
        body: JSON.stringify({ config }),
      },
    ),
  deleteSession: (id: string) =>
    request<{ deleted: string }>(`/api/sessions/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
  clearSessions: () => request<{ deleted: number }>("/api/sessions", { method: "DELETE" }),
  submitTurn: (id: string, message: string) =>
    request<{ jobId: string }>(`/api/sessions/${encodeURIComponent(id)}/turns`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  getTurnJob: (id: string) =>
    request<{ jobId: string; status: string; turn?: unknown; error?: string | null }>(
      `/api/jobs/${encodeURIComponent(id)}`,
    ),

  startPersonaEval: (body: {
    domain?: string;
    applicationId?: string;
    applicationContext?: string;
    personaId: string;
    maxTurns: number;
    goalContextId?: string | null;
    engine?: string | null;
    personaModel?: string | null;
  }) =>
    request<{ jobId: string }>("/api/persona-eval", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getPersonaEvalJob: (id: string) =>
    request<PersonaEvalJobView>(`/api/persona-eval/jobs/${encodeURIComponent(id)}`),

  listHarborJobs: () => request<HarborJobsListResponse>("/api/harbor/jobs"),
  deleteHarborJob: (jobName: string) =>
    request<{ deleted: boolean; jobName: string }>(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}`,
      { method: "DELETE" },
    ),
  getHarborJob: (jobName: string) =>
    request<HarborJobDetail>(`/api/harbor/jobs/${encodeURIComponent(jobName)}`),
  getHarborJobLive: (jobName: string) =>
    request<HarborJobLiveResponse>(`/api/harbor/jobs/${encodeURIComponent(jobName)}/live`),
  getHarborTrialDebrief: (jobName: string, trialName: string) =>
    request<PersonaEvalResult>(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}/trials/${encodeURIComponent(trialName)}/debrief`,
    ),
  getHarborTrialTrace: (jobName: string, trialName: string) =>
    request<{ trace: WebTrace }>(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}/trials/${encodeURIComponent(trialName)}/trace`,
    ),
  getHarborTrialEvents: (jobName: string, trialName: string, after = 0) =>
    request<HarborTrialEventsResponse>(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}/trials/${encodeURIComponent(trialName)}/events${qs({ after })}`,
    ),
  getHarborTrialInstruction: (jobName: string, trialName: string) =>
    request<{ title?: string | null; markdown: string }>(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}/trials/${encodeURIComponent(trialName)}/instruction`,
    ),
  launchHarborJob: (body: {
    taskPath: string;
    sampleSize?: number;
    seed?: number;
    personaPool?: string;
    personaIds?: string[];
    agentName?: string | null;
    personaModel?: string | null;
    nConcurrentTrials?: number;
    mode?: "auto" | "force_docker" | "smoke";
    jobName?: string | null;
    surveyInstrumentId?: string | null;
    chatDomain?: string | null;
    chatApplicationId?: string | null;
    chatApplicationContext?: string | null;
    chatGoalContextId?: string | null;
    chatMaxTurns?: number | null;
    personaSources?: string[] | null;
    personaFilters?: Record<string, string> | null;
    cohortId?: string | null;
  cuaSubmissionProfile?: string | null;
  cuaBackend?: string | null;
}) =>
    request<HarborJobLaunchResponse>("/api/harbor/jobs", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getPersonaPoolCatalog: (pool = PERSONA_BENCH_POOL) =>
    request<PersonaPoolCatalog>(
      `/api/persona-pool/catalog?${new URLSearchParams({ pool }).toString()}`,
    ),
  getPersonaPoolCards: (input?: { limit?: number; seed?: number; personaIds?: string[] }) =>
    request<PersonaPoolCardsResponse>(
      `/api/persona-pool/personas${qs({
        pool: PERSONA_BENCH_POOL,
        limit: input?.limit,
        seed: input?.seed,
        personaIds: input?.personaIds?.join(","),
      })}`,
    ),
  getPersonaPoolPersona: async (personaId: string, pool = PERSONA_BENCH_POOL) => {
    try {
      const byQuery = await request<PersonaPoolPersonaDetail>(
        `/api/persona-pool/personas${qs({
          pool,
          personaIds: personaId,
          detail: "true",
        })}`,
      );
      if (byQuery.profileMarkdown?.trim()) return byQuery;
    } catch {
      // Fall through to path-style endpoint on older backends.
    }
    return request<PersonaPoolPersonaDetail>(
      `/api/persona-pool/personas/${encodeURIComponent(personaId)}?${new URLSearchParams({ pool }).toString()}`,
    );
  },
  getTaskDetail: (taskPath: string) =>
    request<TaskDetail>(`/api/tasks/detail${qs({ taskPath })}`),
  samplePersonaPool: (body: {
    pool?: string;
    sampleSize?: number;
    seed?: number;
    sources?: string[];
    dimensionFilters?: Record<string, string | string[]>;
    stratifyFields?: string[];
    sampleSizePerValueGroup?: number;
  }) =>
    request<PersonaPoolSampleResult>("/api/persona-pool/sample", {
      method: "POST",
      body: JSON.stringify({ pool: PERSONA_BENCH_POOL, ...body }),
    }),

  listPersonaCohorts: () =>
    request<{ cohorts: PersonaCohortSummary[] }>("/api/persona-pool/cohorts"),
  getPersonaCohort: (cohortId: string) =>
    request<PersonaCohortDetail>(`/api/persona-pool/cohorts/${encodeURIComponent(cohortId)}`),
  savePersonaCohort: (body: {
    cohortId: string;
    name?: string;
    description?: string;
    pool?: string;
    kind?: "recipe" | "frozen";
    seed?: number;
    sampleSize?: number;
    sources?: string[];
    dimensionFilters?: Record<string, string>;
    personaIds?: string[];
  }) =>
    request<PersonaCohortDetail>("/api/persona-pool/cohorts", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  startSurveyEval: (body: {
    personaId: string;
    instrumentId: string;
    personaModel?: string | null;
  }) =>
    request<{ jobId: string }>("/api/survey-eval", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getSurveyEvalJob: (id: string) =>
    request<SurveyEvalJobView>(`/api/survey-eval/jobs/${encodeURIComponent(id)}`),

  startWebEval: (body: {
    personaId: string;
    taskId: string;
    personaModel?: string | null;
  }) =>
    request<{ jobId: string }>("/api/web-eval", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getWebEvalJob: (id: string) =>
    request<WebEvalJobView>(`/api/web-eval/jobs/${encodeURIComponent(id)}`),

  startAppWorldEval: (body: {
    personaId: string;
    taskId: string;
    personaModel?: string | null;
  }) =>
    request<{ jobId: string }>("/api/appworld-eval", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getAppWorldEvalJob: (id: string) =>
    request<AppWorldEvalJobView>(`/api/appworld-eval/jobs/${encodeURIComponent(id)}`),
};

export function sessionExportUrl(id: string): string {
  return `/api/sessions/${encodeURIComponent(id)}/export`;
}

export function listPersonaEvalPersonas(input?: {
  q?: string;
  limit?: number;
  domain?: string | null;
}): Promise<PersonaEvalPersonasResponse> {
  return request<PersonaEvalPersonasResponse>(
    `/api/persona-eval/personas${qs({
      q: input?.q,
      limit: input?.limit,
      domain: input?.domain,
    })}`,
  );
}

export function getPersonaEvalPersona(id: string): Promise<PersonaEvalPersonasResponse["personas"][number]> {
  return request<PersonaEvalPersonasResponse["personas"][number]>(
    `/api/persona-eval/personas/${encodeURIComponent(id)}`,
  );
}

export function listGoalContexts(): Promise<GoalContextsResponse> {
  return request<GoalContextsResponse>("/api/persona-eval/goal-contexts");
}

export function listSurveyInstruments(): Promise<SurveyInstrumentsResponse> {
  return request<SurveyInstrumentsResponse>("/api/survey-eval/instruments");
}

export function listSurveyHarborTasks(): Promise<SurveyHarborTasksResponse> {
  return request<SurveyHarborTasksResponse>("/api/survey-eval/harbor-tasks");
}

export function listWebEvalTasks(): Promise<WebEvalTasksResponse> {
  return request<WebEvalTasksResponse>("/api/web-eval/tasks");
}

export function listCuaEvalTasks(): Promise<CuaEvalTasksResponse> {
  return request<CuaEvalTasksResponse>("/api/cua-eval/tasks");
}

export function listAppWorldEvalTasks(): Promise<AppWorldEvalTasksResponse> {
  return request<AppWorldEvalTasksResponse>("/api/appworld-eval/tasks");
}
