import { formatBatchCellStatusLabel } from "@/lib/trialStatus";
import { personaDisplayId, personaPrimaryName } from "@/lib/personaDisplay";
import type { PersonaPoolPersonaCard } from "@/lib/types";

import { PersonaAvatar } from "./PersonaAvatar";
import { useBatchGridLayout } from "./useBatchGridLayout";

export type BatchTrialStatus = "pending" | "running" | "done" | "error";

export interface BatchTrialPersonaMeta {
  personaId: string;
  name?: string;
  source?: string;
  dimensions: Record<string, string>;
}

export interface BatchTrialCell {
  id: string;
  label: string;
  status: BatchTrialStatus;
  statusLabel?: string;
  persona?: BatchTrialPersonaMeta;
}

const STATUS_STYLES: Record<
  BatchTrialStatus,
  { ring: string; dot: string; glow?: string; wash: string }
> = {
  pending: {
    ring: "border-outline/30",
    dot: "bg-text-dim/55",
    wash: "from-surface-high/40 to-surface/20",
  },
  running: {
    ring: "border-amber-400/40",
    dot: "bg-amber-400 animate-pulse",
    glow: "shadow-[0_8px_24px_-12px_rgb(251_191_36/0.35)]",
    wash: "from-amber-400/[0.07] to-surface/30",
  },
  done: {
    ring: "border-secondary/30",
    dot: "bg-secondary",
    wash: "from-secondary/[0.06] to-surface/30",
  },
  error: {
    ring: "border-danger/35",
    dot: "bg-danger",
    glow: "shadow-[0_8px_24px_-12px_rgb(var(--danger)/0.25)]",
    wash: "from-danger/[0.06] to-surface/30",
  },
};

export interface BatchTrialGridProps {
  trials: BatchTrialCell[];
  jobLabel?: string;
  className?: string;
}

function statusBadgeLabel(trial: BatchTrialCell): string {
  return (
    trial.statusLabel ??
    formatBatchCellStatusLabel(trial.status, null, null)
  );
}

function statusLineClass(status: BatchTrialStatus): string {
  if (status === "error") return "text-danger";
  if (status === "running") return "text-amber-600";
  if (status === "done") return "text-secondary";
  return "text-text-variant";
}

function BatchTrialCellView({
  trial,
  rowHeight,
}: {
  trial: BatchTrialCell;
  rowHeight: number;
}) {
  const style = STATUS_STYLES[trial.status];
  const dimensions = trial.persona?.dimensions ?? {};
  const rawPersonaId = (trial.persona?.personaId ?? trial.label.replace(/^persona[-_]?/i, "")).trim();
  const personaId = personaDisplayId(rawPersonaId || null);
  const statusLabel = statusBadgeLabel(trial);
  const displayName = personaPrimaryName(trial.persona?.name, rawPersonaId, dimensions) || trial.label || personaId;
  const avatarMuted = trial.status === "pending";
  const portrait = rowHeight >= 96;

  const avatarFrame = (
    <PersonaAvatar
      personaId={rawPersonaId || trial.id}
      dimensions={dimensions}
      size={portrait ? "lg" : "sm"}
      muted={avatarMuted}
      className={trial.status === "running" ? "animate-[pulse_2.8s_ease-in-out_infinite]" : ""}
    />
  );

  return (
    <article
      className={`group relative flex h-full min-h-0 overflow-hidden rounded-2xl border bg-gradient-to-b ${style.ring} ${style.wash} ${style.glow ?? "shadow-sm"} ${
        portrait
          ? "flex-col items-center justify-center gap-2.5 px-3 py-3"
          : "items-center gap-3 px-3 py-2.5"
      }`}
      title={`${displayName} · ${personaId} · ${statusLabel}`}
    >
      <span
        className={`absolute right-2.5 top-2.5 z-10 h-2 w-2 rounded-full ring-2 ring-surface/80 ${style.dot}`}
        aria-label={statusLabel}
      />

      {avatarFrame}

      <div
        className={`min-w-0 ${portrait ? "w-full space-y-1 text-center" : "flex-1 space-y-0.5 pr-4"}`}
      >
        <p
          className={`truncate font-display font-semibold leading-snug text-text-main ${
            portrait ? "text-[12px] px-1" : "text-[11px]"
          }`}
        >
          {displayName}
        </p>
        <p className="truncate font-mono text-[9px] tracking-wide text-text-dim">
          {personaId}
        </p>
        <p
          className={`truncate font-medium ${statusLineClass(trial.status)} ${
            portrait ? "text-[11px] px-1" : "text-[10px]"
          }`}
        >
          {statusLabel}
        </p>
      </div>
    </article>
  );
}

function CohortStat({
  tone,
  label,
  pulse,
}: {
  tone: "dim" | "amber" | "secondary" | "danger";
  label: string;
  pulse?: boolean;
}) {
  const dot =
    tone === "amber"
      ? "bg-amber-400"
      : tone === "secondary"
        ? "bg-secondary"
        : tone === "danger"
          ? "bg-danger"
          : "bg-text-dim/50";
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-outline/35 bg-surface/80 px-2 py-0.5 text-[10px] text-text-variant">
      <span className={`h-1.5 w-1.5 rounded-full ${dot} ${pulse ? "animate-pulse" : ""}`} />
      {label}
    </span>
  );
}

/** Adaptive roster grid — cells grow to fill the stage; scrolls when cohort is large. */
export function BatchTrialGrid({ trials, jobLabel, className = "" }: BatchTrialGridProps) {
  const done = trials.filter((t) => t.status === "done").length;
  const running = trials.filter((t) => t.status === "running").length;
  const pending = trials.filter((t) => t.status === "pending").length;
  const failed = trials.filter((t) => t.status === "error").length;
  const { setContainer, layout } = useBatchGridLayout(trials.length);

  return (
    <div className={`flex h-full min-h-0 w-full flex-col overflow-hidden ${className}`}>
      <header className="mb-2 shrink-0 space-y-1 border-b border-outline/25 pb-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="hud text-[10px] text-primary">Simulated cohort</p>
            <p className="font-display text-[15px] font-bold tracking-tight text-text-main">
              {trials.length} {trials.length === 1 ? "person" : "people"}
            </p>
          </div>
          <div className="flex flex-wrap justify-end gap-1">
            {pending > 0 && <CohortStat tone="dim" label={`${pending} waiting`} />}
            {running > 0 && <CohortStat tone="amber" label={`${running} active`} pulse />}
            {done > 0 && <CohortStat tone="secondary" label={`${done} finished`} />}
            {failed > 0 && <CohortStat tone="danger" label={`${failed} failed`} />}
          </div>
        </div>
        {jobLabel ? (
          <p className="truncate font-mono text-[10px] text-text-dim" title={jobLabel}>
            {jobLabel}
          </p>
        ) : null}
      </header>

      <div
        ref={setContainer}
        className={`min-h-0 flex-1 ${layout.scroll ? "overflow-y-auto overflow-x-hidden pr-0.5" : "overflow-hidden"}`}
      >
        <div
          className="grid w-full gap-2.5"
          style={{
            height: layout.scroll ? undefined : "100%",
            gridTemplateColumns: `repeat(${layout.cols}, minmax(0, 1fr))`,
            gridTemplateRows: layout.scroll
              ? `repeat(${layout.rows}, ${layout.rowHeight}px)`
              : `repeat(${layout.rows}, minmax(0, 1fr))`,
            alignContent: layout.scroll ? "start" : "stretch",
          }}
        >
          {trials.map((trial) => (
            <BatchTrialCellView key={trial.id} trial={trial} rowHeight={layout.rowHeight} />
          ))}
        </div>
      </div>
    </div>
  );
}

type HarborTrialRow = {
  trialName: string;
  personaId?: string | null;
  personaName?: string | null;
  completed?: boolean;
  succeeded?: boolean | null;
  error?: string | null;
  phase?: string | null;
  stage?: string | null;
};

type BatchGridSlot = {
  personaId: string;
  label: string;
  trial?: HarborTrialRow;
};

function personaMetaFromCard(card: PersonaPoolPersonaCard | undefined): BatchTrialPersonaMeta | undefined {
  if (!card) return undefined;
  return {
    personaId: card.personaId,
    name: card.name,
    source: card.source,
    dimensions: card.dimensions ?? {},
  };
}

function resolveBatchGridSlots(
  personaIds: string[],
  harborTrials: HarborTrialRow[] | undefined,
): BatchGridSlot[] {
  if (personaIds.length > 0) {
    return personaIds.map((personaId, index) => ({
      personaId,
      label: `persona-${personaId}`,
      trial: harborTrials?.[index],
    }));
  }
  return (harborTrials ?? []).map((trial) => ({
    personaId: trial.personaId ?? trial.trialName,
    label:
      trial.personaName ??
      (trial.personaId ? `persona-${trial.personaId}` : trial.trialName),
    trial,
  }));
}

/** One grid cell per persona — all slots visible from job start. */
export function buildBatchGridCells(
  personaIds: string[],
  harborTrials: HarborTrialRow[] | undefined,
  opts: {
    jobStarted?: boolean;
    parallelTrials?: number;
    personaById?: Record<string, PersonaPoolPersonaCard>;
  } = {},
): BatchTrialCell[] {
  const { jobStarted = false, parallelTrials = 1, personaById = {} } = opts;
  const slots = resolveBatchGridSlots(personaIds, harborTrials);
  if (slots.length === 0) return [];

  const completedCount = harborTrials?.filter((trial) => trial.completed).length ?? 0;

  return slots.map((slot, index) => {
    const trial = slot.trial;
    let status: BatchTrialStatus = "pending";

    if (trial?.completed) {
      status = trial.succeeded === false || trial.error ? "error" : "done";
    } else if (!jobStarted) {
      status = "pending";
    } else if (index >= completedCount && index < completedCount + parallelTrials) {
      status = "running";
    }

    const card = personaById[slot.personaId];
    const persona = personaMetaFromCard(card);

    return {
      id: trial?.trialName ?? `persona-${slot.personaId}`,
      label: persona?.name ?? card?.name ?? slot.label,
      status,
      persona,
      statusLabel: formatBatchCellStatusLabel(
        status,
        trial?.stage ?? (status === "running" ? "starting_env" : null),
        trial?.phase,
      ),
    };
  });
}

/** @deprecated Use buildBatchGridCells — keeps old call sites working. */
export function harborTrialsToGridCells(
  trials: HarborTrialRow[],
  personaIds?: string[],
  jobStarted = true,
): BatchTrialCell[] {
  const ids =
    personaIds && personaIds.length >= trials.length
      ? personaIds
      : trials.map((trial, index) => personaIds?.[index] ?? trial.trialName);
  return buildBatchGridCells(ids, trials, { jobStarted, parallelTrials: trials.length });
}
