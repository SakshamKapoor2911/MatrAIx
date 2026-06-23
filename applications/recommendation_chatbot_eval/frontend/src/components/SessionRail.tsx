/**
 * SessionRail — the Chat workbench left navigation rail.
 *
 * Lists every saved/active session (from `GET /api/sessions`) with the active
 * one highlighted, an "add" affordance in the header, and a footer with the
 * Catalog (⌘K) and "All sessions" nav items. Styled to the Executive Precision
 * tokens, mirroring the cockpit's persona catalog register.
 *
 * The per-session sub-line condenses the two config knobs an operator scans for
 * (ranker + engine), e.g. "native · 4o-mini".
 */
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import type { SessionConfig, SessionSummary } from "@/lib/types";

/** Short, human engine label for the rail sub-line ("gpt-4o-mini" → "4o-mini"). */
function shortEngine(engine: string | undefined): string {
  if (!engine) return "";
  return engine.replace(/^gpt-/, "");
}

/** Compose the grey sub-line under a session title. */
function subLine(config: Partial<SessionConfig> | undefined): string {
  if (!config) return "";
  const parts: string[] = [];
  if (config.rankerMode) parts.push(config.rankerMode);
  const eng = shortEngine(config.engine);
  if (eng) parts.push(eng);
  return parts.join(" · ");
}

export interface SessionRailProps {
  sessions: SessionSummary[];
  activeId: string | null;
  loading?: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onOpenCatalog: () => void;
}

/** A shimmering skeleton row shown while sessions load. */
function SkeletonRow() {
  return (
    <div className="flex items-center gap-2.5 rounded-md px-2.5 py-2" aria-hidden>
      <span className="h-4 w-4 flex-none animate-rb-pulse rounded bg-surface-container-high" />
      <span className="min-w-0 flex-1 space-y-1.5">
        <span className="block h-3 w-3/4 animate-rb-pulse rounded bg-surface-container-high" />
        <span className="block h-2.5 w-1/2 animate-rb-pulse rounded bg-surface-container" />
      </span>
    </div>
  );
}

export function SessionRail({
  sessions,
  activeId,
  loading,
  onSelect,
  onNew,
  onOpenCatalog,
}: SessionRailProps) {
  return (
    <aside className="flex min-h-0 flex-col border-r border-border-soft bg-surface-container-low">
      {/* Header */}
      <div className="flex flex-shrink-0 items-center justify-between px-md pb-2 pt-md">
        <h2 className="text-headline-sm font-headline-sm uppercase tracking-wider text-on-surface">Sessions</h2>
        <button
          type="button"
          onClick={onNew}
          aria-label="New session"
          title="New session"
          className={`flex h-6 w-6 items-center justify-center rounded-md border border-outline-variant bg-surface-container-lowest text-on-surface-variant transition-colors hover:border-primary hover:text-primary ${FOCUS_RING}`}
        >
          <Sym name="add" size={16} />
        </button>
      </div>

      {/* Session list */}
      <div className="custom-scrollbar min-h-0 flex-1 space-y-0.5 overflow-auto px-2 py-0.5">
        {loading && sessions.length === 0 ? (
          <>
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </>
        ) : sessions.length === 0 ? (
          <div className="px-2.5 py-3 text-body-sm leading-relaxed text-on-surface-variant">
            No sessions yet. Create one to start a conversation with the recommender.
          </div>
        ) : (
          sessions.map((s) => {
            const active = s.id === activeId;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => onSelect(s.id)}
                aria-current={active ? "true" : undefined}
                className={`flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors ${FOCUS_RING} ${
                  active
                    ? "bg-primary/10 text-on-surface"
                    : "text-on-surface-variant hover:bg-surface-container"
                }`}
              >
                <Sym
                  name="forum"
                  fill={active ? 1 : 0}
                  size={16}
                  className={`flex-none ${active ? "text-primary" : "text-outline"}`}
                />
                <div className="min-w-0 flex-1">
                  <div className={`truncate text-body-md ${active ? "font-semibold text-on-surface" : "font-medium"}`}>
                    {s.title || "Untitled session"}
                  </div>
                  <div className="truncate text-label-md font-label-md text-on-surface-variant">{subLine(s.config)}</div>
                </div>
                <div className="font-mono-sm text-mono-sm tabular-nums text-on-surface-variant">{s.turnCount}</div>
              </button>
            );
          })
        )}
      </div>

      {/* Footer nav */}
      <div className="flex-shrink-0 border-t border-border-soft px-2 py-2">
        <button
          type="button"
          onClick={onOpenCatalog}
          className={`flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-body-md font-medium text-on-surface-variant transition-colors hover:bg-surface-container ${FOCUS_RING}`}
        >
          <Sym name="search" size={16} className="text-outline" />
          Catalog
          <kbd className="ml-auto rounded border border-outline-variant bg-surface-container-lowest px-1.5 py-px font-mono-sm text-[11px] text-on-surface-variant">
            ⌘K
          </kbd>
        </button>
        <button
          type="button"
          onClick={onNew}
          className={`flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-body-md font-medium text-on-surface-variant transition-colors hover:bg-surface-container ${FOCUS_RING}`}
        >
          <Sym name="format_list_bulleted" size={16} className="text-outline" />
          New session
        </button>
      </div>
    </aside>
  );
}
