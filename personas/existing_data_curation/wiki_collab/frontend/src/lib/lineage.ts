/**
 * Client-side derivation of the curation workflow lineage from `AppState.files`.
 *
 * The backend doesn't expose an explicit "what stage are we at" field — instead
 * each lifecycle artifact is a nullable `FileLink` under `state.files`. A stage
 * is "done" once its artifact exists, and links straight to that artifact's
 * already-resolved `/files/<rel>` href. No network call required.
 */
import type { AppState } from "@/lib/types";

export type StageKey = "package" | "run" | "return" | "audit" | "merge";

export interface LineageStage {
  key: StageKey;
  label: string;
  sublabel: string;
  done: boolean;
  href: string | null;
}

/** Map `state.files` into the ordered 5-stage curation lineage. */
export function deriveLineage(state: AppState): LineageStage[] {
  const files = state.files;
  return [
    {
      key: "package",
      label: "Package",
      sublabel: "assignment .tar.gz",
      done: files.assignment_package !== null,
      href: files.assignment_package?.href ?? null,
    },
    {
      key: "run",
      label: "Run",
      sublabel: "worker output",
      done: files.last_run_archive !== null,
      href: files.last_run_archive?.href ?? null,
    },
    {
      key: "return",
      label: "Return",
      sublabel: "to owner inbox",
      done: files.last_returned_archive !== null,
      href: files.last_returned_archive?.href ?? null,
    },
    {
      key: "audit",
      label: "Audit",
      sublabel: "validate + audit",
      done: files.audit_report !== null,
      href: files.audit_report?.href ?? null,
    },
    {
      key: "merge",
      label: "Merge",
      sublabel: "accepted rows",
      done: files.merged_results !== null,
      href: files.merged_results?.href ?? null,
    },
  ];
}
