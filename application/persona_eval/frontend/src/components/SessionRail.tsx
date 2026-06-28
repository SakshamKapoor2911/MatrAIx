/**
 * SessionRail: the Chat workbench left navigation rail.
 *
 * Ports the PersonaEval session rail (mockup `app-redesign-v3.html:295-305`): a
 * full-width "New chat" button at the top, then the scrollable list of saved /
 * active chats from `GET /api/sessions`. The active chat carries a left primary
 * accent + a mint "live" dot; each row's sub-line condenses the honest facts an
 * operator scans: `{domain} · {n} turns · {age}`.
 *
 * Hidden below `lg` (the mockup is desktop-first); the catalog is reachable from
 * the top nav / ⌘K, so the rail stays focused on sessions.
 */
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { fmtDomain } from "./runsShared";
import type { SessionSummary } from "@/lib/types";

/** Compact relative age for a session's `createdAt` ("2m ago", "yesterday"). */
function relativeAge(iso: string | undefined): string {
  if (!iso) return "";
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "";
  const diffMs = Date.now() - then;
  const min = Math.round(diffMs / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day === 1) return "yesterday";
  if (day < 7) return `${day}d ago`;
  const wk = Math.round(day / 7);
  return `${wk}w ago`;
}

/** Compose the rail sub-line: `{domain} · {n} turns · {age}` (honest fields only). */
function subLine(s: SessionSummary): string {
  const parts: string[] = [];
  if (s.config?.domain) parts.push(fmtDomain(s.config.domain));
  parts.push(`${s.turnCount} turn${s.turnCount === 1 ? "" : "s"}`);
  const age = relativeAge(s.createdAt);
  if (age) parts.push(age);
  return parts.join(" · ");
}

export interface SessionRailProps {
  sessions: SessionSummary[];
  activeId: string | null;
  loading?: boolean;
  /** True when the sessions list failed to load. */
  error?: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  /** Delete a single chat session. */
  onDelete: (id: string) => void;
  /** Delete every saved chat session. */
  onClearAll: () => void;
  /** Re-fetch the sessions list after a load error. */
  onRetry?: () => void;
}

/** A shimmering skeleton row shown while sessions load. */
function SkeletonRow() {
  return (
    <div className="rounded-md px-3 py-2.5" aria-hidden>
      <span className="block h-3 w-3/4 animate-rb-pulse rounded bg-surface-high" />
      <span className="mt-2 block h-2.5 w-1/2 animate-rb-pulse rounded bg-surface" />
    </div>
  );
}

export function SessionRail({
  sessions,
  activeId,
  loading,
  error,
  onSelect,
  onNew,
  onDelete,
  onClearAll,
  onRetry,
}: SessionRailProps) {
  return (
    <aside className="hidden w-64 flex-shrink-0 flex-col border-r border-outline bg-surface-lowest lg:flex">
      {/* New chat */}
      <div className="flex-shrink-0 border-b border-outline p-4">
        <button
          type="button"
          onClick={onNew}
          aria-label="Start a new chat"
          className={`flex h-9 w-full items-center justify-center gap-2 rounded-md bg-primary text-[12px] font-semibold text-on-primary transition hover:bg-primary-dim active:scale-[0.98] ${FOCUS_RING}`}
        >
          <Sym name="add" size={16} />
          New chat
        </button>
      </div>

      {/* Session list */}
      <div className="custom-scrollbar min-h-0 flex-1 overflow-auto p-3">
        <div className="flex items-center justify-between px-1 pb-2">
          <span className="hud text-[9px] text-text-dim">Your chats</span>
          {sessions.length > 0 && (
            <button
              type="button"
              onClick={onClearAll}
              title="Delete every saved chat"
              className={`hud rounded text-[9px] text-text-dim transition hover:text-danger ${FOCUS_RING}`}
            >
              Clear all
            </button>
          )}
        </div>

        {error ? (
          <div className="rounded-md border border-warn/30 bg-warn/10 p-3">
            <div className="flex items-start gap-2">
              <Sym name="error" fill={1} size={16} className="mt-px flex-none text-warn" />
              <div className="min-w-0">
                <div className="text-[12px] font-medium text-text-main">Couldn&apos;t load your chats</div>
                <p className="mt-0.5 text-[11px] leading-relaxed text-text-variant">The backend may be starting up.</p>
              </div>
            </div>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className={`mt-2.5 inline-flex items-center gap-1.5 rounded-md border border-warn/40 bg-warn/10 px-3 py-1.5 text-[11px] font-medium text-warn transition hover:bg-warn/20 active:scale-[0.98] ${FOCUS_RING}`}
              >
                <Sym name="refresh" size={14} />
                Recheck
              </button>
            )}
          </div>
        ) : loading && sessions.length === 0 ? (
          <div className="space-y-1">
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </div>
        ) : sessions.length === 0 ? (
          <div className="px-1 py-2 text-[12px] leading-relaxed text-text-variant">
            No chats yet. Start one to try the recommender. You&apos;ll play the user and RecAI replies.
          </div>
        ) : (
          <div className="space-y-1">
            {sessions.map((s, i) => {
              const active = s.id === activeId;
              return (
                <div
                  key={s.id}
                  className="rise-in group relative"
                  style={{ animationDelay: `${Math.min(i, 6) * 30}ms` }}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(s.id)}
                    aria-current={active ? "true" : undefined}
                    className={`block w-full rounded-md border-l-2 px-3 py-2.5 pr-9 text-left transition-colors ${FOCUS_RING} ${
                      active
                        ? "border-primary bg-primary/5"
                        : "border-transparent hover:bg-surface active:bg-surface-low"
                    }`}
                  >
                    <div
                      className={`truncate text-[13px] ${active ? "font-medium text-text-main" : "text-text-variant"}`}
                      title={s.title || "Untitled chat"}
                    >
                      {s.title || "Untitled chat"}
                    </div>
                    <div
                      className="hud mt-1 flex items-start gap-1.5 text-[9px] text-text-dim"
                      title={`Ranker: ${s.config?.rankerMode ?? "not set"} · Model: ${s.config?.engine ?? "not set"}. Change these in the bar above`}
                    >
                      {active && <span className="mt-px h-1.5 w-1.5 flex-none rounded-full bg-secondary" aria-hidden />}
                      <span className="min-w-0 break-words">{subLine(s)}</span>
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(s.id)}
                    aria-label={`Delete chat: ${s.title || "Untitled chat"}`}
                    title="Delete chat"
                    className={`absolute right-1.5 top-1.5 grid h-6 w-6 place-items-center rounded text-text-dim opacity-0 transition hover:bg-danger/10 hover:text-danger focus:opacity-100 group-hover:opacity-100 ${FOCUS_RING}`}
                  >
                    <Sym name="delete" size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}
