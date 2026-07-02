export type Domain = "movie" | "beauty_product" | "game" | string;
export type ApplicationId = "recai" | "finance_openbb" | "medical_assistant" | string;
export type Engine = string;
export type PersonaModel = string;

export interface ConfigOptionValue {
  value: string;
  label: string;
  description?: string;
}

export interface ConfigKnob {
  key: string;
  label: string;
  description?: string;
  options: ConfigOptionValue[];
  rebuildsAgent?: boolean;
}

export interface ConfigEnvironment {
  runtime: string;
  personaAgent: string;
  personaModel: string;
  applicationApi: string;
  scorer: string;
  cache: string;
  ranker: string;
  resources: string;
  agent: string;
  promptOwnership?: Record<string, string>;
}

export interface ConfigOptionsResponse {
  knobs: ConfigKnob[];
  defaults: SessionConfig;
  environment: ConfigEnvironment;
}

export interface PreflightCheck {
  name: string;
  ok: boolean;
  detail: string;
  group?: string | null;
  optional?: boolean;
  applicationId?: string | null;
}

export interface PreflightResponse {
  ready: boolean;
  checks: PreflightCheck[];
}

export interface ChatbotSidecarStatus {
  applicationId: string;
  ok: boolean;
  healthUrl: string;
  canStart: boolean;
  detail: string;
}

export interface ChatbotSidecarsResponse {
  sidecars: ChatbotSidecarStatus[];
}

export interface StartChatbotSidecarResponse {
  sidecar: ChatbotSidecarStatus;
  started: boolean;
}

export interface RecommendedItem {
  itemId: string;
  rank?: number | null;
  title?: string | null;
  meta?: string | null;
  score?: number | null;
}

export interface PlanStep {
  tool: string;
  detail?: string | null;
  status?: string;
}

export interface TurnView {
  turnId?: string | null;
  conversationId?: string | null;
  backend?: string | null;
  userMessage: string;
  assistantMessage: string;
  plan?: PlanStep[];
  recommendedItems?: RecommendedItem[];
  nativeRaw?: string | null;
  rawToolOutputs?: unknown;
  durationSeconds?: number | null;
}

export interface SessionConfig {
  engine?: string;
  rankerMode?: string;
  resourceMode?: string;
  domain?: Domain;
  botType?: string;
  applicationId?: ApplicationId;
  applicationContext?: string;
  [key: string]: unknown;
}

export interface Session {
  id: string;
  title: string;
  config: SessionConfig;
  messages: { role: string; content: string }[];
  turns: TurnView[];
  createdAt: string;
}

export interface SessionSummary {
  id: string;
  title: string;
  config: SessionConfig;
  turnCount: number;
  messageCount: number;
  createdAt?: string;
}

export interface PersonaEvalPersona {
  id: string;
  name: string;
  source: string;
  blurb?: string;
  context?: string;
}

export interface PersonaEvalPersonasResponse {
  personas: PersonaEvalPersona[];
  sutDescription?: string | null;
}

export interface GoalContext {
  id: string;
  label: string;
  description: string;
}

export interface GoalContextsResponse {
  goalContexts: GoalContext[];
}

export interface PersonaEvalPrompts {
  personaPrompt?: string;
  harborPrompt?: string;
  taskPrompt?: string;
  scorerPrompt?: string;
  [key: string]: string | undefined;
}

export interface PersonaEvalQuestionnaire {
  overallRating: number;
  ratingReason: string;
  constraintSatisfaction: number;
  constraintRationale: string;
  preferenceSatisfaction: number;
  preferenceRationale: string;
  askedUsefulClarifyingQuestions: boolean;
  clarifyingNotes: string;
  goalAchieved?: boolean | null;
  satisfaction?: number | null;
  frustration?: number | null;
  trust?: number | null;
  easeOfUse?: number | null;
  comments?: string | null;
  [key: string]: string | number | boolean | null | undefined;
}

export interface PersonaEvalMetricScores {
  numTurns: number;
  durationSeconds?: number | null;
  turnsToRecommendation: number | null;
  recommendedItemCount: number;
  mentionedItemCount?: number | null;
  catalogCoverage?: number | null;
  [key: string]: string | number | boolean | null | undefined;
}

export interface HarborDraftTurn {
  turnIndex?: number;
  userMessage?: string;
  assistantMessage?: string;
  recommendedItems?: RecommendedItem[];
  durationSeconds?: number | null;
}

export interface PersonaEvalJobView {
  jobId: string;
  domain: string;
  applicationId?: string | null;
  applicationContext?: string | null;
  personaId: string;
  personaName: string;
  sutDescription: string;
  goalContextId?: string | null;
  status: string;
  phase?: string | null;
  turns: TurnView[];
  draftTurn?: HarborDraftTurn | null;
  questionnaire?: PersonaEvalQuestionnaire | null;
  metricScores?: PersonaEvalMetricScores | null;
  prompts?: PersonaEvalPrompts | null;
  error?: string | null;
}

export interface PersonaEvalResult {
  id: string;
  createdAt?: string | null;
  config: Record<string, unknown>;
  persona: Record<string, unknown>;
  sutDescription?: string | null;
  transcript: TurnView[];
  recommendedItemIds: Record<string, unknown>;
  questionnaire?: PersonaEvalQuestionnaire | null;
  metricScores?: PersonaEvalMetricScores | null;
  prompts?: PersonaEvalPrompts | null;
  applicationType?: string | null;
  [key: string]: unknown;
}

export interface SurveyQuestion {
  id: string;
  prompt: string;
  type: string;
  options: string[];
  minValue?: number | null;
  maxValue?: number | null;
  construct?: string | null;
  required?: boolean;
}

export interface SurveyInstrument {
  id: string;
  title: string;
  description?: string;
  questions: SurveyQuestion[];
}

export interface SurveyInstrumentsResponse {
  instruments: SurveyInstrument[];
}

export interface SurveyHarborTask {
  id: string;
  title: string;
  description: string;
  taskPath: string;
  instrumentId: string;
  profileMarkdown?: string;
  surveyKind?: "example" | "contributing";
}

export interface SurveyHarborTasksResponse {
  tasks: SurveyHarborTask[];
}

export interface SurveyAnswer {
  questionId: string;
  value: string | number | boolean | string[] | null;
  rationale?: string | null;
  confidence?: number | null;
}

export interface SurveyTrajectoryEvent {
  timestamp?: string | null;
  actor: string;
  action: string;
  context?: Record<string, unknown>;
  outcome?: Record<string, unknown>;
}

/** Harbor test.sh verifier outcome from reward.txt (+ optional stdout). */
export interface VerifierSummary {
  passed: boolean;
  reward: number;
  detail?: string | null;
}

export interface SurveyResult {
  instrument: { id: string; title: string; questions: SurveyQuestion[] };
  answers: SurveyAnswer[];
  trajectory: SurveyTrajectoryEvent[];
  completion: {
    numAnswered: number;
    numQuestions: number;
    answered: number;
    total: number;
    valid: boolean;
    meanLikert?: number | null;
    freeTextCount?: number | null;
  };
  createdAt?: string | null;
  prompts?: PersonaEvalPrompts | null;
}

export interface SurveyEvalJobView {
  jobId: string;
  applicationType: "survey";
  taskId: string;
  instrumentId: string;
  instrumentTitle: string;
  personaId: string;
  personaName: string;
  status: string;
  phase?: string | null;
  surveyResult?: SurveyResult | null;
  instructionMarkdown?: string | null;
  verifier?: VerifierSummary | null;
  prompts?: PersonaEvalPrompts | null;
  error?: string | null;
}

export interface WebEvalTask {
  id: string;
  title: string;
  siteName: string;
  siteUrl: string;
  description: string;
  taskPath?: string;
  outputArtifact: string;
  submissionProfile: string;
  profileMarkdown?: string;
}

export interface WebEvalTasksResponse {
  tasks: WebEvalTask[];
}

export interface WebAction {
  name: string;
  arguments?: Record<string, unknown>;
}

export interface WebTraceEvent {
  step: number;
  source: string;
  message: string;
  actions: WebAction[];
  screenshotUrl?: string | null;
  screenshotFile?: string | null;
}

export interface WebTrace {
  events: WebTraceEvent[];
  raw?: Record<string, unknown>;
}

export interface WebResult {
  selectedProductId: string;
  selectedProductName: string;
  needSatisfaction: number;
  easeOfUse: number;
  informationQuality?: number | null;
  overallExperienceRating: number;
  overallQuality?: number | null;
  valid: boolean;
  reason: string;
  createdAt?: string | null;
}

export interface WebEvalJobView {
  jobId: string;
  applicationType: "web";
  taskId: string;
  taskTitle: string;
  siteName: string;
  siteUrl: string;
  personaId: string;
  personaName: string;
  status: string;
  phase?: string | null;
  webResult?: WebResult | null;
  trace?: WebTrace | null;
  verifier?: VerifierSummary | null;
  prompts?: PersonaEvalPrompts | null;
  error?: string | null;
}

export interface AppWorldEvalTask {
  id: string;
  title: string;
  appName: string;
  description?: string;
  outputArtifact?: string;
  submissionProfile?: string;
}

export interface AppWorldEvalTasksResponse {
  tasks: AppWorldEvalTask[];
}

export interface AppWorldResult {
  taskId: string;
  success: boolean;
  score: number;
  outcome: string;
  reason: string;
  createdAt?: string | null;
}

export type AppWorldTraceEvent = WebTraceEvent;
export type AppWorldTrace = WebTrace;

export interface AppWorldEvalJobView {
  jobId: string;
  applicationType: "appworld";
  taskId: string;
  taskTitle: string;
  appName: string;
  personaId: string;
  personaName: string;
  status: string;
  phase?: string | null;
  appworldResult?: AppWorldResult | null;
  trace?: AppWorldTrace | null;
  prompts?: PersonaEvalPrompts | null;
  error?: string | null;
}

export interface CuaEvalTask {
  id: string;
  title: string;
  platform: string;
  description?: string;
  taskPath: string;
  outputArtifact?: string;
  cuaSubmissionProfile?: string | null;
  environmentLabel?: string;
  /** Harbor persona-computer-1 backend: docker | macos | ios (use.computer). */
  cuaBackend?: string;
  profileMarkdown?: string;
}

export interface CuaEvalTasksResponse {
  tasks: CuaEvalTask[];
}

export interface CuaResult {
  success: boolean;
  score: number;
  artifactName?: string | null;
  artifact?: Record<string, unknown> | null;
  createdAt?: string | null;
}

export interface CuaEvalJobView {
  jobId: string;
  applicationType: "cua";
  taskId: string;
  taskTitle: string;
  platform: string;
  personaId: string;
  personaName: string;
  status: string;
  phase?: string | null;
  cuaResult?: CuaResult | null;
  trace?: WebTrace | null;
  verifier?: VerifierSummary | null;
  prompts?: PersonaEvalPrompts | null;
  error?: string | null;
}

export type HarborJobListStatus = "running" | "success" | "failed";

export interface HarborJobSummary {
  jobName: string;
  trialCount: number;
  completedTrials?: number;
  startedAt?: string | null;
  updatedAt?: string | null;
  finishedAt?: string | null;
  jobResult?: Record<string, unknown> | null;
  status?: HarborJobListStatus;
  failedTrials?: number;
  launchStatus?: string | null;
}

export interface HarborJobsListResponse {
  jobs: HarborJobSummary[];
}

export interface HarborTrialView {
  trialName: string;
  completed?: boolean;
  succeeded?: boolean;
  error?: string | null;
  result?: Record<string, unknown> | null;
}

export interface HarborTrialEvent {
  type: string;
  phase?: string;
  turn?: TurnView;
  prompts?: PersonaEvalPrompts;
  [key: string]: unknown;
}

export interface HarborTrialEventsResponse {
  events: HarborTrialEvent[];
  offset: number;
}

export interface HarborJobLiveTrial {
  trialName: string;
  personaId?: string | null;
  personaName?: string | null;
  completed?: boolean;
  succeeded?: boolean | null;
  error?: string | null;
  phase?: string | null;
  stage?: string | null;
  hasInstruction?: boolean;
}

export interface HarborJobLiveResponse {
  jobName: string;
  launchStatus?: string | null;
  trialCount: number;
  completedTrials: number;
  trials: HarborJobLiveTrial[];
}

export interface HarborLaunchView {
  status?: string;
  configPath?: string | null;
  error?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  exitCode?: number | null;
}

export interface HarborJobDetail {
  jobName: string;
  jobsDir?: string | null;
  config?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  trials: HarborTrialView[];
  launch?: HarborLaunchView | null;
}

export interface HarborJobLaunchResponse {
  jobName: string;
  configPath?: string | null;
  jobsDir?: string | null;
  agentName?: string | null;
  taskType?: string | null;
  trialProfile?: string | null;
  mode?: string | null;
}

export interface PersonaPoolDimensionOption {
  id: string;
  values: string[];
}

export interface PersonaPoolDimensionGroup {
  id: string;
  label: string;
  dimensionIds: string[];
  dimensions: PersonaPoolDimensionOption[];
}

export interface PersonaPoolCatalog {
  pool: string;
  count: number;
  smokePersonaId?: string | null;
  sourceCounts?: Record<string, number>;
  schemaVersion?: string | null;
  dimensionCategoriesPath?: string | null;
  dimensionCategories: {
    schemaVersion?: string | null;
    personaSources?: string[];
    devProfile?: {
      dimensionCount?: number | null;
      groups?: PersonaPoolDimensionGroup[];
    };
  };
}

export interface PersonaPoolSampleResult {
  pool: string;
  matchedCount: number;
  sampleSize: number;
  seed: number;
  personaIds: string[];
  personas: Array<{
    personaId: string;
    source?: string;
    path?: string;
    name?: string;
    dimensions?: Record<string, string>;
  }>;
  stratifyFields?: string[];
}

export interface PersonaPoolPersonaCard {
  personaId: string;
  name?: string;
  source?: string;
  path?: string;
  dimensions: Record<string, string>;
}

export interface PersonaPoolCardsResponse {
  pool: string;
  personas: PersonaPoolPersonaCard[];
}

export interface PersonaPoolPersonaDetail extends PersonaPoolPersonaCard {
  pool: string;
  yaml?: string;
  profileMarkdown?: string;
  dimensions: Record<string, string>;
}

export interface TaskDetail {
  taskPath: string;
  title?: string;
  description?: string;
  metaType?: string;
  taskName?: string;
  instructionMarkdown?: string;
  profileMarkdown?: string;
}

/** Unified persona pool for all PersonaEval cockpit sampling. */
export const PERSONA_BENCH_POOL = "persona/datasets/bench-dev-sample";

export interface PersonaCohortSummary {
  cohortId: string;
  name: string;
  kind: "recipe" | "frozen" | string;
  pool: string;
  sampleSize: number;
  matchedCount: number;
  personaCount: number;
  createdAt?: string | null;
}

export interface PersonaCohortDetail extends PersonaCohortSummary {
  description?: string;
  seed: number;
  sources: string[];
  dimensionFilters: Record<string, string>;
  personaIds: string[];
  personas: Array<{ personaId: string; source?: string; path?: string }>;
}

/** Default Harbor task paths for cockpit launch (one trial per persona). */
export const HARBOR_TASK_PATHS = {
  chatbot: "application/tasks/recommender-agent_chat_api",
  survey: "application/tasks/persona-survey",
  web: "application/tasks/example-web-playwright_books-interest",
  cuaLinux: "application/tasks/example-computer-use-linux_notification-preferences",
  cuaWeb: "application/tasks/example-web-cua_books-interest",
} as const;

export const HARBOR_CHAT_TASKS: Record<string, string> = {
  recai: HARBOR_TASK_PATHS.chatbot,
  finance_openbb: "application/tasks/example-chat-mcp_support_chatbot",
  medical_assistant: "application/tasks/example-chat-api_support_chatbot",
};
