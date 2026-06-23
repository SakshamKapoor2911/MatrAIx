/**
 * `useUrlState` — the single source of truth for the cross-pane view state that
 * should survive a refresh and be shareable by link.
 *
 * The Studio's coarse navigation — which `mode` is active, which `session` is
 * open, which `turn` is focused, and which persisted `run` is being inspected —
 * lives in the URL's query string (via `history.replaceState`, so it never adds
 * history entries) with a `localStorage` mirror. On a cold load with an empty
 * query string the mirror is restored, so reopening the app lands you back where
 * you left off; a link with explicit params always wins over the mirror.
 *
 * The hook returns the parsed state plus a `setState` that accepts a partial
 * patch. Writing `null`/`undefined` for a key drops it from the URL. All writes
 * go through one place so the URL, the mirror, and React state stay in lockstep.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

/** The view state we persist to the URL + localStorage. */
export interface UrlState {
  /** Active workbench mode (manual chat vs. persona-driven persona eval). */
  mode: string | null;
  /**
   * The sub-view within Persona Eval. `"runs"` opens the Runs history (folded
   * inside Persona Eval); anything else (null) shows the cockpit. A `run` /
   * `compareWith` selection implies the runs sub-view too.
   */
  view: string | null;
  /** Active session id (manual chat). */
  session: string | null;
  /** Focused turn index, as a string in the URL; `null` = follow latest. */
  turn: string | null;
  /** Persisted persona-eval run id being inspected. */
  run: string | null;
  /** Second run id to compare against (Runs compare view); `null` = no compare. */
  compareWith: string | null;
}

/** The keys we round-trip, in a stable order for a tidy query string. */
const KEYS = ["mode", "view", "session", "turn", "run", "compareWith"] as const;
type UrlKey = (typeof KEYS)[number];

/** localStorage key for the state mirror. */
const STORAGE_KEY = "recbot.urlstate";

const EMPTY: UrlState = {
  mode: null,
  view: null,
  session: null,
  turn: null,
  run: null,
  compareWith: null,
};

/** Read the current `window.location.search` into a `UrlState`. */
function readFromLocation(): UrlState {
  if (typeof window === "undefined") return { ...EMPTY };
  const params = new URLSearchParams(window.location.search);
  const out: UrlState = { ...EMPTY };
  for (const key of KEYS) {
    const value = params.get(key);
    if (value !== null && value !== "") out[key] = value;
  }
  return out;
}

/** Read the persisted mirror from localStorage (best-effort). */
function readFromStorage(): UrlState {
  if (typeof window === "undefined") return { ...EMPTY };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY };
    const parsed = JSON.parse(raw) as Partial<Record<UrlKey, unknown>>;
    const out: UrlState = { ...EMPTY };
    for (const key of KEYS) {
      const value = parsed[key];
      if (typeof value === "string" && value !== "") out[key] = value;
    }
    return out;
  } catch {
    return { ...EMPTY };
  }
}

/** True when none of the tracked keys are set. */
function isEmpty(state: UrlState): boolean {
  return KEYS.every((key) => state[key] === null);
}

/** Serialize a `UrlState` into a query string (without the leading `?`). */
function toSearch(state: UrlState): string {
  const params = new URLSearchParams();
  for (const key of KEYS) {
    const value = state[key];
    if (value !== null && value !== "") params.set(key, value);
  }
  return params.toString();
}

/** Persist the state to the URL (replaceState) and the localStorage mirror. */
function persist(state: UrlState): void {
  if (typeof window === "undefined") return;
  const search = toSearch(state);
  const url = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
  window.history.replaceState(window.history.state, "", url);
  try {
    if (isEmpty(state)) {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
  } catch {
    /* storage unavailable (private mode / quota) — URL still works */
  }
}

export interface UseUrlStateResult {
  /** The current view state, derived from the URL (+ restored mirror). */
  state: UrlState;
  /** Patch one or more keys; `null`/`undefined` drops the key from the URL. */
  setState: (patch: Partial<Record<UrlKey, string | null | undefined>>) => void;
}

/**
 * Drive view state from the URL with a localStorage fallback.
 *
 * On mount: if the query string carries any tracked key, it wins; otherwise the
 * localStorage mirror is restored (and reflected back into the URL). Thereafter
 * `setState` is the only writer.
 */
export function useUrlState(): UseUrlStateResult {
  // Resolve the initial state once: URL wins, else the mirror.
  const [state, setStateRaw] = useState<UrlState>(() => {
    const fromUrl = readFromLocation();
    return isEmpty(fromUrl) ? readFromStorage() : fromUrl;
  });

  // Reflect the resolved initial state back into the URL exactly once, so a cold
  // load restored from the mirror gets a shareable URL immediately.
  const didInit = useRef(false);
  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;
    persist(state);
    // Run once on mount with the resolved initial state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep in sync with browser back/forward (history navigation).
  useEffect(() => {
    function onPop() {
      setStateRaw(readFromLocation());
    }
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const setState = useCallback(
    (patch: Partial<Record<UrlKey, string | null | undefined>>) => {
      setStateRaw((prev) => {
        const next: UrlState = { ...prev };
        let changed = false;
        for (const key of KEYS) {
          if (!(key in patch)) continue;
          const value = patch[key];
          const normalized = value === undefined || value === "" ? null : value;
          if (next[key] !== normalized) {
            next[key] = normalized;
            changed = true;
          }
        }
        if (!changed) return prev;
        persist(next);
        return next;
      });
    },
    [],
  );

  return useMemo(() => ({ state, setState }), [state, setState]);
}
