import { useCallback, useEffect, useState } from "react";

export interface UrlState {
  mode: string | null;
  session: string | null;
  turn: string | null;
  view: string | null;
  harborJob: string | null;
  harborTrial: string | null;
  /** PersonaEval cockpit task tab (chatbot | survey | web | cua). */
  peTask: string | null;
  /** Active single-run Harbor job in the cockpit (not the Runs sub-view). */
  cockpitJob: string | null;
  cockpitTrial: string | null;
  /** Active batch Harbor job in the cockpit. */
  cockpitBatch: string | null;
}

const KEYS = [
  "mode",
  "session",
  "turn",
  "view",
  "harborJob",
  "harborTrial",
  "peTask",
  "cockpitJob",
  "cockpitTrial",
  "cockpitBatch",
] as const;
const STORAGE_KEY = "personaeval.urlState";
/** Cockpit run pointers should not resurrect from storage unless the URL names them. */
const COCKPIT_RUN_KEYS = ["cockpitJob", "cockpitTrial", "cockpitBatch"] as const;
const STORAGE_MIRROR_KEYS = [
  "session",
  "turn",
  "peTask",
  "cockpitJob",
  "cockpitTrial",
  "cockpitBatch",
] as const;

function readSearch(): URLSearchParams {
  if (typeof window === "undefined") return new URLSearchParams();
  return new URLSearchParams(window.location.search);
}

function readState(): UrlState {
  const search = readSearch();
  const state = Object.fromEntries(
    KEYS.map((key) => [key, search.get(key)]),
  ) as unknown as UrlState;
  if (typeof window !== "undefined") {
    try {
      const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}") as Partial<UrlState>;
      for (const key of STORAGE_MIRROR_KEYS) {
        if ((COCKPIT_RUN_KEYS as readonly string[]).includes(key) && !search.has(key)) {
          continue;
        }
        if (!state[key]) state[key] = saved[key] ?? null;
      }
      const hasCockpitRunInUrl = COCKPIT_RUN_KEYS.some((key) => search.has(key));
      if (!hasCockpitRunInUrl) {
        const cleaned = { ...saved };
        let touched = false;
        for (const key of COCKPIT_RUN_KEYS) {
          if (cleaned[key]) {
            cleaned[key] = null;
            touched = true;
          }
        }
        if (touched) {
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cleaned));
        }
      }
    } catch {
      // Ignore corrupt localStorage payloads.
    }
  }
  return state;
}

export function useUrlState(): {
  state: UrlState;
  setState: (patch: Partial<UrlState>) => void;
} {
  const [state, setLocalState] = useState<UrlState>(() => readState());

  useEffect(() => {
    if (typeof window === "undefined") return;
    const refresh = () => setLocalState(readState());
    window.addEventListener("popstate", refresh);
    window.addEventListener("personaeval:urlstate", refresh);
    return () => {
      window.removeEventListener("popstate", refresh);
      window.removeEventListener("personaeval:urlstate", refresh);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mirror = Object.fromEntries(
      STORAGE_MIRROR_KEYS.map((key) => [key, state[key]]),
    );
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(mirror));
  }, [state]);

  const setState = useCallback((patch: Partial<UrlState>) => {
    if (typeof window === "undefined") return;
    const currentState = readState();
    const search = readSearch();
    for (const key of KEYS) {
      if (!(key in patch)) continue;
      const value = patch[key];
      if (value === null || value === undefined || value === "") search.delete(key);
      else search.set(key, value);
    }
    const nextState = { ...currentState };
    for (const key of KEYS) {
      if (!(key in patch)) continue;
      const value = patch[key];
      nextState[key] = value === null || value === undefined || value === "" ? null : value;
    }
    const mirror = Object.fromEntries(
      STORAGE_MIRROR_KEYS.map((key) => [key, nextState[key]]),
    );
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(mirror));
    const next = `${window.location.pathname}${search.toString() ? `?${search}` : ""}${window.location.hash}`;
    window.history.pushState(null, "", next);
    window.dispatchEvent(new Event("personaeval:urlstate"));
  }, []);

  return { state, setState };
}
