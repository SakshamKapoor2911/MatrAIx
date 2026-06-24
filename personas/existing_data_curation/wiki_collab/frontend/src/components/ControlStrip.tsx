/**
 * The workflow action bar. Buttons in lifecycle order — Package, Run, Return,
 * Audit, Merge — plus a subtle Reset. Each shows its own spinner while in
 * flight (driven by `useAction`'s per-action mutations) and surfaces an
 * `ApiError` message inline so failures stay in context.
 */
import { useState } from "react";

import { Sym } from "@/components/cockpit/cockpitShared";
import { Chip, Spinner } from "@/components/cockpit/Primitives";
import { useAction } from "@/lib/hooks";
import type { ActionKey } from "@/lib/hooks";
import { ApiError } from "@/lib/api";
import type { AppState } from "@/lib/types";

type BackendName = "mock" | "claude-code-acp" | "codex-acp";

const BACKENDS: { value: BackendName; label: string }[] = [
  { value: "mock", label: "Mock" },
  { value: "claude-code-acp", label: "Claude Code (ACP)" },
  { value: "codex-acp", label: "Codex (ACP)" },
];

const EFFORTS = ["low", "medium", "high"] as const;

function errorMessage(err: unknown): string | null {
  if (!err) return null;
  if (err instanceof ApiError) return err.status ? `${err.status}: ${err.message}` : err.message;
  if (err instanceof Error) return err.message;
  return "Action failed";
}

function ActionButton({
  label,
  icon,
  tone = "neutral",
  pending,
  disabled,
  onClick,
}: {
  label: string;
  icon: string;
  tone?: "primary" | "neutral" | "ghost";
  pending: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const base =
    "inline-flex items-center gap-xs rounded-lg px-3 py-2 font-body-md transition-colors disabled:cursor-not-allowed disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface-container-lowest";
  const tones: Record<string, string> = {
    primary: "bg-primary text-on-primary hover:bg-primary-container",
    neutral: "border border-border-soft bg-surface-container-lowest text-on-surface hover:bg-surface-container-low",
    ghost: "text-on-surface-variant hover:bg-surface-container-low",
  };
  return (
    <button type="button" disabled={disabled} onClick={onClick} className={`${base} ${tones[tone]}`}>
      {pending ? <Spinner size={16} /> : <Sym name={icon} size={18} />}
      {label}
    </button>
  );
}

export function ControlStrip({ state }: { state: AppState }) {
  const actions = useAction();
  const busy = actions.pendingKey !== null;

  const [workerId, setWorkerId] = useState("local-claude-demo");
  const [rangeStart, setRangeStart] = useState(0);
  const [rangeEnd, setRangeEnd] = useState(1);
  const [backend, setBackend] = useState<BackendName>("mock");
  const [effort, setEffort] = useState<(typeof EFFORTS)[number]>("high");
  const [concurrency, setConcurrency] = useState(1);

  const hasAssignment = state.assignment !== null;
  const hasRun = state.files.last_run_archive !== null;
  const hasReturn = state.files.last_returned_archive !== null;
  const hasAudit = state.files.audit_report !== null;

  const isPending = (key: ActionKey) => actions.pendingKey === key;

  const firstError =
    errorMessage(actions.package.error) ??
    errorMessage(actions.run.error) ??
    errorMessage(actions.return.error) ??
    errorMessage(actions.audit.error) ??
    errorMessage(actions.merge.error) ??
    errorMessage(actions.reset.error);

  const fieldCls =
    "rounded-md border border-border-soft bg-surface-container-lowest px-2 py-1 font-mono-sm text-on-surface outline-none focus-visible:ring-2 focus-visible:ring-primary";

  return (
    <div className="flex flex-col gap-sm border-b border-border-soft bg-surface-container-low px-md py-sm">
      <div className="flex flex-wrap items-center gap-md">
        {/* Package inputs + action */}
        <div className="flex items-center gap-xs">
          <label className="font-label-md text-on-surface-variant">worker</label>
          <input
            value={workerId}
            onChange={(e) => setWorkerId(e.target.value)}
            className={`${fieldCls} w-40`}
            spellCheck={false}
          />
          <input
            type="number"
            value={rangeStart}
            min={0}
            onChange={(e) => setRangeStart(Number(e.target.value))}
            className={`${fieldCls} w-16 tabular-nums`}
            aria-label="range start"
          />
          <span className="font-mono-sm text-outline">→</span>
          <input
            type="number"
            value={rangeEnd}
            min={0}
            onChange={(e) => setRangeEnd(Number(e.target.value))}
            className={`${fieldCls} w-16 tabular-nums`}
            aria-label="range end"
          />
          <ActionButton
            label="Package"
            icon="inventory_2"
            tone="primary"
            pending={isPending("package")}
            disabled={busy}
            onClick={() =>
              actions.package.mutate({
                worker_id: workerId,
                range_start: rangeStart,
                range_end: rangeEnd,
              })
            }
          />
        </div>

        {/* Run inputs + action */}
        <div className="flex items-center gap-xs">
          <select
            value={backend}
            onChange={(e) => setBackend(e.target.value as BackendName)}
            className={`${fieldCls}`}
            aria-label="backend"
          >
            {BACKENDS.map((b) => (
              <option key={b.value} value={b.value}>
                {b.label}
              </option>
            ))}
          </select>
          <select
            value={effort}
            onChange={(e) => setEffort(e.target.value as (typeof EFFORTS)[number])}
            className={`${fieldCls}`}
            aria-label="effort"
          >
            {EFFORTS.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
          <input
            type="number"
            value={concurrency}
            min={1}
            onChange={(e) => setConcurrency(Math.max(1, Number(e.target.value)))}
            className={`${fieldCls} w-14 tabular-nums`}
            aria-label="concurrency"
            title="concurrency"
          />
          <ActionButton
            label="Run"
            icon="play_arrow"
            tone="primary"
            pending={isPending("run")}
            disabled={busy || !hasAssignment}
            onClick={() =>
              actions.run.mutate({
                backend_name: backend,
                effort,
                concurrency,
              })
            }
          />
        </div>

        <div className="flex items-center gap-xs">
          <ActionButton
            label="Return"
            icon="outbox"
            pending={isPending("return")}
            disabled={busy || !hasRun}
            onClick={() => actions.return.mutate()}
          />
          <ActionButton
            label="Audit"
            icon="fact_check"
            pending={isPending("audit")}
            disabled={busy || !hasReturn}
            onClick={() => actions.audit.mutate()}
          />
          <ActionButton
            label="Merge"
            icon="merge"
            pending={isPending("merge")}
            disabled={busy || !hasAudit}
            onClick={() => actions.merge.mutate()}
          />
        </div>

        <div className="ml-auto">
          <ActionButton
            label="Reset"
            icon="restart_alt"
            tone="ghost"
            pending={isPending("reset")}
            disabled={busy}
            onClick={() => actions.reset.mutate()}
          />
        </div>
      </div>

      {firstError ? (
        <div className="flex items-center gap-xs">
          <Chip tone="error" title={firstError}>
            <Sym name="error" size={14} />
            {firstError}
          </Chip>
        </div>
      ) : null}
    </div>
  );
}
