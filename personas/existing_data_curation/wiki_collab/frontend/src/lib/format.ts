/**
 * Pure formatting + small browser helpers for the cockpit.
 *
 * No React, no side effects beyond the best-effort clipboard write — so these
 * stay trivially testable and reusable across every panel.
 */

/** First `n` chars of a sha/id (mono-friendly), or an em-dash when absent. */
export function shortSha(s: string | null | undefined, n = 10): string {
  if (!s) return "—";
  const trimmed = s.trim();
  if (!trimmed) return "—";
  return trimmed.slice(0, n);
}

/** Locale-grouped integer (`12,345`), or an em-dash when null/undefined/NaN. */
export function fmtInt(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString();
}

/** A 0..100 percentage of `part / whole`, guarding division by zero. */
export function pct(part: number, whole: number): number {
  if (!whole || whole <= 0 || Number.isNaN(whole)) return 0;
  const ratio = (part / whole) * 100;
  if (Number.isNaN(ratio)) return 0;
  return Math.max(0, Math.min(100, ratio));
}

/** Best-effort copy to the clipboard; silently no-ops where unavailable. */
export function copyToClipboard(text: string): void {
  try {
    void navigator.clipboard?.writeText?.(text);
  } catch {
    /* clipboard unavailable (insecure context, permissions) — ignore */
  }
}
