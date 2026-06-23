/**
 * PersonaEvalCockpit — the Persona Eval surface (ports cockpit-stitch-v2.html).
 *
 * The full three-column cockpit (the Persona Eval surface):
 *   - LEFT   `PersonaCatalog` — the curated persona catalog;
 *   - CENTRE `RunHeader` + `RunConfigBar` + `Trajectory` — the run identity, the
 *     editable knobs / fixed-environment facts, and the pure conversation;
 *   - RIGHT  `InspectorTabs` — Evaluation (`Scorecard`) · Persona (`PersonaPanel`).
 *
 * It owns the cross-component state (selected persona, run knobs, the run via
 * `usePersonaEval`, the inspector tab, the open tool-plan folds, the focused
 * turn) and the keyboard shortcuts the brief requires:
 *   R run / re-run · J/K move between turns · 1/2 switch inspector tab ·
 *   E expand / collapse all tool-plans.
 * Shortcuts are ignored while typing in a field. Transitions respect
 * `prefers-reduced-motion` via the global utility fallbacks in `index.css`.
 *
 * Data is honest: it wires the real personas / goal-contexts / config / run
 * endpoints and renders the real run shape (real per-turn latency; no tokens or
 * cost, which aren't tracked).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { PersonaCatalog } from "./PersonaCatalog";
import { RunHeader } from "./RunHeader";
import { RunConfigBar } from "./RunConfigBar";
import { Trajectory } from "./Trajectory";
import { InspectorTabs, type InspectorTab } from "./InspectorTabs";
import { Scorecard } from "./Scorecard";
import { PersonaPanel } from "./PersonaPanel";
import { PersonaDrawer } from "./PersonaDrawer";
import { listGoalContexts } from "@/lib/api";
import { usePersonaEval, type PersonaEvalRunPhase } from "@/lib/usePersonaEval";
import type {
  ConfigOptionsResponse,
  Domain,
  Engine,
  GoalContext,
  GoalContextsResponse,
  PersonaEvalJobView,
  PersonaEvalPersona,
} from "@/lib/types";

/** Map the job's coarse phase into a single "what's happening now" line. */
function liveStatusLine(
  job: PersonaEvalJobView | null,
  phase: PersonaEvalRunPhase,
  isRunning: boolean,
): string | null {
  if (phase === "building") return "Warming the recommender — this first turn can take a minute.";
  if (!isRunning) return null;
  const raw = (job?.phase ?? "").toLowerCase();
  if (raw.includes("persona") || raw.includes("user") || raw.includes("simulat")) return "Persona is thinking…";
  if (raw.includes("recommend") || raw.includes("agent") || raw.includes("recai") || raw.includes("turn"))
    return "Recommender is thinking…";
  if (raw.includes("eval")) return "Scoring the conversation…";
  if (job?.phase) return `${job.phase}…`;
  return "Running the persona eval…";
}

/** True when focus is in a text input / textarea / select / contenteditable. */
function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
}

/**
 * A frozen copy of the persona + run controls captured the moment a run reaches
 * the terminal `done` state. The export is built from this — never the live
 * controls — so changing a knob after a run finishes cannot mislabel the
 * already-completed transcript.
 */
interface ExportSnapshot {
  persona: { id: string; name: string; source: string } | null;
  config: {
    domain: Domain;
    engine: string;
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
}

export function PersonaEvalCockpit({ options, onOpenRuns, onDomainChange }: PersonaEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry } = usePersonaEval();

  // --- Selection + run knobs ---------------------------------------------
  const [persona, setPersona] = useState<PersonaEvalPersona | null>(null);
  const [domain, setDomain] = useState<Domain>((options?.defaults.domain as Domain) ?? "movie");
  const [engine, setEngine] = useState<string>(options?.defaults.engine ?? "gpt-4o-mini");
  const [goalContextId, setGoalContextId] = useState<string | null>(null);
  const [maxTurns, setMaxTurns] = useState<number>(8);
  // Frozen persona + controls captured when a run reaches `done`; the export is
  // built from this, never the (possibly since-changed) live controls.
  const [exportSnapshot, setExportSnapshot] = useState<ExportSnapshot | null>(null);

  // Adopt the canonical defaults once config metadata arrives (without
  // clobbering an operator's explicit change).
  const adoptedDefaults = useRef(false);
  useEffect(() => {
    if (adoptedDefaults.current || !options) return;
    adoptedDefaults.current = true;
    setDomain((options.defaults.domain as Domain) ?? "movie");
    setEngine(options.defaults.engine ?? "gpt-4o-mini");
  }, [options]);

  // Mirror the run domain up so the shared (⌘K) catalog drawer browses the
  // same domain's corpus the operator is evaluating against.
  useEffect(() => {
    onDomainChange?.(domain);
  }, [domain, onDomainChange]);

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

  // Live persona + controls, kept in a ref so the "run finished" effect can
  // freeze them into `exportSnapshot` without re-running when a control changes.
  const liveControls = useMemo<ExportSnapshot>(
    () => ({
      persona: persona ? { id: persona.id, name: persona.name, source: persona.source } : null,
      config: {
        domain,
        engine,
        goalContextId: goalContextId ?? activeGoalContext?.id ?? null,
        maxTurns,
      },
    }),
    [persona, domain, engine, goalContextId, activeGoalContext, maxTurns],
  );
  const liveControlsRef = useRef(liveControls);
  liveControlsRef.current = liveControls;

  // Freeze the export snapshot the moment the run finishes. Depending only on
  // `phase` (and reading controls from the ref) means a later knob change does
  // not re-run this and cannot overwrite the frozen snapshot. A fresh run clears
  // the snapshot back to null (see `handleRun`).
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
  const turnRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const turns = useMemo(() => job?.turns ?? [], [job]);
  const personaName = job?.personaName ?? persona?.name ?? "Persona";
  // SUT description: from the live job, else (no run yet) the goal-context blurb.
  const sutDescription = job?.sutDescription ?? null;
  const status = liveStatusLine(job, phase, isRunning);
  const hasRun = phase === "done" || phase === "error" || phase === "timeout";
  const questionnaire = job?.questionnaire ?? null;
  const metrics = job?.metricScores ?? null;

  // --- Actions ------------------------------------------------------------
  const handleRun = useCallback(() => {
    if (!persona || isRunning) return;
    setExpandedTurns(new Set());
    setFocusedTurnIndex(null);
    setExportSnapshot(null);
    run({
      domain,
      personaId: persona.id,
      goalContextId: goalContextId ?? undefined,
      maxTurns,
      engine: engine as Engine,
    });
  }, [persona, isRunning, run, domain, goalContextId, maxTurns, engine]);

  const handleRetry = useCallback(() => {
    if (timedOut || phase === "error") retry();
    else handleRun();
  }, [timedOut, phase, retry, handleRun]);

  const handleSelectPersona = useCallback((next: PersonaEvalPersona) => {
    setPersona(next);
  }, []);

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
  // Built from the frozen `exportSnapshot` (persona + controls as they were when
  // the run finished), never the live controls — so editing a knob afterwards
  // cannot mislabel the already-completed transcript. Enabled only once a
  // snapshot exists (i.e. a run has reached `done`).
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

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* LEFT — persona catalog */}
      <PersonaCatalog selectedId={persona?.id ?? null} onSelect={handleSelectPersona} />

      {/* CENTRE — run header + knob bar + trajectory */}
      <main className="relative z-0 flex min-w-0 flex-1 flex-col bg-background">
        <RunHeader
          persona={persona}
          context={null}
          running={isRunning}
          hasRun={hasRun}
          onRun={handleRun}
          onExport={handleExport}
          canExport={exportSnapshot !== null && turns.length > 0}
          onOpenRuns={onOpenRuns}
        />
        <RunConfigBar
          knobs={knobs}
          environment={environment}
          goalContexts={goalContexts}
          engine={engine}
          onEngine={setEngine}
          domain={domain}
          onDomain={setDomain}
          goalContextId={goalContextId}
          onGoalContext={setGoalContextId}
          maxTurns={maxTurns}
          onMaxTurns={setMaxTurns}
          disabled={isRunning}
        />
        <Trajectory
          turns={turns}
          domain={domain}
          personaName={personaName}
          sutDescription={sutDescription}
          goalContext={activeGoalContext}
          phase={phase}
          liveStatus={status}
          error={error}
          hasPersona={persona !== null}
          expandedTurns={expandedTurns}
          onToggleTurn={toggleTurnFold}
          focusedTurnIndex={focusedTurnIndex}
          registerTurnRef={registerTurnRef}
          onRetry={handleRetry}
        />
      </main>

      {/* RIGHT — inspector tabs */}
      <InspectorTabs
        active={tab}
        onChange={setTab}
        evaluation={<Scorecard questionnaire={questionnaire} metrics={metrics} phase={phase} />}
        persona={
          <PersonaPanel persona={persona} context={null} onOpenRaw={() => setDrawerOpen(true)} />
        }
      />

      <PersonaDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} persona={persona} context={null} />
    </div>
  );
}

export default PersonaEvalCockpit;
