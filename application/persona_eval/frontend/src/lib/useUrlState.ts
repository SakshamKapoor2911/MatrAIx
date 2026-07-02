import { useCallback, useEffect, useState } from "react";

export interface UrlState {
  mode: string | null;
  session: string | null;
  turn: string | null;
  view: string | null;
  harborJob: string | null;
  harborTrial: string | null;
}

const KEYS = ["mode", "session", "turn", "view", "harborJob", "harborTrial"] as const;
const STORAGE_KEY = "personaeval.urlState";

function readSearch(): URLSearchParams {
  if (typeof window === "undefined") return new URLSearchParams();
  return new URLSearchParams(window.location.search);
}

function readState(): UrlState {
  const search = readSearch();
  const state = Object.fromEntries(
    KEYS.map((key) => [key, search.get(key)]),
  ) as unknown as UrlState;
  if (typeof window !== "undefined" && !state.session) {
    try {
      const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}") as Partial<UrlState>;
      state.session = saved.session ?? null;
      state.turn = state.turn ?? saved.turn ?? null;
    } catch {
      state.session = null;
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
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ session: state.session, turn: state.turn }),
    );
  }, [state.session, state.turn]);

  const setState = useCallback((patch: Partial<UrlState>) => {
    if (typeof window === "undefined") return;
    const search = readSearch();
    for (const key of KEYS) {
      if (!(key in patch)) continue;
      const value = patch[key];
      if (value === null || value === undefined || value === "") search.delete(key);
      else search.set(key, value);
    }
    const next = `${window.location.pathname}${search.toString() ? `?${search}` : ""}${window.location.hash}`;
    window.history.pushState(null, "", next);
    window.dispatchEvent(new Event("personaeval:urlstate"));
  }, []);

  return { state, setState };
}
