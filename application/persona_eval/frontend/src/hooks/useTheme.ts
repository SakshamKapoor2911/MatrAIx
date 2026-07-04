/**
 * Light/dark theme toggle for PersonaEval.
 *
 * Light is the default; dark is opt-in via localStorage `personaeval-theme=dark`.
 * The `light` class on <html> selects the light token ramp. The class is set
 * class is set BEFORE paint by the boot script in index.html (to avoid a flash),
 * so this hook reads the live DOM class as its source of truth and persists the
 * operator's choice to localStorage. UI-state only, touches nothing in the
 * data layer.
 */
import { useCallback, useState } from "react";

const KEY = "personaeval-theme";
export type Theme = "dark" | "light";

function current(): Theme {
  return document.documentElement.classList.contains("light") ? "light" : "dark";
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(current);
  const toggle = useCallback(() => {
    const next: Theme = current() === "light" ? "dark" : "light";
    document.documentElement.classList.toggle("light", next === "light");
    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* private mode / storage disabled, fall back to in-memory only */
    }
    setTheme(next);
  }, []);
  return { theme, toggle };
}
