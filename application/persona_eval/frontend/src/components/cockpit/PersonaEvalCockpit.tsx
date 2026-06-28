/**
 * PersonaEvalCockpit: the PersonaEval chatbot surface (ports the PersonaEval
 * `app-redesign-v3.html` cockpit + liverun screens).
 *
 * Two flows off one shared state:
 *   - IDLE  (`data-view="cockpit"`) shows a centered "Configure a simulation" setup
 *     form: header + app-type switch, a compact Pipeline strip, then a 12-col
 *     grid (LEFT 8: application cards · run-configuration knobs · target persona;
 *     RIGHT 4: the read-only runtime panel · the glowing Run-eval CTA · a hint).
 *   - RUNNING/DONE (`data-view="liverun"`) shows the live-run layout: the stateful
 *     Pipeline strip, the Trajectory thread (persona/app bubbles with items +
 *     tool-plan fold), the right Inspector tabs (Evaluation / Persona / Prompts),
 *     and a bottom status bar.
 *
 * It owns all cross-component state (selected persona, run knobs, the run via
 * `usePersonaEval`, inspector tab, open tool-plan folds, focused turn) and the
 * keyboard shortcuts (R run · J/K move turns · 1/2/3 inspector tab · E expand
 * folds). Data is honest: real personas / goal-contexts / config / run shape
 * (real per-turn latency; no tokens or cost, which aren't tracked).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { PersonaCatalog } from "./PersonaCatalog";
import { RunHeader } from "./RunHeader";
import { RunConfigBar } from "./RunConfigBar";
import { ComponentPipeline } from "./ComponentPipeline";
import { EnvironmentPanel } from "./EnvironmentPopover";
import { Trajectory } from "./Trajectory";
import { InspectorTabs, type InspectorTab } from "./InspectorTabs";
import { Scorecard } from "./Scorecard";
import { PersonaPanel } from "./PersonaPanel";
import { PersonaDrawer } from "./PersonaDrawer";
import { PromptPanel } from "./PromptPanel";
import { SurveyEvalCockpit } from "./SurveyEvalCockpit";
import { WebEvalCockpit } from "./WebEvalCockpit";
import { type PersonaEvalTaskType } from "./TaskTypeSwitch";
import { FOCUS_RING, Sym, personaCodename, personaDescriptiveTitle } from "./cockpitShared";
import { fmtDomain } from "../runsShared";
import { listGoalContexts } from "@/lib/api";
import { usePersonaEval, type PersonaEvalRunPhase } from "@/lib/usePersonaEval";
import type {
  ApplicationId,
  ConfigOptionsResponse,
  ConfigOptionValue,
  Domain,
  Engine,
  GoalContext,
  GoalContextsResponse,
  PersonaModel,
  PersonaEvalJobView,
  PersonaEvalPersona,
} from "@/lib/types";

/** Per-app display name + icon (presentational; the data layer is app-agnostic). */
const APP_NAME: Record<string, string> = {
  recai: "RecAI",
  finance_openbb: "OpenBB",
  medical_assistant: "Medical Assistant",
};
const APP_ICON: Record<string, string> = {
  recai: "recommend",
  finance_openbb: "show_chart",
  medical_assistant: "stethoscope",
};

/** Map the job's coarse phase into a single "what's happening now" line. */
function liveStatusLine(
  job: PersonaEvalJobView | null,
  phase: PersonaEvalRunPhase,
  isRunning: boolean,
): string | null {
  if (phase === "building") return "Starting the app. The first reply can take up to a minute.";
  if (!isRunning) return null;
  const raw = (job?.phase ?? "").toLowerCase();
  if (raw.includes("persona") || raw.includes("user") || raw.includes("simulat")) return "The simulated user is typing…";
  if (raw.includes("chatbot") || raw.includes("application") || raw.includes("agent") || raw.includes("recai") || raw.includes("turn"))
    return "The app is thinking…";
  if (raw.includes("eval")) return "Scoring how it went…";
  if (job?.phase) return `${job.phase}…`;
  return "Running the PersonaEval…";
}

/** True when focus is in a text input / textarea / select / contenteditable. */
function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
}

/**
 * A frozen copy of the persona + run controls captured the moment a run reaches
 * `done`. The export is built from this (never the live controls), so changing
 * a knob after a run finishes cannot mislabel the completed transcript.
 */
interface ExportSnapshot {
  persona: { id: string; name: string; source: string } | null;
  config: {
    applicationId: ApplicationId;
    applicationContext: string;
    domain?: Domain;
    engine: string;
    personaModel: string;
    goalContextId: string | null;
    maxTurns: number;
  };
}

export interface PersonaEvalCockpitProps {
  /** Config metadata (knobs + defaults + environment) from the app. */
  options: ConfigOptionsResponse | null;
  /** Navigate to the Runs surface. */
  onOpenRuns: () => void;
  /** Report the active run domain up (so the shared catalog drawer can match it). */
  onDomainChange?: (domain: Domain) => void;
  /** Report the honest footer context up (task type + active app/instrument/site). */
  onFooterContextChange?: (context: string) => void;
}

export function PersonaEvalCockpit({
  options,
  onOpenRuns,
  onDomainChange,
  onFooterContextChange,
}: PersonaEvalCockpitProps) {
  const [taskType, setTaskType] = useState<PersonaEvalTaskType>("chatbot");
  if (taskType === "survey") {
    return (
      <SurveyEvalCockpit
        options={options}
        taskType={taskType}
        onTaskTypeChange={setTaskType}
        onFooterContextChange={onFooterContextChange}
      />
    );
  }
  if (taskType === "web") {
    return (
      <WebEvalCockpit
        options={options}
        taskType={taskType}
        onTaskTypeChange={setTaskType}
        onFooterContextChange={onFooterContextChange}
      />
    );
  }
  return (
    <ChatbotEvalCockpit
      options={options}
      onOpenRuns={onOpenRuns}
      onDomainChange={onDomainChange}
      onFooterContextChange={onFooterContextChange}
      taskType={taskType}
      onTaskTypeChange={setTaskType}
    />
  );
}

interface ChatbotEvalCockpitProps extends PersonaEvalCockpitProps {
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
}

function ChatbotEvalCockpit({
  options,
  onOpenRuns,
  onDomainChange,
  onFooterContextChange,
  taskType,
  onTaskTypeChange,
}: ChatbotEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry, reset } = usePersonaEval();

  // --- Selection + run knobs ---------------------------------------------
  const [persona, setPersona] = useState<PersonaEvalPersona | null>(null);
  const [applicationId, setApplicationId] = useState<ApplicationId>(
    (options?.defaults.applicationId as ApplicationId | undefined) ?? "recai",
  );
  const [domain, setDomain] = useState<Domain>((options?.defaults.domain as Domain) ?? "movie");
  const [engine, setEngine] = useState<string>(options?.defaults.engine ?? "gpt-4o-mini");
  const [personaModel, setPersonaModel] = useState<string>(
    options?.environment.personaModel ?? "anthropic/claude-haiku-4-5",
  );
  const [goalContextId, setGoalContextId] = useState<string | null>(null);
  const [maxTurns, setMaxTurns] = useState<number>(8);
  const [exportSnapshot, setExportSnapshot] = useState<ExportSnapshot | null>(null);

  // Adopt the canonical defaults once config metadata arrives.
  const adoptedDefaults = useRef(false);
  useEffect(() => {
    if (adoptedDefaults.current || !options) return;
    adoptedDefaults.current = true;
    setApplicationId((options.defaults.applicationId as ApplicationId | undefined) ?? "recai");
    setDomain((options.defaults.domain as Domain) ?? "movie");
    setEngine(options.defaults.engine ?? "gpt-4o-mini");
    setPersonaModel(options.environment.personaModel ?? "anthropic/claude-haiku-4-5");
  }, [options]);

  // Mirror the run domain up so the shared (⌘K) catalog drawer matches it.
  useEffect(() => {
    onDomainChange?.(domain);
  }, [domain, onDomainChange]);

  const applicationContext = contextForApplication(applicationId, domain);
  const requestDomain = applicationId === "recai" ? domain : undefined;

  // --- Goal contexts (the "Conversation style" knob) ----------------------
  const goalContextsQuery = useQuery<GoalContextsResponse>({
    queryKey: ["persona-eval-goal-contexts"],
    queryFn: listGoalContexts,
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  const goalContexts: GoalContext[] = useMemo(
    () => goalContextsQuery.data?.goalContexts ?? [],
    [goalContextsQuery.data],
  );
  const activeGoalContext =
    goalContexts.find((g) => g.id === (goalContextId ?? goalContexts[0]?.id)) ?? null;

  // Live persona + controls, mirrored to a ref so the "run finished" effect can
  // freeze them without re-running when a control changes.
  const liveControls = useMemo<ExportSnapshot>(
    () => ({
      persona: persona ? { id: persona.id, name: persona.name, source: persona.source } : null,
      config: {
        applicationId,
        applicationContext,
        domain: requestDomain,
        engine,
        personaModel,
        goalContextId: goalContextId ?? activeGoalContext?.id ?? null,
        maxTurns,
      },
    }),
    [persona, applicationId, applicationContext, requestDomain, engine, personaModel, goalContextId, activeGoalContext, maxTurns],
  );
  const liveControlsRef = useRef(liveControls);
  liveControlsRef.current = liveControls;

  useEffect(() => {
    if (phase === "done") {
      setExportSnapshot((prev) => prev ?? liveControlsRef.current);
    }
  }, [phase]);

  // --- Inspector + folds + focus -----------------------------------------
  const [tab, setTab] = useState<InspectorTab>("evaluation");
  const [expandedTurns, setExpandedTurns] = useState<Set<number>>(new Set());
  const [focusedTurnIndex, setFocusedTurnIndex] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const turnRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // --- Elapsed clock (live status bar) -----------------------------------
  const runStartedAtRef = useRef<number | null>(null);
  const [, setNowTick] = useState(0);
  useEffect(() => {
    if (!isRunning) return;
    const id = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [isRunning]);

  const turns = useMemo(() => job?.turns ?? [], [job]);
  const sutDescription = job?.sutDescription ?? null;
  const status = liveStatusLine(job, phase, isRunning);
  const questionnaire = job?.questionnaire ?? null;
  const metrics = job?.metricScores ?? null;
  const prompts = job?.prompts ?? null;

  const applicationOptions: ConfigOptionValue[] = useMemo(() => {
    const knob = (options?.knobs ?? []).find((k) => k.key === "applicationId");
    return knob?.options ?? [];
  }, [options]);
  const appName = APP_NAME[applicationId] ?? applicationOptions.find((o) => o.value === applicationId)?.label ?? "The app";
  const runContext = `${appName}${applicationId === "recai" ? ` · ${fmtDomain(domain)}` : ""}`;

  // Report the honest footer context up (task type + app + domain for RecAI).
  useEffect(() => {
    onFooterContextChange?.(`chatbot · ${runContext}`);
  }, [runContext, onFooterContextChange]);

  // --- Actions ------------------------------------------------------------
  const handleRun = useCallback(() => {
    if (!persona || isRunning) return;
    setExpandedTurns(new Set());
    setFocusedTurnIndex(null);
    setExportSnapshot(null);
    runStartedAtRef.current = Date.now();
    run({
      domain: requestDomain,
      applicationId,
      applicationContext,
      personaId: persona.id,
      goalContextId: goalContextId ?? undefined,
      maxTurns,
      engine: engine as Engine,
      personaModel: personaModel as PersonaModel,
    });
  }, [persona, isRunning, run, requestDomain, applicationId, applicationContext, goalContextId, maxTurns, engine, personaModel]);

  const handleRetry = useCallback(() => {
    if (timedOut || phase === "error") retry();
    else handleRun();
  }, [timedOut, phase, retry, handleRun]);

  const handleNewRun = useCallback(() => {
    reset();
    setFocusedTurnIndex(null);
    setExpandedTurns(new Set());
  }, [reset]);

  const handleSelectPersona = useCallback((next: PersonaEvalPersona) => setPersona(next), []);

  const registerTurnRef = useCallback((index: number, el: HTMLDivElement | null) => {
    if (el) turnRefs.current.set(index, el);
    else turnRefs.current.delete(index);
  }, []);

  const toggleTurnFold = useCallback((index: number) => {
    setExpandedTurns((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  const toggleExpandAll = useCallback(() => {
    setExpandedTurns((prev) => (prev.size >= turns.length && turns.length > 0 ? new Set() : new Set(turns.map((_, i) => i))));
  }, [turns]);

  const moveFocus = useCallback(
    (delta: number) => {
      if (turns.length === 0) return;
      setFocusedTurnIndex((prev) => {
        const start = prev ?? (delta > 0 ? -1 : turns.length);
        const next = Math.max(0, Math.min(turns.length - 1, start + delta));
        const el = turnRefs.current.get(next);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
        return next;
      });
    },
    [turns.length],
  );

  // --- Export (client-side JSON of the completed run) ---------------------
  const handleExport = useCallback(() => {
    if (!exportSnapshot || turns.length === 0) return;
    const payload = {
      persona: exportSnapshot.persona,
      config: exportSnapshot.config,
      transcript: turns,
      questionnaire,
      metricScores: metrics,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `persona-eval-${exportSnapshot.persona?.id ?? "run"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportSnapshot, turns, questionnaire, metrics]);

  // --- Keyboard shortcuts -------------------------------------------------
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (isTypingTarget(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
      switch (e.key) {
        case "r":
        case "R":
          e.preventDefault();
          handleRun();
          break;
        case "j":
        case "J":
          e.preventDefault();
          moveFocus(1);
          break;
        case "k":
        case "K":
          e.preventDefault();
          moveFocus(-1);
          break;
        case "1":
          e.preventDefault();
          setTab("evaluation");
          break;
        case "2":
          e.preventDefault();
          setTab("persona");
          break;
        case "3":
          e.preventDefault();
          setTab("prompts");
          break;
        case "e":
        case "E":
          e.preventDefault();
          toggleExpandAll();
          break;
        default:
          break;
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [handleRun, moveFocus, toggleExpandAll]);

  const knobs = options?.knobs ?? [];
  const environment = options?.environment ?? null;
  const showSetup = phase === "idle";
  const canExport = exportSnapshot !== null && turns.length > 0;
  const elapsedSeconds =
    isRunning && runStartedAtRef.current ? Math.max(0, Math.floor((Date.now() - runStartedAtRef.current) / 1000)) : 0;

  // ---------------------------------------------------------------------------
  // IDLE: the centered "Configure a simulation" setup form.
  // ---------------------------------------------------------------------------
  const setupView = (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="custom-scrollbar flex-1 overflow-y-auto bg-surface-dim">
        <div className="mx-auto w-full max-w-[1180px] px-6 py-7">
          <RunHeader taskType={taskType} onTaskTypeChange={onTaskTypeChange} running={isRunning} />

          <div className="mb-5">
            <ComponentPipeline
              variant="setup"
              environment={environment}
              engine={engine}
              personaModel={personaModel}
              phase={phase}
              jobPhase={job?.phase}
              hasPersona={persona !== null}
              turnCount={turns.length}
              hasQuestionnaire={questionnaire !== null}
            />
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
            {/* LEFT (8) */}
            <div className="space-y-5 lg:col-span-8">
              <ApplicationPicker
                options={applicationOptions}
                value={applicationId}
                onChange={(v) => setApplicationId(v as ApplicationId)}
                disabled={isRunning}
              />
              <RunConfigBar
                knobs={knobs}
                goalContexts={goalContexts}
                applicationId={applicationId}
                engine={engine}
                onEngine={setEngine}
                personaModel={personaModel}
                onPersonaModel={setPersonaModel}
                domain={domain}
                onDomain={setDomain}
                goalContextId={goalContextId}
                onGoalContext={setGoalContextId}
                maxTurns={maxTurns}
                onMaxTurns={setMaxTurns}
                disabled={isRunning}
              />
              <TargetPersonaPanel persona={persona} onChange={() => setPickerOpen(true)} />
            </div>

            {/* RIGHT (4) */}
            <div className="space-y-5 lg:col-span-4">
              <EnvironmentPanel environment={environment} applicationId={applicationId} />

              {error && (
                <div className="rise-in rounded-md border border-danger/40 bg-danger/10 p-3">
                  <div className="flex items-start gap-2">
                    <Sym name="error" fill={1} size={18} className="mt-0.5 text-danger" />
                    <div className="min-w-0">
                      <p className="text-[12px] font-semibold text-text-main">Couldn&apos;t start the run</p>
                      <p className="mt-0.5 break-words text-[11px] text-text-variant">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={handleRun}
                disabled={!persona || isRunning}
                title={!persona ? "Choose a persona first." : undefined}
                className={`glow flex w-full items-center justify-center gap-2.5 rounded-md bg-primary py-4 text-on-primary transition ease-out hover:bg-primary-dim active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55 disabled:active:scale-100 ${FOCUS_RING}`}
              >
                <Sym name="play_arrow" fill={1} size={20} />
                <span className="font-display text-[18px] font-bold tracking-tight">Run eval</span>
              </button>
              <p className="text-center text-[11px] leading-relaxed text-text-variant">
                A simulated user chats with the app for a few turns, then rates how well it understood and met their needs.
              </p>
              <div className="flex items-center justify-center pt-1">
                <button
                  type="button"
                  onClick={onOpenRuns}
                  className={`hud text-[9px] text-primary underline-offset-2 transition-opacity hover:underline active:opacity-70 ${FOCUS_RING}`}
                >
                  Past runs →
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // ---------------------------------------------------------------------------
  // RUNNING / DONE: the live-run layout.
  // ---------------------------------------------------------------------------
  const liveView = (
    <div className="flex min-h-0 flex-1 flex-col bg-surface-dim">
      {/* Pipeline strip */}
      <div className="shrink-0 border-b border-outline bg-surface-lowest px-5 py-3">
        <div className="flex items-center gap-3">
          <ComponentPipeline
            variant="live"
            environment={environment}
            engine={engine}
            personaModel={personaModel}
            phase={phase}
            jobPhase={job?.phase}
            hasPersona={persona !== null}
            turnCount={turns.length}
            hasQuestionnaire={questionnaire !== null}
          />
          <div className="ml-auto flex shrink-0 items-center gap-3">
            <span className="hud hidden text-[9px] text-text-dim sm:inline">{runContext}</span>
            <button
              type="button"
              onClick={handleNewRun}
              className={`flex items-center gap-1.5 rounded-md border border-outline bg-surface-low px-3 py-1.5 text-[12px] text-text-variant transition ease-out hover:border-primary hover:text-text-main active:scale-[0.98] ${FOCUS_RING}`}
            >
              <Sym name="tune" size={14} />
              New run
            </button>
          </div>
        </div>
      </div>

      {/* Body: thread + inspector */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">
        <Trajectory
          turns={turns}
          domain={domain}
          appName={appName}
          sutDescription={sutDescription}
          goalContext={activeGoalContext}
          phase={phase}
          liveStatus={status}
          error={error}
          expandedTurns={expandedTurns}
          onToggleTurn={toggleTurnFold}
          focusedTurnIndex={focusedTurnIndex}
          registerTurnRef={registerTurnRef}
          onRetry={handleRetry}
        />
        <InspectorTabs
          active={tab}
          onChange={setTab}
          evaluation={<Scorecard questionnaire={questionnaire} metrics={metrics} phase={phase} />}
          persona={<PersonaPanel persona={persona} context={null} onOpenRaw={() => setDrawerOpen(true)} />}
          prompts={<PromptPanel prompts={prompts} />}
        />
      </div>

      {/* Bottom status bar */}
      <LiveStatusBar
        phase={phase}
        turnCount={turns.length}
        maxTurns={maxTurns}
        elapsedSeconds={elapsedSeconds}
        jobId={job?.jobId ?? null}
        error={error}
        canExport={canExport}
        onExport={handleExport}
        onOpenRuns={onOpenRuns}
        onRetry={handleRetry}
      />
    </div>
  );

  return (
    <>
      {showSetup ? setupView : liveView}
      <PersonaPickerModal
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        selectedId={persona?.id ?? null}
        onSelect={handleSelectPersona}
      />
      <PersonaDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} persona={persona} context={null} />
    </>
  );
}

// ---------------------------------------------------------------------------
// Setup-form sub-components (presentational, local to the cockpit).
// ---------------------------------------------------------------------------

/** The 3-card application picker (RecAI / OpenBB / Medical), mockup `:148-168`. */
function ApplicationPicker({
  options,
  value,
  onChange,
  disabled,
}: {
  options: ConfigOptionValue[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  if (options.length === 0) return null;
  return (
    <div className="panel rounded-md border border-outline bg-surface p-5">
      <div className="mb-3.5 flex items-center justify-between">
        <h3 className="hud text-[10px] text-text-dim">Application</h3>
        <span className="hud text-[9px] text-text-dim">{options.length} adapters</span>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {options.map((opt) => {
          const active = opt.value === value;
          return (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              aria-pressed={active}
              onClick={() => onChange(opt.value)}
              className={`relative rounded-md border p-3.5 text-left transition-all ease-out hover:border-primary active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100 ${FOCUS_RING} ${
                active ? "border-primary bg-primary/[0.07]" : "border-outline bg-surface-low hover:bg-surface"
              }`}
            >
              {active && <Sym name="check" size={14} className="absolute right-3 top-3 text-primary" />}
              <div className="mb-3 grid h-9 w-9 place-items-center rounded border border-outline bg-surface-high">
                <Sym name={APP_ICON[opt.value] ?? "apps"} size={20} className={active ? "text-primary" : "text-text-variant"} />
              </div>
              <div className="text-[13px] font-semibold text-text-main">{opt.label}</div>
              <div className="mt-0.5 line-clamp-2 text-[11px] leading-snug text-text-variant">{opt.description}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** The "Target persona" panel: avatar + identity + Change, mockup `:233-244`. */
function TargetPersonaPanel({ persona, onChange }: { persona: PersonaEvalPersona | null; onChange: () => void }) {
  const title = persona ? personaDescriptiveTitle(null, persona.blurb, persona.source) : null;
  const codename = persona ? personaCodename(persona.name, persona.id) : null;

  return (
    <div className="panel rounded-md border border-outline bg-surface p-5">
      <div className="mb-3.5 flex items-center justify-between">
        <h3 className="hud text-[10px] text-text-dim">Target persona</h3>
        <button type="button" onClick={onChange} className={`hud text-[9px] text-primary underline-offset-2 transition-opacity hover:underline active:opacity-70 ${FOCUS_RING}`}>
          Browse catalog →
        </button>
      </div>
      {persona ? (
        <div className="rise-in flex items-center gap-4">
          <div className="grid h-14 w-14 shrink-0 place-items-center rounded-md border border-outline bg-surface-high">
            <Sym name="face" fill={1} size={24} className="text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="min-w-0 break-words font-display text-[16px] font-semibold text-text-main">{title}</span>
              {persona.source && (
                <span className="hud rounded border border-secondary/30 bg-secondary/10 px-1.5 py-0.5 text-[8px] text-secondary">
                  {persona.source}
                </span>
              )}
              <span className="font-mono text-[10px] text-text-dim">{codename}</span>
            </div>
            <p className="mt-0.5 line-clamp-2 text-[12px] leading-snug text-text-variant">{persona.blurb}</p>
          </div>
          <button
            type="button"
            onClick={onChange}
            className={`shrink-0 rounded-md border border-outline bg-surface-low px-3 py-1.5 text-[12px] text-text-variant transition ease-out hover:border-primary hover:text-text-main active:scale-[0.98] ${FOCUS_RING}`}
          >
            Change
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={onChange}
          className={`flex w-full items-center gap-4 rounded-md border border-dashed border-outline bg-surface-low p-3 text-left transition ease-out hover:border-primary hover:bg-surface active:scale-[0.99] ${FOCUS_RING}`}
        >
          <div className="grid h-14 w-14 shrink-0 place-items-center rounded-md border border-dashed border-outline bg-surface-high">
            <Sym name="person_search" size={24} className="text-text-dim" />
          </div>
          <div>
            <div className="font-display text-[16px] font-semibold text-text-main">Choose a persona</div>
            <p className="mt-0.5 text-[12px] leading-snug text-text-variant">
              PersonaEval needs a target persona before it can run.
            </p>
          </div>
        </button>
      )}
    </div>
  );
}

/** A modal that hosts the existing `PersonaCatalog` for selecting a persona. */
function PersonaPickerModal({
  open,
  onClose,
  selectedId,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  selectedId: string | null;
  onSelect: (persona: PersonaEvalPersona) => void;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fade-in absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Choose a persona"
        className="pop-in relative z-10 flex h-[80vh] w-full max-w-[380px] flex-col overflow-hidden rounded-md border border-outline bg-surface-lowest shadow-2xl"
      >
        <div className="flex shrink-0 items-center justify-between border-b border-outline px-4 py-3">
          <span className="hud text-[10px] text-primary">Choose a persona</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className={`grid h-8 w-8 place-items-center rounded-md border border-outline text-text-variant transition ease-out hover:border-primary hover:text-text-main active:scale-95 ${FOCUS_RING}`}
          >
            <Sym name="close" size={18} />
          </button>
        </div>
        <div className="flex min-h-0 flex-1 [&_aside]:!h-full [&_aside]:!w-full [&_aside]:!border-0">
          <PersonaCatalog
            selectedId={selectedId}
            onSelect={(p) => {
              onSelect(p);
              onClose();
            }}
          />
        </div>
      </div>
    </div>
  );
}

/** The live-run bottom status bar (mockup `:537-547`). */
function LiveStatusBar({
  phase,
  turnCount,
  maxTurns,
  elapsedSeconds,
  jobId,
  error,
  canExport,
  onExport,
  onOpenRuns,
  onRetry,
}: {
  phase: PersonaEvalRunPhase;
  turnCount: number;
  maxTurns: number;
  elapsedSeconds: number;
  jobId: string | null;
  error: string | null;
  canExport: boolean;
  onExport: () => void;
  onOpenRuns: () => void;
  onRetry: () => void;
}) {
  const building = phase === "building";
  const running = phase === "running";
  const done = phase === "done";
  const failed = phase === "error" || phase === "timeout";
  const pct = done ? 100 : running ? Math.min(100, Math.round((turnCount / Math.max(1, maxTurns)) * 100)) : building ? 12 : 100;

  return (
    <div className="shrink-0 border-t border-outline bg-surface-lowest px-5 py-3">
      <div className="flex items-center gap-3">
        {building || running ? (
          <Sym name="autorenew" size={14} className="shrink-0 animate-rb-spin text-primary" />
        ) : done ? (
          <Sym name="check_circle" fill={1} size={14} className="shrink-0 text-secondary" />
        ) : (
          <Sym name="error" fill={1} size={14} className="shrink-0 text-danger" />
        )}

        <span className="min-w-0 truncate text-[12px] text-text-variant">
          {building && "Starting the app. The first reply can take up to a minute."}
          {running && (
            <>
              Running eval <span className="text-text-dim">·</span> turn {turnCount} of {maxTurns}{" "}
              <span className="text-text-dim">·</span> {elapsedSeconds}s elapsed
            </>
          )}
          {done && (
            <>
              Run complete <span className="text-text-dim">·</span> {turnCount} turn{turnCount === 1 ? "" : "s"}
            </>
          )}
          {failed && <span className="text-danger">{error ?? "The run stopped before completing."}</span>}
        </span>

        <div className="ml-auto flex shrink-0 items-center gap-2.5">
          {failed && (
            <button
              type="button"
              onClick={onRetry}
              className={`flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-3 py-1.5 text-[12px] font-medium text-danger transition ease-out hover:bg-danger/20 active:scale-[0.98] ${FOCUS_RING}`}
            >
              <Sym name="refresh" size={14} />
              Retry
            </button>
          )}
          {(done || failed) && (
            <button
              type="button"
              onClick={onExport}
              disabled={!canExport}
              title="Save this conversation and its scores as a JSON file."
              className={`flex items-center gap-1.5 rounded-md border border-outline bg-surface-low px-3 py-1.5 text-[12px] text-text-variant transition ease-out hover:border-primary hover:text-text-main active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-55 disabled:active:scale-100 ${FOCUS_RING}`}
            >
              <Sym name="download" size={14} />
              Download
            </button>
          )}
          <button
            type="button"
            onClick={onOpenRuns}
            className={`hidden items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] text-text-variant transition ease-out hover:text-primary active:scale-[0.98] sm:flex ${FOCUS_RING}`}
          >
            <Sym name="history" size={14} />
            Past runs
          </button>
          {jobId && <span className="hud hidden font-mono text-[9px] text-text-dim md:inline">{jobId.slice(0, 8)}</span>}
        </div>
      </div>

      <div className="mt-2.5 h-0.5 w-full overflow-hidden rounded-full bg-field">
        <div
          className={`h-full rounded-full transition-[width] duration-500 ${failed ? "bg-danger" : done ? "bg-secondary" : "bg-primary"} ${building ? "animate-pulse" : ""}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function contextForApplication(applicationId: ApplicationId, domain: Domain): string {
  if (applicationId === "finance_openbb") return "financial_research";
  if (applicationId === "medical_assistant") return "medical_consultation";
  return domain;
}

export default PersonaEvalCockpit;
