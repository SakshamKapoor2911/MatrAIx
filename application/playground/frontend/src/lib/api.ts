import type {
  ConfigOptionsResponse,
  PlaygroundPersonasResponse,
  PlaygroundResult,
  HarborJobAggregation,
  HarborJobDetail,
  HarborJobLaunchResponse,
  HarborJobsListResponse,
  HarborJobLiveResponse,
  HarborJobStatusResponse,
  HarborTrialEventsResponse,
  PersonaPoolCatalog,
  PersonaPoolCardsResponse,
  PersonaPoolPersonaDetail,
  PersonaPoolSampleResult,
  TaskDetail,
  TaskPersonaStrategy,
  PersonaCohortDetail,
  PersonaCohortSummary,
  PreflightResponse,
  ChatbotSidecarsResponse,
  StartChatbotSidecarResponse,
  SurveyInstrumentsResponse,
  SurveyHarborTasksResponse,
  ChatbotEvalTasksResponse,
  WebEvalTasksResponse,
  WebTrace,
  OsAppEvalTasksResponse,
} from "./types";
import { PERSONA_BENCH_POOL } from "./types";
import { normalizePersonaPoolName } from "./personaDisplay";

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

async function downloadFile(path: string, fallbackFilename: string): Promise<void> {
  const response = await fetch(path);
  if (!response.ok) {
    let message = response.statusText || "Download failed";
    try {
      const data = await response.json();
      if (data && typeof data === "object" && "detail" in data && typeof data.detail === "string") {
        message = data.detail;
      }
    } catch {
      /* ignore */
    }
    throw new ApiError(response.status, message);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = /filename="?([^";]+)"?/i.exec(disposition);
  const filename = match?.[1]?.trim() || fallbackFilename;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
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

function normalizePersonaPoolCardsResponse(
  response: PersonaPoolCardsResponse,
): PersonaPoolCardsResponse {
  return {
    ...response,
    personas: response.personas.map((persona) => normalizePersonaPoolName(persona)),
  };
}

function normalizePersonaPoolDetail(
  response: PersonaPoolPersonaDetail,
): PersonaPoolPersonaDetail {
  return normalizePersonaPoolName(response);
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
  listChatbotEvalTasks: () => request<ChatbotEvalTasksResponse>("/api/chatbot-eval/tasks"),

  listHarborJobs: () => request<HarborJobsListResponse>("/api/harbor/jobs"),
  deleteHarborJob: (jobName: string) =>
    request<{ deleted: boolean; jobName: string }>(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}`,
      { method: "DELETE" },
    ),
  getHarborJob: (jobName: string) =>
    request<HarborJobDetail>(`/api/harbor/jobs/${encodeURIComponent(jobName)}`),
  retryHarborJobFailed: (jobName: string) =>
    request<{ jobName: string; retried: number }>(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}/retry-failed`,
      { method: "POST" },
    ),
  getHarborJobAggregation: (jobName: string) =>
    request<HarborJobAggregation>(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}/aggregation`,
    ),
  downloadHarborJobReportPdf: (jobName: string) =>
    downloadFile(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}/report.pdf`,
      `${jobName}-batch-report.pdf`,
    ),
  getHarborJobLive: (jobName: string) =>
    request<HarborJobLiveResponse>(`/api/harbor/jobs/${encodeURIComponent(jobName)}/live`),
  getHarborJobStatus: (jobName: string, since = 0) =>
    request<HarborJobStatusResponse>(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}/status${qs({ since })}`,
    ),
  getHarborTrialDebrief: (jobName: string, trialName: string) =>
    request<PlaygroundResult>(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}/trials/${encodeURIComponent(trialName)}/debrief`,
    ),
  downloadHarborTrialReportPdf: (jobName: string, trialName: string) =>
    downloadFile(
      `/api/harbor/jobs/${encodeURIComponent(jobName)}/trials/${encodeURIComponent(trialName)}/report.pdf`,
      `${jobName}-${trialName}-trial-report.pdf`,
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
    request<{
      title?: string | null;
      markdown: string;
      instructionMarkdown?: string | null;
      contextMarkdown?: string | null;
      questionnaireMarkdown?: string | null;
      outputSchemaMarkdown?: string | null;
      selfReportMarkdown?: string | null;
    }>(
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
    plane?: "harbor" | "remote";
    jobName?: string | null;
    chatDomain?: string | null;
    chatApplicationId?: string | null;
    chatApplicationContext?: string | null;
    chatMaxTurns?: number | null;
    personaSources?: string[] | null;
    personaFilters?: Record<string, string> | null;
    cohortId?: string | null;
    osAppSubmissionProfile?: string | null;
    osAppBackend?: string | null;
  }) =>
    request<HarborJobLaunchResponse>("/api/harbor/jobs", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getPersonaPoolCatalog: (pool = PERSONA_BENCH_POOL) =>
    request<PersonaPoolCatalog>(
      `/api/persona-pool/catalog?${new URLSearchParams({ pool }).toString()}`,
    ),
  getPersonaPoolCards: async (input?: {
    limit?: number;
    offset?: number;
    seed?: number;
    personaIds?: string[];
    all?: boolean;
  }) =>
    normalizePersonaPoolCardsResponse(
      await request<PersonaPoolCardsResponse>(
        `/api/persona-pool/personas${qs({
          pool: PERSONA_BENCH_POOL,
          limit: input?.limit,
          offset: input?.offset,
          seed: input?.seed,
          personaIds: input?.personaIds?.join(","),
          all: input?.all ? "true" : undefined,
        })}`,
      ),
    ),
  listAllPersonaPoolCards: async (pageSize = 50) => {
    const personas: PersonaPoolCardsResponse["personas"] = [];
    let pool = PERSONA_BENCH_POOL;
    let offset = 0;
    for (;;) {
      const page = await request<PersonaPoolCardsResponse>(
        `/api/persona-pool/personas${qs({
          pool: PERSONA_BENCH_POOL,
          all: "true",
          limit: pageSize,
          offset,
        })}`,
      );
      pool = page.pool;
      if (
        offset > 0 &&
        page.personas.length > 0 &&
        personas.some((item) => item.personaId === page.personas[0]?.personaId)
      ) {
        break;
      }
      personas.push(...page.personas);
      if (page.personas.length < pageSize) break;
      offset += pageSize;
      if (offset > 10_000) break;
    }
    return normalizePersonaPoolCardsResponse({ pool, personas });
  },
  getPersonaPoolPersona: async (personaId: string, pool = PERSONA_BENCH_POOL) => {
    try {
      const byQuery = normalizePersonaPoolDetail(
        await request<PersonaPoolPersonaDetail>(
          `/api/persona-pool/personas${qs({
            pool,
            personaIds: personaId,
            detail: "true",
          })}`,
        ),
      );
      if (byQuery.profileMarkdown?.trim()) return byQuery;
    } catch {
      // Fall through to path-style endpoint on older backends.
    }
    return normalizePersonaPoolDetail(
      await request<PersonaPoolPersonaDetail>(
        `/api/persona-pool/personas/${encodeURIComponent(personaId)}?${new URLSearchParams({ pool }).toString()}`,
      ),
    );
  },
  getTaskDetail: (taskPath: string) =>
    request<TaskDetail>(`/api/tasks/detail${qs({ taskPath })}`),
  getTaskPersonaStrategy: (taskPath: string) =>
    request<{ personaStrategy: TaskPersonaStrategy | null }>(
      `/api/tasks/persona-strategy${qs({ taskPath })}`,
    ),
  samplePersonaPool: (body: {
    pool?: string;
    sampleSize?: number;
    seed?: number;
    sources?: string[];
    dimensionFilters?: Record<string, string | string[]>;
    stratifyFields?: string[];
    sampleSizePerValueGroup?: number;
    taskPath?: string;
    autoEnsureStrategyPool?: boolean;
  }) =>
    request<PersonaPoolSampleResult>("/api/persona-pool/sample", {
      method: "POST",
      body: JSON.stringify({
        pool: PERSONA_BENCH_POOL,
        autoEnsureStrategyPool: true,
        ...body,
      }),
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
};

export function listPlaygroundPersonas(input?: {
  q?: string;
  limit?: number;
  domain?: string | null;
}): Promise<PlaygroundPersonasResponse> {
  return request<PlaygroundPersonasResponse>(
    `/api/playground/personas${qs({
      q: input?.q,
      limit: input?.limit,
      domain: input?.domain,
    })}`,
  );
}

export function getPlaygroundPersona(id: string): Promise<PlaygroundPersonasResponse["personas"][number]> {
  return request<PlaygroundPersonasResponse["personas"][number]>(
    `/api/playground/personas/${encodeURIComponent(id)}`,
  );
}

export function listSurveyInstruments(): Promise<SurveyInstrumentsResponse> {
  return request<SurveyInstrumentsResponse>("/api/survey-eval/instruments");
}

export function listSurveyHarborTasks(): Promise<SurveyHarborTasksResponse> {
  return request<SurveyHarborTasksResponse>("/api/survey-eval/harbor-tasks");
}

export function listChatbotEvalTasks(): Promise<ChatbotEvalTasksResponse> {
  return request<ChatbotEvalTasksResponse>("/api/chatbot-eval/tasks");
}

export function listWebEvalTasks(): Promise<WebEvalTasksResponse> {
  return request<WebEvalTasksResponse>("/api/web-eval/tasks");
}

export function listOsAppEvalTasks(): Promise<OsAppEvalTasksResponse> {
  return request<OsAppEvalTasksResponse>("/api/os-app-eval/tasks");
}

export function harborTrialLiveScreenshotUrl(jobName: string, trialName: string): string {
  return `/api/harbor/jobs/${encodeURIComponent(jobName)}/trials/${encodeURIComponent(trialName)}/live-screenshot`;
}
