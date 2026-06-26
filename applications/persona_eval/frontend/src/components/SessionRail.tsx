/**
 * SessionRail — the Chat workbench left navigation rail.
 *
 * Lists every saved/active chat (from `GET /api/sessions`) with the active one
 * highlighted by a left accent, an "add" affordance in the header, and a footer
 * with the Catalog (⌘K) and New-chat nav items. Styled to the matrAIx tokens,
 * mirroring the cockpit's persona catalog register.
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
      <span className="h-4 w-4 flex-none animate-rb-pulse rounded bg-surface-high" />
      <span className="min-w-0 flex-1 space-y-1.5">
        <span className="block h-3 w-3/4 animate-rb-pulse rounded bg-surface-high" />
        <span className="block h-2.5 w-1/2 animate-rb-pulse rounded bg-surface" />
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
    <aside className="flex min-h-0 flex-col border-r border-outline bg-surface-lowest">
      {/* Header */}
      <div className="flex flex-shrink-0 items-center justify-between px-md pb-2 pt-md">
        <h2 className="hud text-[9px] text-text-dim">Your chats</h2>
        <button
          type="button"
          onClick={onNew}
          aria-label="Start a new chat"
          title="Start a new chat"
          className={`flex h-6 w-6 items-center justify-center rounded-md border border-outline bg-surface-low text-text-variant transition-colors hover:border-primary hover:text-primary ${FOCUS_RING}`}
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
          <div className="px-2.5 py-3 text-[12px] leading-relaxed text-text-variant">
            No chats yet. Start one to try the recommender — you&apos;ll play the user and RecAI replies.
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
                className={`flex w-full items-center gap-2.5 rounded-md border-l-2 px-2.5 py-2 text-left transition-colors ${FOCUS_RING} ${
                  active
                    ? "border-primary bg-primary/5 text-text-main"
                    : "border-transparent text-text-variant hover:bg-surface"
                }`}
              >
                <Sym
                  name="forum"
                  fill={active ? 1 : 0}
                  size={16}
                  className={`flex-none ${active ? "text-primary" : "text-text-dim"}`}
                />
                <div className="min-w-0 flex-1">
                  <div className={`truncate text-[13px] ${active ? "font-semibold text-text-main" : "font-medium"}`}>
                    {s.title || "Untitled chat"}
                  </div>
                  <div
                    className="hud truncate text-[9px] text-text-dim"
                    title={`Ranker: ${s.config?.rankerMode ?? "—"} · Model: ${s.config?.engine ?? "—"} — change these in the bar above`}
                  >
                    {subLine(s.config)}
                  </div>
                </div>
                <div className="font-mono text-[11px] tabular-nums text-text-dim">{s.turnCount}</div>
              </button>
            );
          })
        )}
      </div>

      {/* Footer nav */}
      <div className="flex-shrink-0 border-t border-outline px-2 py-2">
        <button
          type="button"
          onClick={onOpenCatalog}
          className={`flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] font-medium text-text-variant transition-colors hover:bg-surface ${FOCUS_RING}`}
        >
          <Sym name="search" size={16} className="text-text-dim" />
          Browse catalog
          <kbd className="ml-auto rounded border border-outline bg-surface px-1.5 py-px font-mono text-[10px] text-text-variant">
            ⌘K
          </kbd>
        </button>
        <button
          type="button"
          onClick={onNew}
          className={`flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] font-medium text-text-variant transition-colors hover:bg-surface ${FOCUS_RING}`}
        >
          <Sym name="format_list_bulleted" size={16} className="text-text-dim" />
          New chat
        </button>
      </div>
    </aside>
  );
}
