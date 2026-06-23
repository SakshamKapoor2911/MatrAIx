/**
 * RecBot Studio — application shell.
 *
 * Wires the locked three-pane Workbench (top bar · session rail · chat · turn
 * inspector) to the typed API client and TanStack Query. App owns the small
 * amount of cross-pane UI state — the active session id, the focused turn, and
 * whether the catalog drawer is open — and delegates everything else to the
 * data layer:
 *
 *   - `GET /api/config/options`   → config pill choices + defaults
 *   - `GET /api/sessions`         → the left rail
 *   - `GET /api/sessions/{id}`    → the active conversation + inspector
 *   - `useTurnJob`                → submit a turn, poll the async job, refetch
 *
 * Mutations (create session, patch config, save) optimistically refresh the
 * relevant queries via the shared `sessionKeys`, so the rail and thread stay in
 * sync without bespoke cache surgery.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { TopBar, type StudioMode } from "@/components/TopBar";
import { ChatConfigBar } from "@/components/ChatConfigBar";
import { SessionRail } from "@/components/SessionRail";
import { ChatThread } from "@/components/ChatThread";
import { Composer } from "@/components/Composer";
import { TurnInspector } from "@/components/TurnInspector";
import { CatalogDrawer } from "@/components/CatalogDrawer";
import { PersonaEvalCockpit } from "@/components/cockpit/PersonaEvalCockpit";
import { RunsView } from "@/components/RunsView";

import { api, sessionExportUrl } from "@/lib/api";
import { sessionKeys, useTurnJob } from "@/lib/useTurnJob";
import { useUrlState } from "@/lib/useUrlState";
import type {
  ConfigOptionsResponse,
  Domain,
  Session,
  SessionConfig,
  SessionSummary,
} from "@/lib/types";

/** The two surfaces we accept from the URL (anything else falls back). */
const STUDIO_MODES: ReadonlyArray<StudioMode> = ["normal", "persona-eval"];

/** Coerce a free-form URL `mode` value into a valid `StudioMode`. */
function parseMode(value: string | null): StudioMode {
  return value && (STUDIO_MODES as readonly string[]).includes(value)
    ? (value as StudioMode)
    : "normal";
}

/** Parse the URL `turn` value into a focused turn index, or `null` (follow latest). */
function parseTurnIndex(value: string | null): number | null {
  if (value === null) return null;
  const n = Number.parseInt(value, 10);
  return Number.isInteger(n) && n >= 0 ? n : null;
}

/** Operator identity for the chat avatar (wired from the environment later). */
const OPERATOR_ID = "qianfeng.wen@mail.utoronto.ca";

/** Format a turn duration for the centre header chip ("~2.4s"). */
function fmtDuration(seconds: number | null | undefined): string | null {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return null;
  if (seconds < 1) return "<1s";
  if (seconds < 60) return `~${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `~${m}m ${s}s`;
}

export default function App() {
  const queryClient = useQueryClient();

  // --- Cross-pane UI state (URL-driven) -----------------------------------
  // `mode` / `session` / `turn` / `run` live in the URL (+ a localStorage
  // mirror) so a refresh restores the view and a link reopens it. `catalogOpen`
  // and `followLatest` are transient and stay local.
  const { state: urlState, setState: setUrlState } = useUrlState();
  const mode = parseMode(urlState.mode);
  const activeId = urlState.session;
  const activeTurnIndex = parseTurnIndex(urlState.turn);
  // Runs now live INSIDE Persona Eval. The runs sub-view is URL-driven:
  //   view=runs                  → the runs history list
  //   run set                    → that run's detail
  //   run + compareWith          → the side-by-side compare
  // A `run`/`compareWith` selection implies the runs sub-view even without
  // `view=runs`, so a shared deep link to a run still resolves.
  const activeRunId = urlState.run;
  const compareWithRunId = urlState.compareWith;
  const runsViewActive =
    mode === "persona-eval" && (urlState.view === "runs" || activeRunId !== null);

  const [catalogOpen, setCatalogOpen] = useState(false);
  // The persona-eval cockpit's active domain, mirrored up so the shared (⌘K)
  // catalog drawer browses the same domain in that surface.
  const [pevalDomain, setPevalDomain] = useState<Domain>("movie");

  // --- Runs navigation handlers (Persona Eval → Runs sub-view) ------------
  const openRunsList = useCallback(() => {
    setUrlState({ view: "runs", run: null, compareWith: null });
  }, [setUrlState]);
  const openRun = useCallback(
    (id: string) => {
      setUrlState({ view: "runs", run: id, compareWith: null });
    },
    [setUrlState],
  );
  const compareRuns = useCallback(
    (a: string, b: string) => {
      setUrlState({ view: "runs", run: a, compareWith: b });
    },
    [setUrlState],
  );
  const backToRunsList = useCallback(() => {
    setUrlState({ view: "runs", run: null, compareWith: null });
  }, [setUrlState]);
  /** Leave the Runs sub-view, back to the cockpit. */
  const closeRunsView = useCallback(() => {
    setUrlState({ view: null, run: null, compareWith: null });
  }, [setUrlState]);

  const setMode = useCallback(
    (next: StudioMode) => {
      // Switching surface always lands on the surface's primary view (clears any
      // runs sub-view so Persona Eval opens on the cockpit, not the runs list).
      setUrlState({
        mode: next === "normal" ? null : next,
        view: null,
        run: null,
        compareWith: null,
      });
    },
    [setUrlState],
  );

  const setActiveId = useCallback(
    (id: string | null) => {
      setUrlState({ session: id });
    },
    [setUrlState],
  );

  const setActiveTurnIndex = useCallback(
    (index: number | null) => {
      setUrlState({ turn: index === null ? null : String(index) });
    },
    [setUrlState],
  );

  /** Re-enable "follow latest" by clearing the pinned turn from the URL. */
  const followLatestTurn = useCallback(() => {
    setUrlState({ turn: null });
  }, [setUrlState]);

  // --- Config options (static for the app's lifetime) ---------------------
  const optionsQuery = useQuery<ConfigOptionsResponse>({
    queryKey: ["config", "options"],
    queryFn: api.getConfigOptions,
    staleTime: Infinity,
  });
  // The ConfigBar now consumes the enriched `knobs` list directly (labels,
  // per-value descriptions, the `rebuildsAgent` warning flag).
  const knobs = optionsQuery.data?.knobs ?? null;

  // --- Session list (left rail) ------------------------------------------
  const sessionsQuery = useQuery<SessionSummary[]>({
    queryKey: sessionKeys.list(),
    queryFn: api.listSessions,
  });
  const sessions = useMemo(() => sessionsQuery.data ?? [], [sessionsQuery.data]);

  // --- Active session detail (centre + inspector) -------------------------
  const sessionQuery = useQuery<Session>({
    queryKey: activeId ? sessionKeys.detail(activeId) : ["sessions", "detail", "none"],
    queryFn: () => api.getSession(activeId as string),
    enabled: activeId !== null,
  });
  const session = sessionQuery.data ?? null;
  const turns = useMemo(() => session?.turns ?? [], [session]);

  // --- Create session -----------------------------------------------------
  const createMutation = useMutation({
    mutationFn: (input?: { title?: string; config?: Partial<SessionConfig> }) =>
      api.createSession(input),
    onSuccess: (created) => {
      queryClient.setQueryData(sessionKeys.detail(created.id), created);
      void queryClient.invalidateQueries({ queryKey: sessionKeys.list() });
      setUrlState({ session: created.id, turn: null });
    },
  });

  // --- Patch config -------------------------------------------------------
  const patchMutation = useMutation({
    mutationFn: (patch: Partial<SessionConfig>) => {
      if (!activeId) return Promise.reject(new Error("No active session"));
      return api.patchSessionConfig(activeId, patch);
    },
    onSuccess: (res) => {
      queryClient.setQueryData(sessionKeys.detail(res.session.id), res.session);
      void queryClient.invalidateQueries({ queryKey: sessionKeys.list() });
    },
  });

  // --- Save (persist to disk) --------------------------------------------
  // Saving is achieved by re-fetching the session, which the API persists on
  // read/patch; we expose an explicit Save by patching the (unchanged) config
  // so the operator gets a clear "Saved" affordance without a bespoke endpoint.
  const saveMutation = useMutation({
    mutationFn: () => {
      if (!activeId || !session) return Promise.reject(new Error("No active session"));
      return api.patchSessionConfig(activeId, session.config);
    },
    onSuccess: (res) => {
      queryClient.setQueryData(sessionKeys.detail(res.session.id), res.session);
    },
  });

  // --- Turn job (submit + poll) ------------------------------------------
  const onTurnDone = useCallback(() => {
    // A new turn landed; follow it in the inspector.
    followLatestTurn();
  }, [followLatestTurn]);
  const turnJob = useTurnJob(activeId, onTurnDone);

  // --- Auto-select a session on first load --------------------------------
  // Only when the URL carried no `session` (otherwise we'd clobber a shared link
  // / restored mirror that points at a specific — possibly not-yet-loaded —
  // session).
  useEffect(() => {
    if (activeId === null && sessions.length > 0) {
      setActiveId(sessions[0].id);
    }
  }, [activeId, sessions, setActiveId]);

  // --- Clamp a stale pinned turn into range -------------------------------
  // A pinned `turn` from the URL/mirror can outrun the loaded session (e.g. a
  // shared link to turn 9 of a session that now has 3). When following latest
  // the index is derived below, so this only fixes an out-of-range *pin*.
  useEffect(() => {
    if (activeTurnIndex !== null && activeTurnIndex > turns.length - 1) {
      setActiveTurnIndex(turns.length === 0 ? null : turns.length - 1);
    }
  }, [turns.length, activeTurnIndex, setActiveTurnIndex]);

  // --- ⌘K opens the catalog ----------------------------------------------
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        setCatalogOpen(true);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // --- Handlers -----------------------------------------------------------
  const handleNew = useCallback(() => {
    createMutation.mutate(
      optionsQuery.data ? { config: optionsQuery.data.defaults } : undefined,
    );
  }, [createMutation, optionsQuery.data]);

  const handleSelectSession = useCallback(
    (id: string) => {
      setUrlState({ session: id, turn: null });
      turnJob.reset();
    },
    [setUrlState, turnJob],
  );

  const handleConfigChange = useCallback(
    (patch: Partial<SessionConfig>) => {
      if (!activeId) return;
      patchMutation.mutate(patch);
    },
    [activeId, patchMutation],
  );

  const handleSelectTurn = useCallback(
    (index: number) => {
      setActiveTurnIndex(index);
    },
    [setActiveTurnIndex],
  );

  const handleSend = useCallback(
    (message: string) => {
      if (!activeId) {
        // No session yet: create one, then the operator re-sends. Creating is
        // fast; the cold start happens on the turn itself.
        handleNew();
        return;
      }
      followLatestTurn();
      turnJob.send(message);
    },
    [activeId, handleNew, turnJob, followLatestTurn],
  );

  const handleExport = useCallback(() => {
    if (!activeId) return;
    window.location.href = sessionExportUrl(activeId);
  }, [activeId]);

  // --- Derived view values ------------------------------------------------
  const config: SessionConfig | null = session
    ? (session.config as unknown as SessionConfig)
    : null;
  const headerTitle = session?.title ?? "New session";
  // The index the inspector/thread actually highlight: the pinned turn from the
  // URL, or — when following latest (no pin) — the most recent turn.
  const focusedTurnIndex =
    turns.length === 0
      ? null
      : activeTurnIndex !== null
        ? Math.min(activeTurnIndex, turns.length - 1)
        : turns.length - 1;
  const focusedTurn = focusedTurnIndex !== null ? turns[focusedTurnIndex] ?? null : null;
  const headerReq = useMemo(() => {
    if (turnJob.phase === "building") return "warming…";
    if (turnJob.phase === "running") return "running…";
    if (turnJob.phase === "timeout") return "timed out";
    if (focusedTurn) {
      const dur = fmtDuration(focusedTurn.durationSeconds);
      const n = (focusedTurnIndex ?? 0) + 1;
      return dur ? `turn ${n} · ${dur}` : `turn ${n}`;
    }
    return turns.length > 0 ? `${turns.length} turns` : "no turns yet";
  }, [turnJob.phase, focusedTurn, focusedTurnIndex, turns.length]);

  // The shared TopBar — identical on both surfaces (it hides the Chat-only
  // session actions itself when `mode !== "normal"`). The Chat config knobs live
  // in a separate `ChatConfigBar` row below it (not in the nav).
  const topBar = (
    <TopBar
      onExport={handleExport}
      onSave={() => saveMutation.mutate()}
      onNew={handleNew}
      saving={saveMutation.isPending}
      hasSession={Boolean(activeId)}
      mode={mode}
      onModeChange={setMode}
      onOpenSearch={() => setCatalogOpen(true)}
    />
  );

  // Persona Eval is a FULL-WIDTH three-column cockpit (catalog · centre ·
  // inspector); its Runs sub-view (history list / detail / compare) renders
  // full-width too. Like the Chat workbench, it's a flex column with the TopBar
  // above the surface.
  if (mode === "persona-eval") {
    return (
      <div className="flex h-screen flex-col">
        {topBar}
        {runsViewActive ? (
          <RunsView
            runId={activeRunId}
            compareWith={compareWithRunId}
            openRun={openRun}
            compareRuns={compareRuns}
            backToList={backToRunsList}
            onClose={closeRunsView}
          />
        ) : (
          <PersonaEvalCockpit
            options={optionsQuery.data ?? null}
            onOpenRuns={openRunsList}
            onDomainChange={setPevalDomain}
          />
        )}
        <CatalogDrawer
          open={catalogOpen}
          onClose={() => setCatalogOpen(false)}
          domain={pevalDomain}
        />
      </div>
    );
  }

  // Chat workbench: a flex column — TopBar, the config-knob bar, then the locked
  // three-pane row (rail · conversation · inspector).
  return (
    <div className="flex h-screen flex-col">
      {topBar}

      <ChatConfigBar
        config={config}
        options={knobs}
        environment={optionsQuery.data?.environment ?? null}
        disabled={
          !activeId ||
          patchMutation.isPending ||
          turnJob.phase === "building" ||
          turnJob.phase === "running"
        }
        onChange={handleConfigChange}
      />

      <div className="grid min-h-0 flex-1 grid-cols-[280px_minmax(0,1fr)_340px]">
        <SessionRail
          sessions={sessions}
          activeId={activeId}
          loading={sessionsQuery.isLoading}
          onSelect={handleSelectSession}
          onNew={handleNew}
          onOpenCatalog={() => setCatalogOpen(true)}
        />

        {/* Centre — manual conversation. */}
        <main className="flex min-h-0 min-w-0 flex-col bg-background">
          <div className="flex flex-shrink-0 items-center gap-2.5 border-b border-border-soft bg-surface-container-lowest px-lg py-3">
            <span className="truncate text-body-md font-semibold text-on-surface">{headerTitle}</span>
            <span className="flex-none text-body-sm text-on-surface-variant">/ conversation</span>
            <span className="ml-auto flex-none rounded-full border border-border-soft bg-surface-container-low px-3 py-1 font-mono-sm text-mono-sm text-on-surface-variant">
              {headerReq}
            </span>
          </div>

          <ChatThread
            turns={turns}
            activeTurnIndex={focusedTurnIndex}
            pendingMessage={turnJob.pendingMessage}
            phase={turnJob.phase}
            error={turnJob.error}
            userId={OPERATOR_ID}
            onSelectTurn={handleSelectTurn}
            onSelectItem={() => setCatalogOpen(true)}
            onRetry={turnJob.retry}
          />

          <Composer onSend={handleSend} phase={turnJob.phase} disabled={false} />
        </main>

        <TurnInspector turns={turns} activeIndex={focusedTurnIndex} onSelectIndex={handleSelectTurn} />
      </div>

      <CatalogDrawer
        open={catalogOpen}
        onClose={() => setCatalogOpen(false)}
        domain={config?.domain}
      />
    </div>
  );
}
