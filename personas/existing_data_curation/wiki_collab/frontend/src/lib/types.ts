/**
 * TypeScript mirror of the demo_app.py JSON contract.
 *
 * Source of truth: `state_payload()` (GET /api/state), the POST action handlers
 * in `DemoHandler.do_POST`, `load_full_clean_page` (POST /api/full-page), and
 * the additive `GET /api/dimensions` (the slim 1339-dim catalog grouped by
 * category). Keep these types in lockstep with demo_app.py.
 */

/** A downloadable artifact: `{path, href}` where href is a /files/<rel> URL. */
export interface FileLink {
  path: string;
  href: string;
}

/** One row of `_db_profiles` — a Wikipedia person profile + demo detail join. */
export interface Profile {
  global_idx: number;
  task_id: string;
  page_id: number;
  qid: string;
  title: string;
  source_url: string;
  profile_text: string;
  input_sha256: string;
  entity_type: string;
  tags: string[];
  revision_id: number | null;
  revision_timestamp: string | null;
  sections: unknown[];
  chunks: unknown[];
}

/** The runner input payload (subset of a profile sent to the model). */
export interface SelectedInput {
  global_idx: number;
  task_id: string;
  qid: string;
  title: string;
  source_url: string;
  profile_text: string;
}

export interface Assignment {
  assignment_id: string;
  worker_id: string;
  dataset_id: string;
  dataset_sha256: string;
  protocol_id: string;
  protocol_sha256: string;
  range_start: number;
  range_end: number;
  status: string;
}

export interface ProtocolManifest {
  protocol_id: string;
  protocol_version: string;
  prompt_file: string;
  output_schema_file: string;
  input_schema_file: string | null;
  prompt_sha256: string;
  output_schema_sha256: string;
  input_schema_sha256: string | null;
  protocol_sha256: string;
}

/** Assignment-type taxonomy from the protocol output schema. */
export type AssignmentType =
  | "direct"
  | "structured_claim"
  | "summary_inference"
  | "unsupported";

/** One attributed field from a result row (preview_result_archive). */
export interface ResultField {
  field_id: string | null;
  value: unknown;
  confidence: number | null;
  assignment_type: AssignmentType | string | null;
  evidence: string | null;
  plain_meaning: string;
}

export interface ResultRow {
  global_idx: number | null;
  task_id: string | null;
  qid: string | null;
  title: string;
  status: string | null;
  input_sha256: string | null;
  fields: ResultField[];
  provenance: Record<string, unknown>;
}

export interface ResultPreview {
  archive_path: string;
  row_count: number;
  failure_count: number;
  preview_limit: number;
  rows: ResultRow[];
}

/** Integer-keyed-by-label distributions in the audit summary. */
export type CountMap = Record<string, number>;

export interface AuditSummary {
  archive_count: number;
  accepted_archives: number;
  rejected_archives: number;
  returned_rows: number;
  valid_rows: number;
  failed_rows: number;
  duplicate_rows: number;
  backend_counts: CountMap;
  worker_counts: CountMap;
  requested_model_counts: CountMap;
  reported_model_counts: CountMap;
  effort_counts: CountMap;
  field_counts: CountMap;
  assignment_type_counts: CountMap;
  confidence_buckets: CountMap;
}

export interface AuditCoverage {
  assigned_rows: number;
  covered_rows: number;
  missing_assigned_rows: number;
  missing_indices_sample: number[];
  duplicate_indices_sample: number[];
}

export interface AuditArchive {
  archive_path: string;
  accepted: boolean;
  valid_rows: number;
  failed_rows: number;
  errors: string[];
  warnings: string[];
  worker_id?: string;
  [key: string]: unknown;
}

export interface AuditReport {
  summary: AuditSummary;
  coverage: AuditCoverage;
  archives: AuditArchive[];
}

export interface StateFiles {
  assignment_package: FileLink | null;
  last_run_archive: FileLink | null;
  last_returned_archive: FileLink | null;
  audit_report: FileLink | null;
  merged_results: FileLink | null;
}

export interface BackendStatus {
  claude_bin: string | null;
  codex_bin: string | null;
  claude_command: string;
  claude_cli_model_env: string;
}

export interface Metrics {
  clean_pages: number;
  sections: number;
  chunks: number;
  plain_text_chars: number;
  markup_residue_rows: number;
  demo_rows: number;
}

/** The full GET /api/state payload. */
export interface AppState {
  root: string;
  metrics: Metrics;
  dataset_manifest: Record<string, unknown> & { row_count?: number };
  full_page_derivatives: { path: string; available: boolean };
  lincoln_full_article: Record<string, unknown>;
  protocol_manifest: ProtocolManifest;
  prompt_template: string;
  selected_input: SelectedInput;
  rendered_prompt: string;
  profiles: Profile[];
  assignment: Assignment | null;
  backend_status: BackendStatus;
  files: StateFiles;
  audit_report: AuditReport | null;
  result_preview: ResultPreview | null;
}

// --- POST /api/full-page (load_full_clean_page) ---------------------------

export interface FullPageSection {
  section_index?: number;
  section_id?: string;
  section_title?: string;
  text?: string;
  [key: string]: unknown;
}

export interface FullPageChunk {
  section_index?: number;
  chunk_index?: number;
  chunk_id?: string;
  text?: string;
  [key: string]: unknown;
}

export interface FullPageResult {
  found: boolean;
  query: string;
  clean?: Record<string, unknown>;
  sections?: FullPageSection[];
  chunks?: FullPageChunk[];
  source?: Record<string, string>;
  error?: string;
  scanned_files?: number;
  scanned_rows?: number;
  elapsed_seconds?: number;
}

// --- GET /api/dimensions (the 1339-dim catalog grouped by category) -------

export interface CatalogDimension {
  id: string;
  label: string;
  description: string;
  values: string[];
}

export interface CatalogCategory {
  category: string;
  slug: string;
  protocol_id: string;
  count: number;
  dimensions: CatalogDimension[];
}

export interface DimensionCatalog {
  total_dimensions: number;
  category_count: number;
  categories: CatalogCategory[];
}

// --- POST action request/response shapes ----------------------------------

export interface AssignmentRequest {
  worker_id?: string;
  range_start?: number;
  range_end?: number;
  prompt_text?: string;
}
export interface AssignmentResponse {
  assignment: Assignment;
  package: FileLink | null;
}

export interface RunRequest {
  backend_name?: string;
  model?: string | null;
  effort?: string;
  concurrency?: number;
  prompt_text?: string;
}
export interface RunResponse {
  archive: FileLink | null;
  assignment: Assignment;
}

export interface ReturnResponse {
  returned: FileLink | null;
}
export interface AuditResponse {
  report: AuditReport;
}
export interface MergeResponse {
  summary: Record<string, number>;
  merged: FileLink | null;
}
