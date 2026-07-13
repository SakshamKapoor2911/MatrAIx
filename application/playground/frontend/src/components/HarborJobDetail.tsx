/**
 * Harbor batch job detail — trial index only; open a trial for evaluation + run content.
 */
import { useId, useMemo, useRef, useState, type ReactNode } from "react";
import { flushSync } from "react-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import {
  exportBatchReportPdf,
  humanizePathLeaf,
  plainTextFromMarkdown,
  type BatchReportPdfMeta,
  type BatchReportPdfPersona,
  type BatchReportPdfPersonaStrategy,
  type BatchReportPdfSnapshot,
} from "@/lib/exportBatchReportPdf";
import { personaDisplayId, personaPrimaryName } from "@/lib/personaDisplay";
import {
  surveyQuestionTypeChipClass,
  surveyQuestionTypeLabel,
  type SurveyQuestionTypeCount,
} from "@/lib/surveyDisplay";
import type {
  HarborJobAggregation,
  HarborJobDetail,
  JobAggregationCrossFacetView,
  TaskPersonaStrategy,
} from "@/lib/types";
import { PersonaAvatar } from "./cockpit/setup/PersonaAvatar";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import {
  StudioGlassPanel,
  StudioPageFrame,
  StudioPageHeader,
  StudioToolbarButton,
} from "./studio/StudioShell";

export interface HarborJobDetailProps {
  jobName: string;
  onBack: () => void;
  onOpenTrial?: (trialName: string) => void;
}

type HarborTrialRow = HarborJobDetail["trials"][number];
type AggregationField = HarborJobAggregation["fields"][number];
type AggregationContext = NonNullable<HarborJobAggregation["contexts"]>[number];
type AggregationSummary = NonNullable<AggregationContext["summaries"]>[number];
type AggregationJudge = NonNullable<AggregationContext["judges"]>[number];
type AggregationCrossFacetView = JobAggregationCrossFacetView;
type AggregationContextType =
  | "question_response"
  | "decision"
  | "decision_process"
  | "experience"
  | "task_outcome"
  | "conversation_summary"
  | "user_feedback"
  | "feedback"
  | "policy_and_trust"
  | "coordination"
  | string;

const CONTEXT_TYPE_META: Record<
  string,
  { badge: string; description: string; order: number }
> = {
  question_response: {
    badge: "Question",
    description: "One survey question — response mix across the persona cohort.",
    order: 0,
  },
  trial_summary: {
    badge: "Trial summary",
    description: "Per-trial coverage stats (answers, trajectory).",
    order: 80,
  },
  decision: {
    badge: "Decision",
    description: "What the persona ultimately chose and why.",
    order: 0,
  },
  task_outcome: {
    badge: "Task outcome",
    description: "Whether the user's goal was resolved, blocked, or left for follow-up.",
    order: 0,
  },
  decision_process: {
    badge: "Decision process",
    description: "How the persona explored options before deciding.",
    order: 1,
  },
  conversation_summary: {
    badge: "Conversation summary",
    description: "How the exchange progressed, including turn counts and clarification behavior.",
    order: 1,
  },
  experience: {
    badge: "Experience",
    description: "Post-task ratings covering ease, trust, and friction.",
    order: 2,
  },
  user_feedback: {
    badge: "User feedback",
    description: "Persona self-report about usefulness, fit, trust, or effort.",
    order: 2,
  },
  feedback: {
    badge: "User feedback",
    description: "Persona self-report about usefulness, fit, trust, or effort.",
    order: 2,
  },
  policy_and_trust: {
    badge: "Policy and trust",
    description: "Checks for groundedness, policy compliance, and handoff quality.",
    order: 3,
  },
  coordination: {
    badge: "Coordination",
    description: "Who still needs to act and whether the next step was clear.",
    order: 4,
  },
  web_interaction: {
    badge: "Web interaction",
    description: "How the persona navigated the site before submitting.",
    order: 5,
  },
  web_artifact: {
    badge: "Web artifact",
    description: "Whether the saved submission artifact matched the task goal.",
    order: 5,
  },
  goal_component: {
    badge: "Goal component",
    description: "Per-step checks against individual task requirements.",
    order: 5,
  },
  persona_alignment: {
    badge: "Persona alignment",
    description: "How well the outcome matched persona preferences or constraints.",
    order: 1,
  },
  persona_constraint: {
    badge: "Persona constraint",
    description: "Whether persona-specific limits or preferences were respected.",
    order: 1,
  },
};

type ReportingCategory = "web" | "os-app" | "chatbot" | "survey" | "generic";

/** Category-level UX: context ordering / compaction / breakdown preference — not per-task facet keys. */
const CONTEXT_PRIORITY_BY_CATEGORY: Record<ReportingCategory, Record<string, number>> = {
  web: {
    decision: 0,
    question_response: 0,
    user_feedback: 1,
    feedback: 1,
    decision_process: 2,
    task_outcome: 3,
    experience: 4,
    web_artifact: 8,
    web_interaction: 9,
  },
  "os-app": {
    persona_alignment: 0,
    persona_constraint: 1,
    question_response: 0,
    user_feedback: 2,
    feedback: 2,
    decision: 3,
    task_outcome: 4,
    goal_component: 5,
    experience: 6,
  },
  chatbot: {
    task_outcome: 0,
    user_feedback: 1,
    feedback: 1,
    conversation_summary: 2,
    coordination: 3,
    policy_and_trust: 4,
    question_response: 0,
  },
  survey: {
    question_response: 0,
    user_feedback: 1,
    feedback: 1,
    experience: 2,
  },
  generic: {},
};

const HEADLINE_CONTEXT_TYPES: Record<ReportingCategory, Set<string>> = {
  web: new Set(["decision", "decision_process", "user_feedback", "feedback", "question_response"]),
  "os-app": new Set([
    "persona_alignment",
    "persona_constraint",
    "decision",
    "user_feedback",
    "feedback",
    "question_response",
  ]),
  chatbot: new Set(["task_outcome", "user_feedback", "feedback", "coordination", "question_response"]),
  survey: new Set(["question_response", "user_feedback", "feedback"]),
  generic: new Set(["decision", "user_feedback", "feedback", "question_response"]),
};

const EXECUTION_CONTEXT_TYPES_BY_CATEGORY: Record<ReportingCategory, Set<string>> = {
  web: new Set(["task_outcome", "web_artifact", "web_interaction", "decision_process"]),
  "os-app": new Set(["task_outcome", "goal_component", "side_effects", "execution_profile"]),
  chatbot: new Set(["task_outcome", "conversation_summary"]),
  survey: new Set(["task_outcome"]),
  generic: new Set([
    "task_outcome",
    "web_artifact",
    "web_interaction",
    "decision_process",
    "goal_component",
    "side_effects",
    "execution_profile",
    "conversation_summary",
  ]),
};

const BREAKDOWN_CONTEXT_ORDER: Record<ReportingCategory, string[]> = {
  web: ["decision", "decision_process", "question_response", "user_feedback", "feedback"],
  "os-app": ["goal_component", "persona_alignment", "persona_constraint", "decision", "user_feedback"],
  chatbot: ["task_outcome", "user_feedback", "feedback", "conversation_summary"],
  survey: ["question_response", "user_feedback", "feedback"],
  generic: ["decision", "question_response", "task_outcome", "user_feedback"],
};

const WEB_SIGNAL_CONTEXT_TYPES = new Set(["web_artifact", "web_interaction"]);
const OS_APP_SIGNAL_CONTEXT_TYPES = new Set(["goal_component", "persona_alignment", "persona_constraint"]);
const CHAT_SIGNAL_CONTEXT_TYPES = new Set(["conversation_summary", "coordination", "policy_and_trust"]);

function inferReportingCategory(
  contexts: AggregationContext[],
  applicationType?: string | null,
): ReportingCategory {
  const contextTypes = new Set(contexts.map((context) => context.contextType).filter(Boolean) as string[])
  if ([...contextTypes].some((type) => CHAT_SIGNAL_CONTEXT_TYPES.has(type))) return "chatbot"
  if ([...contextTypes].some((type) => WEB_SIGNAL_CONTEXT_TYPES.has(type))) return "web"
  if ([...contextTypes].some((type) => OS_APP_SIGNAL_CONTEXT_TYPES.has(type))) return "os-app"
  if (contextTypes.has("question_response")) return "survey"

  const explicit = (applicationType ?? "").trim().toLowerCase()
  if (explicit && explicit !== "unknown" && ["web", "os-app", "chatbot", "survey"].includes(explicit)) {
    return explicit as ReportingCategory
  }
  return "generic"
}

function contextPriority(context: AggregationContext, category: ReportingCategory): number {
  const mapped = CONTEXT_PRIORITY_BY_CATEGORY[category][context.contextType ?? ""]
  if (mapped != null) return mapped
  return contextTypeMeta(context.contextType)?.order ?? 50
}

function breakdownContextRank(context: AggregationContext, category: ReportingCategory): number {
  const order = BREAKDOWN_CONTEXT_ORDER[category]
  const index = order.indexOf(context.contextType ?? "")
  return index === -1 ? 99 : index
}

function trialStatus(trial: HarborTrialRow): "done" | "failed" | "running" | "pending" {
  if (trial.error || trial.succeeded === false) return "failed";
  if (trial.completed) return "done";
  if (trial.completed === false) return "running";
  return "pending";
}

function trialStatusLabel(status: ReturnType<typeof trialStatus>): string {
  switch (status) {
    case "done":
      return "Done";
    case "failed":
      return "Failed";
    case "running":
      return "Running";
    default:
      return "Pending";
  }
}

const TRIAL_STATUS_STYLES: Record<
  ReturnType<typeof trialStatus>,
  { className: string; icon: string; fill?: 0 | 1 }
> = {
  running: { className: "border-warn/40 bg-warn/10 text-warn", icon: "autorenew" },
  done: { className: "border-secondary/40 bg-secondary/10 text-secondary", icon: "check_circle", fill: 1 },
  failed: { className: "border-danger/40 bg-danger/10 text-danger", icon: "error", fill: 1 },
  pending: { className: "border-outline bg-surface-high text-text-dim", icon: "hourglass_empty" },
};

function TrialStatusBadge({ trial }: { trial: HarborTrialRow }) {
  const status = trialStatus(trial);
  const style = TRIAL_STATUS_STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[12px] uppercase tracking-wide ${style.className}`}
    >
      <Sym
        name={style.icon}
        size={12}
        fill={style.fill}
        className={status === "running" ? "shrink-0 animate-rb-spin" : "shrink-0"}
      />
      {trialStatusLabel(status)}
    </span>
  );
}

function TrialPersonaIdentity({ trial }: { trial: HarborTrialRow }) {
  const displayName = personaPrimaryName(trial.personaName, trial.personaId);
  const codename = trial.personaId ? personaDisplayId(trial.personaId) : trial.trialName;
  const personaKey = trial.personaId ?? trial.trialName;

  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <PersonaAvatar personaId={personaKey} size="sm" />
      <div className="min-w-0">
        <p className="truncate font-medium text-text-main">{displayName}</p>
        <p className="truncate font-mono text-[12px] text-text-dim">{codename}</p>
      </div>
    </div>
  );
}

function metricValue(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function reportingStatusLabel(status: string | null | undefined): string {
  const normalized = (status ?? "").trim().toLowerCase();
  switch (normalized) {
    case "queued":
      return "Queued";
    case "running":
      return "Running";
    case "completed":
      return "Completed";
    case "completed_with_errors":
      return "Completed with errors";
    case "partial":
      return "Partial";
    case "partial_with_errors":
      return "Partial with errors";
    case "failed":
      return "Failed";
    case "ready":
      return "Ready";
    case "not_applicable":
      return "Not applicable";
    default:
      return normalized ? normalized.split("_").join(" ") : "Unknown";
  }
}

function reportingStatusClassName(status: string | null | undefined): string {
  const normalized = (status ?? "").trim().toLowerCase();
  if (normalized === "queued" || normalized === "running") {
    return "border-warn/40 bg-warn/10 text-warn";
  }
  if (normalized === "completed") {
    return "border-secondary/40 bg-secondary/10 text-secondary";
  }
  if (normalized === "completed_with_errors" || normalized === "partial_with_errors" || normalized === "failed") {
    return "border-danger/40 bg-danger/10 text-danger";
  }
  if (normalized === "ready" || normalized === "partial") {
    return "border-primary/40 bg-primary/10 text-primary";
  }
  return "border-outline/50 bg-surface/60 text-text-dim";
}

function ratioWidth(count: number, total: number): string {
  const safeTotal = Math.max(total, 1)
  return `${Math.max(6, Math.round((count / safeTotal) * 100))}%`
}

function previewText(value: string | null | undefined, limit = 220): string {
  const normalized = (value ?? "").trim().replace(/\s+/g, " ")
  if (!normalized) return ""
  if (normalized.length <= limit) return normalized
  return `${normalized.slice(0, limit - 1).trimEnd()}…`
}

function primaryFacetForContext(context: AggregationContext): AggregationField | null {
  return context.facets.find((facet) => facet.role === "primary") ?? context.facets[0] ?? null
}

function explanationFacetForContext(context: AggregationContext): AggregationField | null {
  return (
    context.facets.find((facet) => facet.role === "explanation") ??
    context.facets.find((facet) => facet.kind === "textual") ??
    null
  )
}

/** Survey reasons only — never reuse the primary answer facet. */
function surveyReasonFacetForContext(context: AggregationContext): AggregationField | null {
  const primary = primaryFacetForContext(context)
  const byRole = context.facets.find((facet) => facet.role === "explanation")
  if (byRole && byRole.key !== primary?.key) return byRole
  return (
    context.facets.find(
      (facet) => facet.kind === "textual" && facet.key !== primary?.key && facet.role !== "primary",
    ) ?? null
  )
}

function contextTypeMeta(contextType: AggregationContextType | null | undefined) {
  return contextType ? CONTEXT_TYPE_META[contextType] ?? null : null
}

function contextTypeBadgeLabel(context: AggregationContext): string | null {
  return contextTypeMeta(context.contextType)?.badge ?? null
}

function contextTypeDescription(context: AggregationContext): string | null {
  return contextTypeMeta(context.contextType)?.description ?? null
}

function isHeuristicAggregationSummary(text: string): boolean {
  const normalized = text.trim()
  return (
    /^All \d+ available trials reported the same text:/i.test(normalized) ||
    /^Collected \d+ text responses across \d+ unique values/i.test(normalized) ||
    /^All \d+ answers (point to the same theme|converge on one theme):/i.test(normalized) ||
    /^Across \d+ answers/i.test(normalized)
  )
}

function isUnanimousField(field: AggregationField): boolean {
  if (field.kind !== "categorical") return false
  const counts = field.categorical?.counts ?? []
  return counts.length === 1 && counts[0].count === field.presentCount && field.presentCount > 0
}

function contextDivergenceScore(context: AggregationContext): number {
  let score = 0
  for (const facet of context.facets) {
    if (facet.kind === "categorical") {
      score += facet.categorical?.distinctCount ?? facet.categorical?.counts?.length ?? 0
    } else if (facet.kind === "textual") {
      score += facet.textual?.uniqueCount ?? 0
    }
  }
  return score
}

function formatBucketLabel(value: string): string {
  const normalized = value.trim().toLowerCase()
  if (normalized === "true" || normalized === "yes") return "Yes"
  if (normalized === "false" || normalized === "no") return "No"
  if (normalized === "partially" || normalized === "partial") return "Partially"
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function formatCategoricalDistribution(field: AggregationField | null): string {
  const counts = field?.categorical?.counts ?? []
  if (counts.length === 0) return "—"
  const total = Math.max(
    field?.presentCount ?? 0,
    counts.reduce((sum, entry) => sum + entry.count, 0),
    1,
  )
  // Compact share form for small enums (Yes/No, yes/partially/no).
  if (counts.length <= 3) {
    return counts
      .map((entry) => `${formatBucketLabel(entry.value)} ${entry.count}/${total}`)
      .join(" · ")
  }
  return counts.map((entry) => `${formatBucketLabel(entry.value)} (${entry.count})`).join(" · ")
}

function groupTextualSamples(field: AggregationField | null): Array<{ label: string; count: number }> {
  const grouped = new Map<string, number>()
  for (const sample of field?.textual?.samples ?? []) {
    const label = sample.trim()
    if (!label) continue
    grouped.set(label, (grouped.get(label) ?? 0) + 1)
  }
  return [...grouped.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
}

type InsightTone = "success" | "warn" | "danger" | "primary"

function ratingTone(avg: number | null | undefined): InsightTone {
  if (avg == null || Number.isNaN(avg)) return "warn"
  if (avg >= 7) return "success"
  if (avg >= 4) return "warn"
  return "danger"
}

function categoricalFacetTone(field: AggregationField | null): InsightTone {
  const values = (field?.categorical?.counts ?? []).map((entry) => entry.value.toLowerCase())
  if (values.length === 0) return "primary"
  if (
    values.some((value) =>
      ["no", "false", "failed", "unresolved", "blocked", "stalled", "unmet", "missed", "not_met"].includes(
        value,
      ),
    )
  ) {
    return "danger"
  }
  if (
    values.some(
      (value) =>
        ["partially", "partially_resolved", "partial", "partial_met"].includes(value) ||
        value.includes("partial") ||
        value.includes("clarify"),
    )
  ) {
    return "warn"
  }
  if (
    values.some(
      (value) =>
        ["yes", "true", "passed", "complete", "resolved", "selected", "met", "satisfied", "aligned"].includes(
          value,
        ) || (value.includes("resolve") && !value.includes("partial")),
    )
  ) {
    return "success"
  }
  return "primary"
}

function inferRatingScale(field: AggregationField): number | null {
  const max = field.numerical?.max
  if (max == null) return null
  if (max <= 5) return 5
  if (max <= 10) return 10
  if (max <= 100) return 100
  return null
}

/** True only for real rating/score facets — not raw counts like answer_count. */
function looksLikeRatingFacet(field: AggregationField): boolean {
  const haystack = `${field.facetKey} ${field.key} ${field.label}`.toLowerCase()
  if (
    haystack.includes("count") ||
    haystack.includes("answer_count") ||
    haystack.includes("trajectory") ||
    haystack.includes("event")
  ) {
    return false
  }
  if (!(haystack.includes("rating") || haystack.includes("score") || haystack.includes("likert"))) {
    return false
  }
  return inferRatingScale(field) != null
}

function facetUsesSemanticTone(field: AggregationField): boolean {
  if (field.kind === "numerical") return looksLikeRatingFacet(field)
  if (field.kind === "categorical") return categoricalFacetTone(field) !== "primary"
  return false
}

type InsightChipProps = {
  label: string
  value: string
  tone?: InsightTone
  variant?: "neutral" | "semantic"
  meterPct?: number | null
}

function facetToInsightChip(field: AggregationField): InsightChipProps | null {
  if (field.kind === "numerical") {
    const avg = field.numerical?.avg ?? null
    const scale = inferRatingScale(field)
    const isRating = looksLikeRatingFacet(field)
    // Only append /5 or /10 for real ratings — never for counts (e.g. answer_count=9 → "9/10").
    const suffix = isRating ? (scale === 10 ? "/10" : scale === 5 ? "/5" : "") : ""
    return {
      label: field.label,
      value: `${formatNumericalSummary(field)}${suffix}`,
      variant: isRating ? "semantic" : "neutral",
      tone: isRating ? ratingTone(avg) : "primary",
      meterPct: isRating && scale != null && avg != null ? (avg / scale) * 100 : null,
    }
  }
  if (field.kind === "categorical") {
    const tone = categoricalFacetTone(field)
    return {
      label: field.label,
      value: formatCategoricalDistribution(field),
      variant: facetUsesSemanticTone(field) ? "semantic" : "neutral",
      tone,
    }
  }
  return null
}

type DistributionBreakdown = {
  contextLabel: string
  dimensionKey: string
  dimensionLabel: string
  rows: Array<{ label: string; count: number }>
  detailField: AggregationField | null
}

function dimensionDistinctCount(field: AggregationField): number {
  if (field.kind === "categorical") {
    return field.categorical?.distinctCount ?? field.categorical?.counts?.length ?? 0
  }
  if (field.kind === "textual") {
    return field.textual?.uniqueCount ?? groupTextualSamples(field).length
  }
  return 0
}

function breakdownRowsForField(field: AggregationField): Array<{ label: string; count: number }> {
  if (field.kind === "textual") return groupTextualSamples(field)
  if (field.kind === "categorical") {
    return (field.categorical?.counts ?? []).map((entry) => ({
      label: formatBucketLabel(entry.value),
      count: entry.count,
    }))
  }
  return []
}

function findBreakdownDimension(context: AggregationContext, trialCount: number): AggregationField | null {
  const candidates = context.facets.filter((facet) => {
    if (facet.role === "explanation" && facet.kind === "textual") return false
    if (facet.kind === "categorical") return (facet.categorical?.counts?.length ?? 0) > 0
    if (facet.kind === "textual") return (facet.textual?.samples?.length ?? 0) > 0
    return false
  })
  if (candidates.length === 0) return null

  candidates.sort((a, b) => {
    const distinctDelta = dimensionDistinctCount(b) - dimensionDistinctCount(a)
    if (distinctDelta !== 0) return distinctDelta
    const roleRank = (facet: AggregationField) =>
      facet.role === "primary" ? 0 : facet.role === "evidence" ? 1 : 2
    return roleRank(a) - roleRank(b)
  })

  const dimension = candidates[0]
  const rows = breakdownRowsForField(dimension)
  if (rows.length === 0) return null
  if (rows.length === 1 && trialCount <= 1) return null
  return dimension
}

function findBreakdownDetailField(context: AggregationContext, dimensionKey: string): AggregationField | null {
  return (
    context.facets.find(
      (facet) =>
        facet.key !== dimensionKey &&
        facet.kind === "textual" &&
        (facet.role === "evidence" || facet.role === "explanation") &&
        (facet.textual?.samples?.length ?? 0) > 0,
    ) ?? null
  )
}

function buildContextDistributionBreakdown(
  context: AggregationContext,
  trialCount: number,
): DistributionBreakdown | null {
  const dimension = findBreakdownDimension(context, trialCount)
  if (!dimension) return null
  const rows = breakdownRowsForField(dimension)
  if (rows.length === 0 || (rows.length === 1 && trialCount <= 1)) return null

  return {
    contextLabel: context.label,
    dimensionKey: dimension.key,
    dimensionLabel: dimension.label,
    rows,
    detailField: findBreakdownDetailField(context, dimension.key),
  }
}

function buildDistributionBreakdowns(
  contexts: AggregationContext[],
  trialCount: number,
  category: ReportingCategory,
  options?: { limit?: number },
): DistributionBreakdown[] {
  const limit = options?.limit ?? 2
  const breakdowns: DistributionBreakdown[] = []
  for (const context of orderedContextsForBreakdown(contexts, category)) {
    if (shouldCompactContext(context, category)) continue
    const breakdown = buildContextDistributionBreakdown(context, trialCount)
    if (!breakdown) continue
    if (breakdown.rows.length === 1 && trialCount <= 1) continue
    breakdowns.push(breakdown)
    if (breakdowns.length >= limit) break
  }
  return breakdowns
}

function insightFacetsForContext(context: AggregationContext): AggregationField[] {
  const facets: AggregationField[] = []
  const push = (facet: AggregationField | null | undefined) => {
    if (!facet || facet.kind === "textual") return
    if (!facets.some((entry) => entry.key === facet.key)) facets.push(facet)
  }
  push(primaryFacetForContext(context))
  for (const facet of context.facets) {
    if (facet.role === "score" && looksLikeRatingFacet(facet)) push(facet)
    if (facet.kind === "categorical" && facetUsesSemanticTone(facet)) push(facet)
  }
  return facets
}

function buildHeadlineInsightChips(
  contexts: AggregationContext[],
  coverage: HarborJobAggregation["coverage"],
  category: ReportingCategory,
  options?: { excludeFacetKeys?: ReadonlySet<string> },
): InsightChipProps[] {
  if (category === "survey") {
    return buildSurveyCoverageStats(contexts, coverage).map((stat) => ({
      label: stat.label,
      value: stat.value,
      variant: "neutral",
      tone: "primary",
    }))
  }
  // Coverage tiles already show trial completion — chips only carry signals not expanded below.
  const chips: InsightChipProps[] = []
  const exclude = options?.excludeFacetKeys ?? new Set<string>()
  const seen = new Set<string>()
  for (const context of orderedContexts(contexts, category)) {
    if (shouldCompactContext(context, category)) continue
    for (const facet of insightFacetsForContext(context)) {
      if (seen.has(facet.key) || exclude.has(facet.key)) continue
      seen.add(facet.key)
      const chip = facetToInsightChip(facet)
      if (chip) chips.push(chip)
      if (chips.length >= 8) return chips
    }
  }
  return chips
}

/** Survey header extras — mirror single-trial debrief (types + agreement), never a global Likert mean. */
function buildSurveyCoverageStats(
  contexts: AggregationContext[],
  coverage: HarborJobAggregation["coverage"],
): Array<{ label: string; value: string; hint?: string }> {
  const stats: Array<{ label: string; value: string; hint?: string }> = []
  const questionContexts = contexts.filter((context) => context.contextType === "question_response")
  const questionCount = questionContexts.length
  const summary = contexts.find((context) => context.contextType === "trial_summary")

  if (coverage.completedTrials !== coverage.trialCount) {
    stats.push({
      label: "Completed",
      value: `${coverage.completedTrials}/${coverage.trialCount}`,
      hint: "Still running or failed",
    })
  }

  const answerCount = summary?.facets.find(
    (facet) => facet.key === "answer_count" || facet.facetKey === "answer_count",
  )
  if (answerCount?.kind === "numerical" && answerCount.numerical?.avg != null) {
    const avg = answerCount.numerical.avg
    const expected = questionCount > 0 ? questionCount : (answerCount.numerical.max ?? null)
    // Only surface when personas skipped questions — full completion is implied by Questions.
    if (expected != null && Math.abs(avg - expected) > 0.05) {
      stats.push({
        label: "Answered",
        value: `${metricValue(avg)} / ${expected}`,
        hint: "Avg questions answered per persona",
      })
    }
  }

  const agreement = buildSurveyAgreementStat(questionContexts)
  if (agreement) stats.push(agreement)

  return stats
}

/** Count instrument questions by type — same chip language as single-trial debrief. */
function buildSurveyQuestionTypeCounts(contexts: AggregationContext[]): SurveyQuestionTypeCount[] {
  const totals = new Map<string, number>()
  for (const context of contexts) {
    if (context.contextType !== "question_response") continue
    const type = resolveSurveyQuestionType(context, primaryFacetForContext(context))
    if (type === "unknown") continue
    totals.set(type, (totals.get(type) ?? 0) + 1)
  }
  return [...totals.entries()]
    .map(([type, count]) => ({
      type,
      label: surveyQuestionTypeLabel(type),
      count,
    }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
}

/** Per-question consensus — same labels as the question cards (Unanimous / Clear / Split). */
function surveyQuestionConsensus(context: AggregationContext): "unanimous" | "clear" | "split" | null {
  const primary = primaryFacetForContext(context)
  if (!primary || (primary.presentCount ?? 0) <= 0) return null
  const questionType = resolveSurveyQuestionType(context, primary)

  if (questionType === "likert" || primary.kind === "numerical") {
    const scale = likertScaleBounds(context, primary)
    const points = likertScalePoints(context, primary, scale)
    const filled = points.filter((point) => point.count > 0).length
    if (filled <= 1) return "unanimous"
    const avg = primary.numerical?.avg
    if (avg != null && (avg >= scale.max - 0.35 || avg <= scale.min + 0.35)) return "clear"
    return "split"
  }

  if (
    questionType === "single_choice" ||
    questionType === "multi_choice" ||
    primary.kind === "categorical"
  ) {
    const items = surveyAnswerItems(context, primary)
    const denom = Math.max(primary.presentCount ?? 0, 1)
    const ranked = [...items].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
    const leader = ranked.find((item) => item.count > 0)
    const chosen = ranked.filter((item) => item.count > 0).length
    if (chosen <= 1 && (leader?.count ?? 0) > 0) return "unanimous"
    const share = leader ? leader.count / denom : 0
    if (share >= 0.6) return "clear"
    return "split"
  }

  if (questionType === "free_text" || primary.kind === "textual") {
    const themes = freeTextThemes(primary)
    if (themes.length === 0) return null
    const present = Math.max(primary.presentCount ?? 0, 1)
    if (themes.length === 1) return "unanimous"
    if (themes[0].count / present >= 0.6) return "clear"
    return "split"
  }

  return null
}

function buildSurveyAgreementStat(
  questionContexts: AggregationContext[],
): { label: string; value: string; hint?: string } | null {
  let unanimous = 0
  let clear = 0
  let split = 0
  for (const context of questionContexts) {
    const consensus = surveyQuestionConsensus(context)
    if (consensus === "unanimous") unanimous += 1
    else if (consensus === "clear") clear += 1
    else if (consensus === "split") split += 1
  }
  const scored = unanimous + clear + split
  if (scored === 0) return null

  if (unanimous === scored) {
    return {
      label: "Agreement",
      value: "Unanimous",
      hint: `All ${scored} question${scored === 1 ? "" : "s"}`,
    }
  }
  if (split === scored) {
    return {
      label: "Agreement",
      value: "Split",
      hint: `All ${scored} question${scored === 1 ? "" : "s"} diverge`,
    }
  }
  const aligned = unanimous + clear
  return {
    label: "Agreement",
    value: `${aligned}/${scored}`,
    hint: [
      unanimous > 0 ? `${unanimous} unanimous` : null,
      clear > 0 ? `${clear} clear` : null,
      split > 0 ? `${split} split` : null,
    ]
      .filter(Boolean)
      .join(" · "),
  }
}

function buildScoreMetricStrip(contexts: AggregationContext[]): string[] {
  const stats: string[] = []
  const seen = new Set<string>()
  for (const context of contexts) {
    for (const facet of context.facets) {
      if (facet.role !== "score" || facet.kind !== "numerical" || seen.has(facet.key)) continue
      if (looksLikeRatingFacet(facet)) continue
      seen.add(facet.key)
      stats.push(`${facet.label}: ${formatNumericalSummary(facet)}`)
    }
  }
  return stats
}

function buildPersonaSnapshotFields(contexts: AggregationContext[]): AggregationField[] {
  return contexts.flatMap((context) =>
    context.facets.filter(
      (facet) =>
        facet.kind === "textual" &&
        (facet.role === "explanation" || facet.role === "primary") &&
        (facet.textual?.samples?.length ?? 0) > 0 &&
        !isHeuristicAggregationSummary(facet.textual?.summary ?? ""),
    ),
  )
}

function ratingBarClass(tone: "success" | "warn" | "danger"): string {
  if (tone === "success") return "bg-secondary"
  if (tone === "warn") return "bg-warn"
  return "bg-danger"
}

function shouldCompactContext(context: AggregationContext, category: ReportingCategory): boolean {
  if (HEADLINE_CONTEXT_TYPES[category].has(context.contextType ?? "")) return false
  if (!EXECUTION_CONTEXT_TYPES_BY_CATEGORY[category].has(context.contextType ?? "")) return false
  const primary = primaryFacetForContext(context)
  return primary != null && primary.kind === "categorical" && isUnanimousField(primary)
}

function splitContexts(contexts: AggregationContext[], category: ReportingCategory): {
  headline: AggregationContext[]
  compact: AggregationContext[]
} {
  const ordered = orderedContexts(contexts, category)
  const headline: AggregationContext[] = []
  const compact: AggregationContext[] = []
  for (const context of ordered) {
    if (shouldCompactContext(context, category)) compact.push(context)
    else headline.push(context)
  }
  return { headline, compact }
}

function orderedContexts(contexts: AggregationContext[], category: ReportingCategory): AggregationContext[] {
  return [...contexts].sort((a, b) => {
    const aPriority = contextPriority(a, category)
    const bPriority = contextPriority(b, category)
    if (aPriority !== bPriority) return aPriority - bPriority
    const aDivergence = contextDivergenceScore(a)
    const bDivergence = contextDivergenceScore(b)
    if (aDivergence !== bDivergence) return bDivergence - aDivergence
    const aOrder = contextTypeMeta(a.contextType)?.order ?? 99
    const bOrder = contextTypeMeta(b.contextType)?.order ?? 99
    if (aOrder !== bOrder) return aOrder - bOrder
    return a.label.localeCompare(b.label)
  })
}

function orderedContextsForBreakdown(
  contexts: AggregationContext[],
  category: ReportingCategory,
): AggregationContext[] {
  return [...contexts].sort((a, b) => {
    const aRank = breakdownContextRank(a, category)
    const bRank = breakdownContextRank(b, category)
    if (aRank !== bRank) return aRank - bRank
    const aDivergence = contextDivergenceScore(a)
    const bDivergence = contextDivergenceScore(b)
    if (aDivergence !== bDivergence) return bDivergence - aDivergence
    return a.label.localeCompare(b.label)
  })
}

function crossFacetViewsForContext(context: AggregationContext): AggregationCrossFacetView[] {
  return context.crossFacetViews ?? context.relationships ?? []
}

function summaryBucketsForContext(context: AggregationContext): CountBarItem[] {
  const summary = context.summaries?.find((item) => item.buckets.length > 0)
  if (summary) {
    return summary.buckets.map((bucket) => ({
      label: bucket.bucket,
      count: bucket.count,
      detail: bucket.summary ?? null,
    }))
  }
  const categorical = context.facets.find((facet) => facet.kind === "categorical")
  if (categorical?.categorical?.counts?.length) {
    return categorical.categorical.counts.map((entry) => ({
      label: formatBucketLabel(entry.value),
      count: entry.count,
    }))
  }
  const crossFacetView = crossFacetViewsForContext(context).find(
    (item) => (item.buckets?.length ?? 0) > 0,
  )
  return (crossFacetView?.buckets ?? []).map((bucket) => ({
    label: bucket.category,
    count: bucket.count,
  }))
}

function contextLeadText(context: AggregationContext): string {
  const summary = context.summaries?.find((item) => item.overall?.summary)?.overall?.summary
  if (summary && !isHeuristicAggregationSummary(summary)) return previewText(summary, 140)

  const explanation = explanationFacetForContext(context)
  const explanationSample = explanation?.textual?.samples?.[0]
  if (explanationSample && !isHeuristicAggregationSummary(explanation?.textual?.summary ?? explanationSample)) {
    return previewText(explanationSample, 140)
  }
  if (explanation?.textual?.summary && !isHeuristicAggregationSummary(explanation.textual.summary)) {
    return previewText(explanation.textual.summary, 140)
  }

  const primary = primaryFacetForContext(context)
  if (primary?.kind === "categorical" && isUnanimousField(primary)) {
    const value = primary.categorical?.counts?.[0]?.value ?? "—"
    return `All ${primary.presentCount} personas: ${formatBucketLabel(value)}`
  }
  if (primary?.kind === "numerical") {
    return `${primary.label}: ${formatNumericalSummary(primary)}`
  }

  const buckets = summaryBucketsForContext(context)
  if (buckets.length > 0) {
    return `${formatBucketLabel(buckets[0].label)} (${buckets[0].count})`
  }

  return ""
}

function reportingSummary(
  reporting: HarborJobAggregation["reporting"] | null | undefined,
): { value: string; hint: string } | null {
  if (!reporting || reporting.status === "not_applicable") return null

  const total = reporting.totalUnits ?? 0
  const completed = reporting.completedUnits ?? 0
  const ready = reporting.readyUnits ?? 0
  const failed = reporting.failedUnits ?? 0
  const model = reporting.model ? ` · ${reporting.model}` : ""
  const status = reportingStatusLabel(reporting.status)

  if ((reporting.status === "ready" || reporting.status === "partial") && completed === 0) {
    return {
      value: status,
      hint: `${ready || total} units${model}`,
    }
  }

  if (reporting.status === "queued" || reporting.status === "running") {
    return {
      value: `${completed}/${total}`,
      hint: `${status}${model}`,
    }
  }

  if (
    reporting.status === "completed" ||
    reporting.status === "completed_with_errors" ||
    reporting.status === "partial_with_errors" ||
    reporting.status === "failed"
  ) {
    return {
      value: status,
      hint: `${completed}/${total}${failed > 0 ? ` · ${failed} failed` : ""}${model}`,
    }
  }

  return {
    value: status,
    hint: `${total} units${model}`,
  }
}

function orderedFacets(facets: AggregationField[]): AggregationField[] {
  return [...facets].sort((a, b) => {
    const aRank = a.role === "primary" ? 0 : a.role === "explanation" ? 2 : 1
    const bRank = b.role === "primary" ? 0 : b.role === "explanation" ? 2 : 1
    if (aRank !== bRank) return aRank - bRank
    return a.label.localeCompare(b.label)
  })
}

type CountBarItem = {
  label: string
  count: number
  detail?: string | null
}

function formatNumericalSummary(field: AggregationField | null, suffix = ""): string {
  if (!field) return "—"
  const avg = field.numerical?.avg
  if (avg == null) return "—"
  const min = field.numerical?.min
  const max = field.numerical?.max
  if (min != null && max != null && min !== max) {
    return `${metricValue(min)}–${metricValue(max)} avg ${metricValue(avg)}${suffix}`
  }
  return `${metricValue(avg)}${suffix}`
}

function InsightChip({
  label,
  value,
  tone = "primary",
  variant = "neutral",
  meterPct,
}: {
  label: string
  value: string
  tone?: "primary" | "success" | "warn" | "danger"
  /** semantic = always apply tone colors; neutral = grey summary chip */
  variant?: "neutral" | "semantic"
  meterPct?: number | null
}) {
  const toneTextClass: Record<NonNullable<typeof tone>, string> = {
    success: "text-secondary",
    primary: "text-primary",
    warn: "text-warn",
    danger: "text-danger",
  }
  const toneBoxClass: Record<NonNullable<typeof tone>, string> = {
    success: "border-secondary/45 bg-secondary/10",
    primary: "border-primary/45 bg-primary/15",
    warn: "border-warn/45 bg-warn/10",
    danger: "border-danger/45 bg-danger/10",
  }
  const colored = variant === "semantic"
  const meterTone = tone === "primary" ? "warn" : tone

  return (
    <div
      className={`min-w-[108px] rounded-lg border px-2.5 py-1.5 ${
        colored ? toneBoxClass[tone] : "border-outline/40 bg-surface/55"
      }`}
    >
      <div className="text-[11px] uppercase tracking-wide text-text-dim">{label}</div>
      <div className={`mt-0.5 text-[14px] font-medium ${colored ? toneTextClass[tone] : "text-text-main"}`}>
        {value}
      </div>
      {meterPct != null ? (
        <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-high/80">
          <div
            className={`h-full rounded-full ${ratingBarClass(meterTone)}`}
            style={{ width: `${Math.max(4, Math.min(100, meterPct))}%` }}
          />
        </div>
      ) : null}
    </div>
  )
}

function BatchInsightsPanel({
  aggregation,
  category,
}: {
  aggregation: HarborJobAggregation
  category: ReportingCategory
}) {
  const contexts = aggregation.contexts ?? []
  const trialCount = aggregation.coverage.trialCount
  if (contexts.length === 0 && aggregation.fields.length === 0) return null

  // Survey stats live in the coverage row — no second band.
  if (category === "survey") return null

  return (
    <div className="mt-3 space-y-3 rounded-xl border border-primary/30 bg-primary/10 p-3">
      <div>
        <div className="flex items-center gap-2 text-[13px] font-medium uppercase tracking-wide text-primary">
          <Sym name="insights" size={14} />
          Batch insights
        </div>
        <p className="mt-1 text-[13px] leading-relaxed text-text-variant">
          Compact signals first; tables below expand the top outcome mixes. Open the detailed report for
          per-context evidence.
        </p>
      </div>
      <ContractBatchInsights aggregation={aggregation} trialCount={trialCount} category={category} />
    </div>
  )
}

function ContractBatchInsights({
  aggregation,
  trialCount,
  category,
}: {
  aggregation: HarborJobAggregation
  trialCount: number
  category: ReportingCategory
}) {
  const contexts = aggregation.contexts ?? []
  // Tables own the top categorical distributions; chips only show signals not expanded below.
  const distributionBreakdowns =
    category === "survey" ? [] : buildDistributionBreakdowns(contexts, trialCount, category)
  const breakdownFacetKeys = new Set(distributionBreakdowns.map((breakdown) => breakdown.dimensionKey))
  const chips = buildHeadlineInsightChips(contexts, aggregation.coverage, category, {
    excludeFacetKeys: breakdownFacetKeys,
  })
  const scoreStats = category === "survey" ? [] : buildScoreMetricStrip(contexts)
  const snapshotFields = buildPersonaSnapshotFields(contexts)
  const showSnapshots = category !== "survey" && trialCount <= 8 && snapshotFields.length > 0

  return (
    <>
      {chips.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {chips.map((chip) => (
            <InsightChip key={`${chip.label}-${chip.value}`} {...chip} />
          ))}
        </div>
      ) : null}

      {distributionBreakdowns.map((breakdown) => (
        <DistributionBreakdownTable
          key={`${breakdown.contextLabel}-${breakdown.dimensionLabel}`}
          breakdown={breakdown}
          trialCount={trialCount}
        />
      ))}

      {scoreStats.length > 0 ? (
        <ScoreMetricStrip stats={scoreStats} trialCount={trialCount} />
      ) : null}

      {showSnapshots ? <PersonaTextSnapshots fields={snapshotFields} trialCount={trialCount} /> : null}
    </>
  )
}

function ScoreMetricStrip({ stats, trialCount }: { stats: string[]; trialCount: number }) {
  return (
    <div className="overflow-hidden rounded-lg border border-outline/40 bg-surface/45 px-3 py-2.5">
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[14px] text-text-main">
        {stats.map((stat) => (
          <span key={stat}>{stat}</span>
        ))}
        <span className="text-text-dim">· {trialCount} personas</span>
      </div>
    </div>
  )
}

function DistributionBreakdownTable({
  breakdown,
  trialCount,
}: {
  breakdown: DistributionBreakdown
  trialCount: number
}) {
  const detailSamples = breakdown.detailField?.textual?.samples ?? []
  const unanimousDetail =
    detailSamples.length > 0 && new Set(detailSamples.map((sample) => sample.trim())).size === 1
      ? detailSamples[0]?.trim()
      : null

  return (
    <div className="overflow-hidden rounded-lg border border-outline/40 bg-surface/45">
      <div className="border-b border-outline/35 bg-surface/30 px-3 py-1.5">
        <div className="text-[12px] font-medium uppercase tracking-wide text-text-dim">{breakdown.contextLabel}</div>
      </div>
      <div className="grid gap-2 border-b border-outline/35 bg-surface/30 px-3 py-1.5 text-[11px] uppercase tracking-wide text-text-dim sm:grid-cols-[minmax(0,1.4fr)_auto_auto_auto]">
        <span>{breakdown.dimensionLabel}</span>
        <span className="sm:text-right">Count</span>
        <span className="sm:text-right">Share</span>
        <span className="sm:text-right">{breakdown.detailField?.label ?? "Detail"}</span>
      </div>
      <div className="divide-y divide-outline/30">
        {breakdown.rows.map((row) => (
          <div
            key={row.label}
            className="grid gap-2 px-3 py-2.5 sm:grid-cols-[minmax(0,1.4fr)_auto_auto_auto]"
          >
            <div className="min-w-0">
              <div className="truncate text-[15px] font-medium text-text-main">{row.label}</div>
            </div>
            <div className="text-[14px] font-mono text-text-main sm:text-right">{row.count}</div>
            <div className="text-[13px] text-text-dim sm:text-right">
              {Math.round((row.count / Math.max(trialCount, 1)) * 100)}%
            </div>
            <div className="truncate text-[13px] text-text-variant sm:text-right">
              {unanimousDetail ?? (detailSamples.length > 0 ? "varies" : "—")}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function PersonaTextSnapshots({
  fields,
  trialCount,
}: {
  fields: AggregationField[]
  trialCount: number
}) {
  const rowCount = Math.max(...fields.map((field) => field.textual?.samples?.length ?? 0), 0)
  if (rowCount === 0) return null
  const visibleRows = trialCount <= 8 ? rowCount : Math.min(3, rowCount)

  return (
    <div className="overflow-hidden rounded-lg border border-outline/40 bg-surface/45">
      <div className="border-b border-outline/35 px-3 py-2 text-[12px] font-medium uppercase tracking-wide text-text-dim">
        Persona voice
      </div>
      <div className="divide-y divide-outline/30">
        {Array.from({ length: visibleRows }, (_, index) => (
          <div key={`snapshot-${index}`} className="space-y-2 px-3 py-2.5">
            <div className="font-mono text-[12px] uppercase tracking-wide text-text-dim">
              Persona {index + 1}
            </div>
            {fields.map((field) => {
              const sample = field.textual?.samples?.[index]
              if (!sample) return null
              return (
                <div key={`${field.key}-${index}`}>
                  <div className="text-[12px] uppercase tracking-wide text-text-dim">{field.label}</div>
                  <p className="mt-0.5 text-[14px] leading-relaxed text-text-main">
                    {previewText(sample, 260)}
                  </p>
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

function CompactContextGroup({ contexts }: { contexts: AggregationContext[] }) {
  const [open, setOpen] = useState(false)
  if (contexts.length === 0) return null

  return (
    <section className="overflow-hidden rounded-xl border border-outline/45 bg-surface/30">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-surface/25 ${FOCUS_RING}`}
      >
        <div>
          <div className="text-[15px] font-medium text-text-main">Execution checks</div>
          <p className="mt-1 text-[13px] text-text-dim">
            {contexts.length} contexts · all personas agreed
          </p>
        </div>
        <span className="inline-flex items-center gap-1 text-[12px] uppercase tracking-wide text-text-dim">
          {open ? "Hide" : "Show"}
          <Sym name={open ? "expand_less" : "expand_more"} size={14} />
        </span>
      </button>
      <div className="divide-y divide-outline/30 border-t border-outline/35">
        {(open ? contexts : contexts.slice(0, 4)).map((context) => {
          const primary = primaryFacetForContext(context)
          const value = primary?.categorical?.counts?.[0]?.value ?? "—"
          return (
            <div key={context.key} className="flex items-center gap-3 px-4 py-2.5">
              <Sym name="check_circle" size={16} className="shrink-0 text-secondary" fill={1} />
              <div className="min-w-0 flex-1">
                <div className="text-[14px] font-medium text-text-main">{context.label}</div>
                {contextTypeDescription(context) ? (
                  <div className="truncate text-[12px] text-text-dim">{contextTypeDescription(context)}</div>
                ) : null}
              </div>
              <div className="shrink-0 text-right">
                <div className="text-[14px] font-medium text-text-main">{value}</div>
                <div className="font-mono text-[12px] text-text-dim">{primary?.presentCount ?? 0}/{primary?.presentCount ?? 0}</div>
              </div>
            </div>
          )
        })}
      </div>
      {!open && contexts.length > 4 ? (
        <div className="border-t border-outline/35 px-4 py-2 text-[13px] text-text-dim">
          +{contexts.length - 4} more unanimous checks
        </div>
      ) : null}
    </section>
  )
}


function readAgentModel(config: Record<string, unknown> | null): string | null {
  const agents = Array.isArray(config?.agents) ? config.agents : [];
  const firstAgent =
    agents.length > 0 && agents[0] && typeof agents[0] === "object"
      ? (agents[0] as Record<string, unknown>)
      : null;
  return typeof firstAgent?.model_name === "string" ? firstAgent.model_name : null;
}

function readTaskPathFromConfig(config: Record<string, unknown> | null): string | null {
  const tasks = Array.isArray(config?.tasks) ? config.tasks : [];
  const first =
    tasks.length > 0 && tasks[0] && typeof tasks[0] === "object"
      ? (tasks[0] as Record<string, unknown>)
      : null;
  return typeof first?.path === "string" && first.path.trim() ? first.path.trim() : null;
}

function personaPoolFromPath(personaPath: string | null | undefined): string | null {
  if (!personaPath) return null;
  const parts = personaPath.replace(/\\/g, "/").split("/").filter(Boolean);
  if (parts.length < 2) return null;
  const leaf = parts[parts.length - 1] ?? "";
  const parent = parts[parts.length - 2] ?? "";
  if (/^persona_\d+/i.test(leaf) || leaf.endsWith(".yaml") || leaf.endsWith(".yml")) {
    return parent || null;
  }
  return parent || leaf || null;
}

function readPersonaPool(config: Record<string, unknown> | null): string | null {
  const agents = Array.isArray(config?.agents) ? config.agents : [];
  for (const agent of agents) {
    if (!agent || typeof agent !== "object") continue;
    const kwargs = (agent as Record<string, unknown>).kwargs;
    if (!kwargs || typeof kwargs !== "object") continue;
    const personaPath = (kwargs as Record<string, unknown>).persona_path;
    if (typeof personaPath === "string" && personaPath.trim()) {
      return personaPoolFromPath(personaPath.trim());
    }
  }
  return null;
}

function buildPersonaRoster(trials: HarborJobDetail["trials"] | undefined): BatchReportPdfPersona[] {
  const seen = new Set<string>();
  const personas: BatchReportPdfPersona[] = [];
  for (const trial of trials ?? []) {
    const idRaw = (trial.personaId ?? "").trim();
    const id = idRaw ? personaDisplayId(idRaw) : "";
    const name = personaPrimaryName(trial.personaName, trial.personaId);
    const key = idRaw || name || trial.trialName;
    if (!key || seen.has(key)) continue;
    seen.add(key);
    personas.push({
      id: id || key,
      name: name || key,
    });
  }
  return personas.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
}

function buildCoverageSnapshot(
  aggregation: HarborJobAggregation | null | undefined,
): BatchReportPdfSnapshot[] {
  if (!aggregation) return [];
  const coverage = aggregation.coverage;
  const snap: BatchReportPdfSnapshot[] = [
    {
      label: "Trials",
      value: String(coverage.completedTrials),
      hint: coverage.trialCount !== coverage.completedTrials ? `/ ${coverage.trialCount}` : undefined,
    },
  ];
  if (coverage.pendingTrials > 0) {
    snap.push({ label: "Pending", value: String(coverage.pendingTrials) });
  }
  if (coverage.completedWithoutArtifactTrials > 0) {
    snap.push({
      label: "No artifact",
      value: String(coverage.completedWithoutArtifactTrials),
    });
  }
  const reportingStatus = aggregation.reporting?.status;
  if (reportingStatus && reportingStatus !== "not_applicable") {
    snap.push({ label: "Reporting", value: reportingStatus });
  }
  return snap.slice(0, 4);
}

function normalizePersonaStrategy(
  strategy: TaskPersonaStrategy | null | undefined,
): BatchReportPdfPersonaStrategy | null {
  if (!strategy) return null;
  return {
    mode: strategy.defaultMode ?? null,
    sampleSizePerValueGroup: strategy.sampleSizePerValueGroup ?? null,
    sampleSize: strategy.sampleSize ?? null,
    seed: strategy.seed ?? null,
    stratifyFields: strategy.stratifyFields ?? undefined,
    dimensionFilters: strategy.dimensionFilters ?? undefined,
    sources: strategy.sources ?? undefined,
  };
}

async function enrichBatchReportPdfMeta(meta: BatchReportPdfMeta): Promise<BatchReportPdfMeta> {
  if (!meta.taskPath) return meta;
  try {
    const detail = await api.getTaskDetail(meta.taskPath);
    const instrumentTitle = detail.questionnaire?.title?.trim() || null;
    const instructionPlain = plainTextFromMarkdown(detail.instructionMarkdown);
    const contextPlain = plainTextFromMarkdown(detail.contextMarkdown);
    const description =
      (detail.description || "").trim() ||
      instructionPlain
        .split(/\n\n+/)
        .map((p) => p.trim())
        .find((p) => p.length > 40 && !/^how to answer/i.test(p)) ||
      null;
    return {
      ...meta,
      taskTitle: instrumentTitle || detail.title?.trim() || meta.taskTitle,
      taskDescription: description || meta.taskDescription || null,
      taskContext: contextPlain || meta.taskContext || null,
      taskInstruction: instructionPlain || meta.taskInstruction || null,
      taskDomain: detail.domain?.trim() || meta.taskDomain || null,
      taskDifficulty: detail.difficulty?.trim() || meta.taskDifficulty || null,
      taskTags: Array.isArray(detail.tags) && detail.tags.length ? detail.tags.map(String) : meta.taskTags,
      taskName: detail.taskName?.trim() || meta.taskName || null,
      applicationType: meta.applicationType || detail.metaType || null,
      personaStrategy: normalizePersonaStrategy(detail.personaStrategy) ?? meta.personaStrategy,
    };
  } catch {
    return meta;
  }
}

function buildBatchReportPdfMeta(jobName: string, job: HarborJobDetail | undefined): BatchReportPdfMeta {
  const launch = job?.launch ?? null;
  const result = (job?.result ?? null) as Record<string, unknown> | null;
  const config = (job?.config ?? null) as Record<string, unknown> | null;

  let status = launch?.status ?? null;
  if (!status) {
    if (result?.finished_at) status = "completed";
    else if (result?.started_at) status = "running";
  }

  const started = typeof result?.started_at === "string" ? result.started_at : null;
  const finished = typeof result?.finished_at === "string" ? result.finished_at : null;
  const runWindow = started || finished ? `${started || "-"} -> ${finished || "-"}` : null;
  const generatedAt =
    typeof job?.aggregation?.generatedAt === "string" && job.aggregation.generatedAt
      ? job.aggregation.generatedAt
      : null;
  const parallelismRaw = config?.n_concurrent_trials;
  const parallelism =
    typeof parallelismRaw === "number" && Number.isFinite(parallelismRaw)
      ? Math.max(1, Math.floor(parallelismRaw))
      : typeof parallelismRaw === "string" && parallelismRaw.trim() !== "" && Number.isFinite(Number(parallelismRaw))
        ? Math.max(1, Math.floor(Number(parallelismRaw)))
        : null;

  const taskPath = (job?.taskPath ?? readTaskPathFromConfig(config) ?? "").trim() || null;
  const taskTitle =
    (job?.taskTitle ?? "").trim() ||
    humanizePathLeaf(taskPath) ||
    null;
  const applicationType =
    (job?.applicationType ?? job?.metaType ?? "").trim() ||
    (taskPath && /\/survey[_-]/i.test(taskPath) ? "survey" : null);
  const personas = buildPersonaRoster(job?.trials);

  return {
    jobName,
    status,
    configPath: launch?.configPath ?? null,
    agentModel: readAgentModel(config),
    parallelism,
    runWindow,
    startedAt: started,
    finishedAt: finished,
    generatedAt,
    applicationType,
    taskPath,
    taskTitle,
    taskDescription: (job?.description ?? "").trim() || null,
    taskDomain: (job?.domain ?? "").trim() || null,
    taskDifficulty: (job?.difficulty ?? "").trim() || null,
    taskTags: Array.isArray(job?.tags) ? job.tags.map(String) : undefined,
    taskName: (job?.taskName ?? "").trim() || null,
    personaPool: readPersonaPool(config),
    personaStrategy: normalizePersonaStrategy(job?.personaStrategy),
    personas,
    snapshot: buildCoverageSnapshot(job?.aggregation),
  };
}

function shortModelLabel(model: string): string {
  return model.split("/").pop()?.trim() || model;
}

function formatRunDuration(startedAt: string | null | undefined, finishedAt: string | null | undefined): string | null {
  if (!startedAt || !finishedAt) return null;
  const start = Date.parse(startedAt);
  const end = Date.parse(finishedAt);
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return null;
  const sec = Math.round((end - start) / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  const rem = sec % 60;
  if (min < 60) return rem ? `${min}m ${rem}s` : `${min}m`;
  const hr = Math.floor(min / 60);
  const minRem = min % 60;
  return minRem ? `${hr}h ${minRem}m` : `${hr}h`;
}

/** Compact absolute timestamp for report chrome (`Jul 13, 00:38:25`). */
function formatTimestamp(iso: string | null | undefined, withSeconds = false): string | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return new Date(t).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" as const } : {}),
    hour12: false,
  });
}

function BatchReportMetaFact({
  label,
  value,
  title,
}: {
  label: string;
  value: string;
  title?: string;
}) {
  return (
    <div className="min-w-0 bg-surface/80 px-3 py-2.5" title={title}>
      <div className="text-[11px] font-medium uppercase tracking-wide text-text-dim">{label}</div>
      <div className="mt-1 text-[13px] leading-snug text-text-main">{value}</div>
    </div>
  );
}

function BatchReportMetaByline({ meta }: { meta: BatchReportPdfMeta }) {
  const model = meta.agentModel ? shortModelLabel(meta.agentModel) : null;
  const duration = formatRunDuration(meta.startedAt, meta.finishedAt);
  const runStart = formatTimestamp(meta.startedAt, true);
  const runEnd = formatTimestamp(meta.finishedAt, true);
  const reportAt = formatTimestamp(meta.generatedAt, true);

  let runValue: string | null = null;
  if (runStart && runEnd) {
    runValue = duration ? `${runStart} → ${runEnd} · ${duration}` : `${runStart} → ${runEnd}`;
  } else if (runStart || runEnd) {
    runValue = duration ? `${runStart ?? runEnd} · ${duration}` : (runStart ?? runEnd);
  } else if (duration) {
    runValue = `Duration ${duration}`;
  }

  const facts: Array<{ label: string; value: string; title?: string }> = [];
  if (meta.taskTitle || meta.taskPath) {
    facts.push({
      label: "Task",
      value: meta.taskTitle || humanizePathLeaf(meta.taskPath) || meta.taskPath || "",
      title: meta.taskPath ?? undefined,
    });
  }
  if (meta.personas && meta.personas.length > 0) {
    facts.push({
      label: "Personas",
      value:
        meta.personaPool != null
          ? `${meta.personas.length} · ${meta.personaPool}`
          : String(meta.personas.length),
      title: meta.personas.map((p) => `${p.id} ${p.name}`).join(", "),
    });
  }
  if (model) {
    facts.push({
      label: "Agent model",
      value: model,
      title: meta.agentModel ?? undefined,
    });
  }
  if (meta.parallelism != null) {
    facts.push({
      label: "Parallelism",
      value: String(meta.parallelism),
      title: `${meta.parallelism} concurrent trials`,
    });
  }
  if (runValue) {
    facts.push({
      label: "Run",
      value: runValue,
      title: meta.runWindow ?? undefined,
    });
  }
  if (reportAt) {
    facts.push({
      label: "Report",
      value: reportAt,
      title: meta.generatedAt ?? undefined,
    });
  }

  if (facts.length === 0) return null;

  const colClass =
    facts.length >= 5
      ? "grid-cols-1 sm:grid-cols-2 xl:grid-cols-3"
      : facts.length === 4
        ? "grid-cols-1 sm:grid-cols-2 xl:grid-cols-4"
        : facts.length === 3
          ? "grid-cols-1 sm:grid-cols-3"
          : facts.length === 2
            ? "grid-cols-1 sm:grid-cols-2"
            : "grid-cols-1";

  return (
    <div className={`mt-3 grid gap-px overflow-hidden rounded-lg border border-outline/40 bg-outline/40 ${colClass}`}>
      {facts.map((fact) => (
        <BatchReportMetaFact key={fact.label} label={fact.label} value={fact.value} title={fact.title} />
      ))}
    </div>
  );
}

function AggregationDashboard({
  aggregation,
  applicationType,
  pdfMeta,
}: {
  aggregation: HarborJobAggregation;
  applicationType?: string | null;
  pdfMeta: BatchReportPdfMeta;
}) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const allContexts = useMemo(() => aggregation.contexts ?? [], [aggregation.contexts]);
  const category = useMemo(
    () => inferReportingCategory(allContexts, applicationType),
    [allContexts, applicationType],
  );
  const { headline: headlineContexts, compact: compactContexts } = useMemo(
    () => splitContexts(allContexts, category),
    [allContexts, category],
  );
  const contexts = allContexts;
  const numerical = aggregation.fields.filter((field) => field.kind === "numerical");
  const categorical = aggregation.fields.filter((field) => field.kind === "categorical");
  const textual = aggregation.fields.filter((field) => field.kind === "textual");
  const coverage = aggregation.coverage;
  const reporting = aggregation.reporting ?? null;
  const reportingChip = reportingSummary(reporting);
  const hasDetails = contexts.length > 0 || numerical.length > 0 || categorical.length > 0 || textual.length > 0;
  const isSurvey = category === "survey";
  const questionCount = allContexts.filter((context) => context.contextType === "question_response").length;
  const detailCount = isSurvey
    ? questionCount || contexts.length
    : contexts.length > 0
      ? contexts.length
      : numerical.length + categorical.length + textual.length;
  const detailLabel = isSurvey ? "questions" : contexts.length > 0 ? "contexts" : "fields";
  const trialHint =
    coverage.pendingTrials > 0
      ? `${coverage.completedTrials}/${coverage.trialCount} complete`
      : `${coverage.completedTrials} completed`;
  const showArtifactsChip =
    coverage.completedWithoutArtifactTrials > 0 || coverage.artifactReadyTrials !== coverage.trialCount;
  const showPendingChip = coverage.pendingTrials > 0;
  const surveyStats = useMemo(
    () => (isSurvey ? buildSurveyCoverageStats(contexts, coverage) : []),
    [contexts, coverage, isSurvey],
  );
  const surveyTypeCounts = useMemo(
    () => (isSurvey ? buildSurveyQuestionTypeCounts(contexts) : []),
    [contexts, isSurvey],
  );
  const showReportingBadge =
    reporting != null && (reporting.status ?? "").trim().toLowerCase() !== "not_applicable";

  const downloadPdf = async () => {
    if (downloadBusy) return;
    setDownloadBusy(true);
    setCaptureError(null);
    try {
      flushSync(() => {
        if (hasDetails) setOpen(true);
      });
      await new Promise<void>((resolve) => {
        requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
      });
      await new Promise((resolve) => window.setTimeout(resolve, 150));
      const root = rootRef.current;
      if (!root) {
        throw new Error("Batch report is not ready to capture.");
      }
      const enriched = await enrichBatchReportPdfMeta({
        ...pdfMeta,
        applicationType: pdfMeta.applicationType ?? applicationType ?? null,
        snapshot:
          pdfMeta.snapshot && pdfMeta.snapshot.length > 0
            ? pdfMeta.snapshot
            : buildCoverageSnapshot(aggregation),
      });
      await exportBatchReportPdf(root, enriched);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not download PDF report.";
      setCaptureError(message);
    } finally {
      setDownloadBusy(false);
    }
  };

  return (
    <div ref={rootRef} className="mb-5 space-y-5" data-batch-report-root>
      <StudioGlassPanel className="bg-surface/95 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2 text-[14px] font-medium text-text-main">
            <Sym name="analytics" size={16} className="shrink-0 text-primary" />
            Persona-task batch report
          </div>
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              data-pdf-ignore
              onClick={() => {
                void downloadPdf();
              }}
              disabled={downloadBusy}
              className={`inline-flex items-center gap-1.5 rounded-md border border-outline/50 bg-surface/60 px-2.5 py-1 text-[12px] font-medium text-text-variant transition hover:border-primary/40 hover:bg-surface hover:text-text-main disabled:opacity-55 ${FOCUS_RING}`}
            >
              <Sym name="download" size={14} />
              {downloadBusy ? "Preparing PDF…" : "Download PDF"}
            </button>
            {showReportingBadge ? (
              <span
                className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[12px] uppercase tracking-wide ${reportingStatusClassName(
                  reporting.status,
                )}`}
              >
                <Sym
                  name={reporting.status === "queued" || reporting.status === "running" ? "autorenew" : "analytics"}
                  size={12}
                  className={reporting.status === "queued" || reporting.status === "running" ? "animate-rb-spin" : ""}
                />
                LLM report · {reportingStatusLabel(reporting.status)}
              </span>
            ) : null}
          </div>
        </div>

        <BatchReportMetaByline meta={pdfMeta} />

        {captureError ? (
          <p className="mt-2 text-[13px] text-danger" data-pdf-ignore>
            {captureError}
          </p>
        ) : null}

        <div className="mt-3 flex flex-wrap gap-2">
          <CoverageTile
            label={isSurvey ? "Personas" : "Trials"}
            value={coverage.trialCount}
            hint={trialHint}
          />
          <CoverageTile
            label={isSurvey ? "Questions" : "Contexts"}
            value={isSurvey ? questionCount || contexts.length : contexts.length}
            hint={
              isSurvey
                ? "In this instrument"
                : contexts.length > 0
                  ? "Structured context view"
                  : "Fallback field view"
            }
          />
          {isSurvey && surveyTypeCounts.length > 0 ? (
            <SurveyQuestionTypesTile counts={surveyTypeCounts} />
          ) : null}
          {isSurvey
            ? surveyStats.map((stat) => (
                <CoverageTile key={`${stat.label}-${stat.value}`} label={stat.label} value={stat.value} hint={stat.hint} />
              ))
            : null}
          {showArtifactsChip ? (
            <CoverageTile
              label="Artifacts"
              value={coverage.artifactReadyTrials}
              hint={coverage.completedWithoutArtifactTrials > 0 ? `${coverage.completedWithoutArtifactTrials} missing` : "Ready"}
            />
          ) : null}
          {showPendingChip ? <CoverageTile label="Pending" value={coverage.pendingTrials} hint="Still running" /> : null}
          {!isSurvey && reportingChip ? (
            <CoverageTile label="LLM report" value={reportingChip.value} hint={reportingChip.hint} />
          ) : null}
        </div>
        {reporting?.error ? (
          <p className="mt-3 text-[14px] leading-relaxed text-danger">{reporting.error}</p>
        ) : null}
        {!isSurvey && contexts.length > 0 ? (
          <BatchInsightsPanel aggregation={aggregation} category={category} />
        ) : null}
        {hasDetails ? (
          <div
            data-pdf-ignore
            className={`space-y-2 ${contexts.length > 0 ? "mt-3 border-t border-outline/35 pt-3" : "mt-3"}`}
          >
            <button
              type="button"
              onClick={() => setOpen((value) => !value)}
              aria-expanded={open}
              className={`glow flex w-full items-center justify-between gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors ${FOCUS_RING} ${
                open
                  ? "border-primary bg-primary-dim text-on-primary hover:bg-primary"
                  : "border-primary bg-primary text-on-primary hover:bg-primary-dim"
              }`}
            >
              <div className="min-w-0">
                <div className="text-[14px] font-medium text-on-primary">
                  {open
                    ? isSurvey
                      ? "Hide per-question report"
                      : "Hide detailed report"
                    : isSurvey
                      ? "Show per-question report"
                      : "Show detailed report"}
                </div>
                <div className="mt-0.5 text-[13px] leading-relaxed text-on-primary/80">
                  {isSurvey
                    ? `${detailCount} ${detailLabel} · answer mix, open Reasons for quotes`
                    : `${detailCount} ${detailLabel} · signals, grouped summaries, and evidence`}
                </div>
              </div>
              <div className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-white/15 bg-white/10 px-2.5 py-1.5 text-[13px] text-on-primary">
                <span>{open ? "Collapse" : "Expand"}</span>
                <Sym name={open ? "expand_less" : "expand_more"} size={16} />
              </div>
            </button>
          </div>
        ) : null}
      </StudioGlassPanel>

      {open ? (
        contexts.length > 0 ? (
          <StudioGlassPanel className="overflow-hidden bg-surface/95">
            <SectionHeader
              title={isSurvey ? "Per-question report" : "Detailed contexts"}
              subtitle={
                isSurvey
                  ? "Answer mix per question. Open Reasons for quotes."
                  : "Decision and feedback first. Expand any card for signals, grouped summaries, and evidence."
              }
            />
            <div className="space-y-3 p-4">
              {compactContexts.length > 0 ? <CompactContextGroup contexts={compactContexts} /> : null}
              {headlineContexts
                .filter((context) => !(isSurvey && context.contextType === "trial_summary"))
                .map((context) =>
                  isSurvey && context.contextType === "question_response" ? (
                    <SurveyQuestionCard key={context.key} context={context} />
                  ) : context.contextType === "user_feedback" || context.contextType === "feedback" ? (
                    <UserFeedbackBatchCard key={context.key} context={context} />
                  ) : (
                    <ContextCard key={context.key} context={context} />
                  ),
                )}
            </div>
          </StudioGlassPanel>
        ) : (
          <FlatAggregationFallback
            numerical={numerical}
            categorical={categorical}
            textual={textual}
          />
        )
      ) : null}
    </div>
  );
}

function scoreFacetsForContext(context: AggregationContext): AggregationField[] {
  return context.facets.filter(
    (facet) =>
      facet.role === "score" ||
      /confidence|score|rating/i.test(facet.key) ||
      /confidence|score|rating/i.test(facet.label),
  )
}

function resolveSurveyQuestionType(
  context: AggregationContext,
  primary: AggregationField | null,
): "likert" | "single_choice" | "multi_choice" | "free_text" | "unknown" {
  const raw = String(context.questionType ?? "").trim().toLowerCase()
  if (raw === "likert" || raw === "single_choice" || raw === "multi_choice" || raw === "free_text") {
    return raw
  }
  // Legacy artifacts without questionType — infer from facet kind.
  if (primary?.kind === "numerical") return "likert"
  if (primary?.kind === "categorical") return "single_choice"
  if (primary?.kind === "textual") return "free_text"
  return "unknown"
}

function surveyAnswerItems(
  context: AggregationContext,
  primary: AggregationField | null,
): Array<CountBarItem & { id?: string }> {
  if (!primary || primary.kind !== "categorical") return []
  const counts = primary.categorical?.counts ?? []
  const byId = new Map(counts.map((entry) => [entry.value, entry.count]))
  const options = context.choiceOptions ?? []
  if (options.length > 0) {
    const known = new Set(options.map((option) => option.id))
    const rows = options.map((option) => ({
      id: option.id,
      label: option.label?.trim() || formatBucketLabel(option.id),
      count: byId.get(option.id) ?? 0,
    }))
    // Keep unexpected values that aren't in the questionnaire inventory.
    for (const entry of counts) {
      if (!known.has(entry.value)) {
        rows.push({
          id: entry.value,
          label: formatBucketLabel(entry.value),
          count: entry.count,
        })
      }
    }
    return rows
  }
  return counts.map((entry) => ({
    id: entry.value,
    label: formatBucketLabel(entry.value),
    count: entry.count,
  }))
}

function ChoiceCompositionChart({
  items,
  respondentCount,
  multi = false,
}: {
  items: Array<CountBarItem & { id?: string }>
  respondentCount: number
  multi?: boolean
}) {
  const ranked = [...items].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
  const denom = Math.max(respondentCount, 1)
  const peak = Math.max(...ranked.map((item) => item.count), 1)
  const leader = ranked.find((item) => item.count > 0) ?? ranked[0]
  const leaderShare = leader ? Math.round((leader.count / denom) * 100) : 0
  const chosen = ranked.filter((item) => item.count > 0).length
  const consensus =
    chosen <= 1 && (leader?.count ?? 0) > 0
      ? "Unanimous"
      : leaderShare >= 60
        ? "Clear leader"
        : "Split opinions"

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div className="min-w-0 text-[14px] text-text-main">
          {leader && leader.count > 0 ? (
            <>
              Top pick <span className="font-medium">{leader.label}</span>
              <span className="font-mono text-text-dim">
                {" "}
                · {leader.count}/{denom} · {leaderShare}%
              </span>
            </>
          ) : (
            "No choices yet"
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {multi ? (
            <span className="text-[12px] text-text-dim">Multi-select · shares can exceed 100%</span>
          ) : null}
          <span className="rounded-md border border-outline/40 bg-surface/50 px-2 py-1 text-[13px] text-text-variant">
            {consensus}
          </span>
        </div>
      </div>

      <div className="rounded-lg border border-outline/40 bg-surface/40 px-3 py-3">
        <div className="space-y-2.5">
          {ranked.map((item, index) => {
            const share = Math.round((item.count / denom) * 100)
            const widthPct = item.count > 0 ? Math.max(6, Math.round((item.count / peak) * 100)) : 0
            const tone =
              item.count <= 0
                ? "bg-outline/25"
                : index === 0
                  ? "bg-secondary/80"
                  : index === 1
                    ? "bg-primary/65"
                    : index === 2
                      ? "bg-warn/55"
                      : "bg-primary/40"
            return (
              <div key={`${item.id ?? item.label}-${item.count}`} className="space-y-1">
                <div className="flex items-start justify-between gap-3 text-[14px]">
                  <span className={`min-w-0 leading-snug ${item.count > 0 ? "text-text-main" : "text-text-dim"}`}>
                    {item.label}
                  </span>
                  <span className="shrink-0 font-mono text-text-dim">
                    {item.count}
                    {item.count > 0 ? <span className="text-text-variant"> · {share}%</span> : null}
                  </span>
                </div>
                <div className="h-2.5 rounded-full bg-surface-high/90">
                  <div
                    className={`h-2.5 rounded-full ${tone}`}
                    style={{ width: `${widthPct}%` }}
                    title={`${item.label}: ${item.count}`}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

type FreeTextTheme = { label: string; count: number; samples: string[] }

function freeTextThemes(primary: AggregationField | null): FreeTextTheme[] {
  const counts = primary?.textual?.counts ?? []
  // Trust backend TF-IDF clustering — do not re-cluster with client heuristics.
  if (counts.length === 0) return []
  return counts
    .filter((entry) => entry.value.trim().length > 0 && entry.count > 0)
    .slice(0, 8)
    .map((entry) => {
      const label = entry.value.trim()
      const samples = (entry.samples ?? [label]).map((sample) => sample.trim()).filter(Boolean)
      return {
        label,
        count: entry.count,
        samples: samples.length > 0 ? samples.slice(0, 3) : [label],
      }
    })
}

function freeTextSignalTags(judges: AggregationJudge[]): FreeTextTheme[] {
  const totals = new Map<string, { label: string; count: number; samples: string[] }>()
  for (const judge of judges) {
    const defs = new Map((judge.signals ?? []).map((signal) => [signal.key, signal.label || signal.key]))
    for (const bucket of judge.buckets ?? []) {
      for (const signal of bucket.signals ?? []) {
        if (!signal.present) continue
        const label = defs.get(signal.key) ?? signal.key
        const current = totals.get(signal.key)
        const quoteSamples = (bucket.samples ?? []).map((sample) => sample.trim()).filter(Boolean)
        if (current) {
          current.count += bucket.count || 1
          for (const sample of quoteSamples) {
            if (!current.samples.includes(sample)) current.samples.push(sample)
          }
        } else {
          totals.set(signal.key, {
            label,
            count: bucket.count || 1,
            samples: quoteSamples.slice(0, 3),
          })
        }
      }
    }
  }
  return [...totals.values()]
    .map((theme) => ({
      ...theme,
      samples: theme.samples.length > 0 ? theme.samples.slice(0, 3) : [theme.label],
    }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
}

function freeTextThemeSummary(present: number, themes: FreeTextTheme[], uniqueHint: number): string | null {
  if (present <= 0) return null
  if (themes.length === 0) {
    return uniqueHint > 0
      ? `${present} written answer${present === 1 ? "" : "s"} · ${uniqueHint} distinct theme${uniqueHint === 1 ? "" : "s"}`
      : `${present} written answer${present === 1 ? "" : "s"}`
  }
  if (themes.length === 1) {
    return `All ${present} answers converge on one theme: "${themes[0].label}".`
  }

  const primary = themes[0]
  const secondary = themes[1]
  const smaller = themes.slice(2)
  const smallerAnswers = smaller.reduce((sum, theme) => sum + theme.count, 0)

  if (primary.count + secondary.count >= Math.max(2, Math.round(present * 0.65))) {
    let summary = `Across ${present} answers, the dominant themes are "${primary.label}" (${primary.count}) and "${secondary.label}" (${secondary.count}).`
    if (smallerAnswers > 0) {
      summary = `${summary.slice(0, -1)}, with ${smallerAnswers} more in ${smaller.length} smaller theme${smaller.length === 1 ? "" : "s"}.`
    }
    return summary
  }

  let summary = `Across ${present} answers, responses form ${themes.length} themes. The largest is "${primary.label}" (${primary.count}), followed by "${secondary.label}" (${secondary.count}).`
  if (smallerAnswers > 0) {
    summary += ` The remaining ${smallerAnswers} answers fall into ${smaller.length} smaller theme${smaller.length === 1 ? "" : "s"}.`
  }
  return summary
}

function freeTextCoverage(primary: AggregationField | null): {
  present: number
  unique: number
  summary: string | null
  themes: FreeTextTheme[]
} {
  const present = primary?.presentCount ?? 0
  const themes = freeTextThemes(primary)
  const unique = themes.length || primary?.textual?.uniqueCount || 0
  const rawSummary = primary?.textual?.summary?.trim() || null
  // Prefer LLM/reporting summaries; otherwise roll up from clustered themes.
  const summary =
    rawSummary && !isHeuristicAggregationSummary(rawSummary)
      ? rawSummary
      : freeTextThemeSummary(present, themes, unique)
  return { present, unique, summary, themes }
}

function FreeTextThemeTags({ themes, label }: { themes: FreeTextTheme[]; label: string }) {
  if (themes.length === 0) return null
  return (
    <div className="space-y-1.5">
      <div className="text-[12px] font-medium uppercase tracking-wide text-text-dim">{label}</div>
      <div className="flex flex-wrap gap-1.5">
        {themes.map((theme) => (
          <span
            key={`${theme.label}-${theme.count}`}
            className="inline-flex max-w-full items-start gap-1.5 rounded-lg border border-outline/45 bg-surface/70 px-2.5 py-1.5 text-[13px] leading-snug text-text-main"
          >
            <span className="min-w-0 whitespace-normal break-words">{theme.label}</span>
            <span className="shrink-0 font-mono text-text-dim">{theme.count}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

function FreeTextThemeExamples({ themes }: { themes: FreeTextTheme[] }) {
  if (themes.length === 0) return null
  return (
    <div className="space-y-3">
      {themes.map((theme) => (
        <div key={`${theme.label}-${theme.count}`} className="space-y-1.5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 text-[14px] font-medium leading-snug text-text-main">{theme.label}</div>
            <span className="shrink-0 font-mono text-[13px] text-text-dim">{theme.count}</span>
          </div>
          <div className="space-y-1.5">
            {theme.samples.slice(0, 2).map((sample) => (
              <div
                key={`${theme.label}-${sample.slice(0, 40)}`}
                className="rounded-md border border-outline/40 bg-surface/60 px-3 py-2 text-[14px] leading-relaxed text-text-variant"
              >
                {sample}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

const DEFAULT_LIKERT_LABELS_5: Record<string, string> = {
  "1": "Strongly disagree",
  "2": "Disagree",
  "3": "Neutral",
  "4": "Agree",
  "5": "Strongly agree",
}

function likertScaleBounds(
  context: AggregationContext,
  primary: AggregationField,
): { min: number; max: number } {
  const fromContextMin = Number(context.scaleMin)
  const fromContextMax = Number(context.scaleMax)
  if (Number.isFinite(fromContextMin) && Number.isFinite(fromContextMax) && fromContextMax > fromContextMin) {
    return { min: fromContextMin, max: fromContextMax }
  }
  const observedMin = primary.numerical?.min
  const observedMax = primary.numerical?.max
  // Unanimous high scores still need the questionnaire scale (typically 1–5).
  if (
    observedMin != null &&
    observedMax != null &&
    observedMin === observedMax &&
    observedMax >= 1 &&
    observedMax <= 5
  ) {
    return { min: 1, max: 5 }
  }
  if (observedMin != null && observedMax != null && observedMax > observedMin) {
    return { min: Math.min(1, observedMin), max: observedMax <= 5 ? 5 : observedMax <= 10 ? 10 : observedMax }
  }
  const inferred = inferRatingScale(primary)
  return { min: 1, max: inferred ?? 5 }
}

function likertPointLabel(
  value: number,
  context: AggregationContext,
  scale: { min: number; max: number },
): string | null {
  const key = String(Math.round(value))
  const custom = context.scaleLabels?.[key]?.trim()
  if (custom) return custom
  if (scale.min === 1 && scale.max === 5) return DEFAULT_LIKERT_LABELS_5[key] ?? null
  if (value === scale.min) return "Low"
  if (value === scale.max) return "High"
  return null
}

function likertScalePoints(
  context: AggregationContext,
  primary: AggregationField,
  scale: { min: number; max: number },
): Array<{ value: number; label: string; count: number }> {
  const counts = primary.numerical?.counts ?? []
  const byValue = new Map(counts.map((entry) => [String(entry.value), entry.count]))
  const points: Array<{ value: number; label: string; count: number }> = []
  for (let value = scale.min; value <= scale.max; value += 1) {
    const labelText = likertPointLabel(value, context, scale)
    points.push({
      value,
      label: labelText ? `${value} · ${labelText}` : String(value),
      count: byValue.get(String(value)) ?? 0,
    })
  }
  return points
}

function likertSegmentClass(index: number, total: number): string {
  if (total <= 1) return "bg-secondary/75"
  const t = index / Math.max(total - 1, 1)
  if (t <= 0.2) return "bg-danger/55"
  if (t <= 0.4) return "bg-warn/55"
  if (t <= 0.6) return "bg-outline/70"
  if (t <= 0.8) return "bg-secondary/55"
  return "bg-secondary/85"
}

function LikertSpectrumChart({
  points,
  total,
  avg,
  scale,
}: {
  points: Array<{ value: number; label: string; count: number }>
  total: number
  avg: number | null | undefined
  scale: { min: number; max: number }
}) {
  const safeTotal = Math.max(total, 1)
  const peak = Math.max(...points.map((point) => point.count), 1)
  const span = Math.max(scale.max - scale.min, 1)
  const avgPct =
    avg != null && Number.isFinite(avg) ? ((avg - scale.min) / span) * 100 : null

  return (
    <div className="space-y-3">
      <div className="relative rounded-lg border border-outline/40 bg-surface/40 px-3 pb-2 pt-4">
        {avgPct != null ? (
          <div
            className="pointer-events-none absolute bottom-8 top-3 z-10 w-px -translate-x-1/2 bg-text-main/70"
            style={{ left: `calc(12px + (100% - 24px) * ${Math.max(0, Math.min(100, avgPct)) / 100})` }}
          >
            <span className="absolute -top-1 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-text-main px-1.5 py-0.5 font-mono text-[12px] text-surface">
              avg {metricValue(avg)}
            </span>
          </div>
        ) : null}
        <div className="flex h-24 items-end gap-1.5">
          {points.map((point, index) => {
            const heightPct = point.count > 0 ? Math.max(10, Math.round((point.count / peak) * 100)) : 3
            return (
              <div key={point.value} className="flex min-w-0 flex-1 flex-col items-center gap-1">
                <div className="flex h-16 w-full items-end">
                  <div
                    className={`w-full rounded-t-md ${point.count > 0 ? likertSegmentClass(index, points.length) : "bg-outline/25"}`}
                    style={{ height: `${heightPct}%` }}
                    title={`${point.label}: ${point.count}`}
                  />
                </div>
                <div className="font-mono text-[12px] text-text-dim">{point.value}</div>
              </div>
            )
          })}
        </div>
      </div>
      <div className="grid gap-1.5">
        {points.map((point, index) => {
          const share = Math.round((point.count / safeTotal) * 100)
          return (
            <div key={point.value} className="flex items-center gap-2 text-[13px]">
              <span className={`h-2.5 w-2.5 shrink-0 rounded-sm ${likertSegmentClass(index, points.length)}`} />
              <span className={`min-w-0 flex-1 ${point.count > 0 ? "text-text-main" : "text-text-dim"}`}>
                {point.label}
              </span>
              <span className="shrink-0 font-mono text-text-dim">
                {point.count}
                {point.count > 0 ? ` · ${share}%` : ""}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function LikertQuestionBody({
  context,
  primary,
}: {
  context: AggregationContext
  primary: AggregationField
}) {
  const scale = likertScaleBounds(context, primary)
  const avg = primary.numerical?.avg
  const avgLabel = avg != null ? likertPointLabel(Math.round(avg), context, scale) : null
  const points = likertScalePoints(context, primary, scale)
  const total = Math.max(
    primary.presentCount ?? 0,
    points.reduce((sum, point) => sum + point.count, 0),
    1,
  )
  const lowLabel = likertPointLabel(scale.min, context, scale)
  const highLabel = likertPointLabel(scale.max, context, scale)
  const filled = points.filter((point) => point.count > 0).length
  const consensus =
    filled <= 1 && total > 0
      ? "Unanimous"
      : avg != null && avg >= scale.max - 0.35
        ? "Strongly favorable"
        : avg != null && avg <= scale.min + 0.35
          ? "Strongly unfavorable"
          : "Mixed"

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
        <div className="flex flex-wrap items-end gap-x-4 gap-y-1">
          <div>
            <div className="text-[12px] uppercase tracking-wide text-text-dim">Average</div>
            <div className="flex items-baseline gap-1.5">
              <span className="font-mono text-[22px] text-text-main">{metricValue(avg)}</span>
              <span className="font-mono text-[15px] text-text-dim">/{scale.max}</span>
            </div>
          </div>
          {avgLabel ? <div className="pb-1 text-[15px] text-text-main">{avgLabel}</div> : null}
        </div>
        <div className="rounded-md border border-outline/40 bg-surface/50 px-2 py-1 text-[13px] text-text-variant">
          {consensus}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-text-dim">
        <span>
          {scale.min}
          {lowLabel ? ` · ${lowLabel}` : ""}
        </span>
        <span aria-hidden="true">→</span>
        <span>
          {scale.max}
          {highLabel ? ` · ${highLabel}` : ""}
        </span>
      </div>
      <LikertSpectrumChart points={points} total={total} avg={avg} scale={scale} />
    </div>
  )
}

function SurveyQuestionCard({ context }: { context: AggregationContext }) {
  const [reasonsOpen, setReasonsOpen] = useState(false)
  const [quotesOpen, setQuotesOpen] = useState(false)
  const [scoresOpen, setScoresOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const reasonsPanelId = useId()
  const quotesPanelId = useId()
  const scoresPanelId = useId()
  const morePanelId = useId()
  const primaryFacet = primaryFacetForContext(context)
  const questionType = resolveSurveyQuestionType(context, primaryFacet)
  const isFreeText = questionType === "free_text"
  const isLikert = questionType === "likert" || primaryFacet?.kind === "numerical"
  const explanationFacet = surveyReasonFacetForContext(context)
  const scoreFacets = scoreFacetsForContext(context).filter(
    (facet) => facet.key !== primaryFacet?.key && facet.key !== explanationFacet?.key,
  )
  const claimedKeys = new Set(
    [primaryFacet?.key, explanationFacet?.key, ...scoreFacets.map((facet) => facet.key)].filter(Boolean),
  )
  const leftoverFacets = orderedFacets(context.facets).filter((facet) => !claimedKeys.has(facet.key))
  const answerItems = surveyAnswerItems(context, primaryFacet)
  const answerTotal = Math.max(
    primaryFacet?.presentCount ?? 0,
    answerItems.reduce((sum, item) => sum + item.count, 0),
    1,
  )
  const summaries = context.summaries ?? []
  const judges = context.judges ?? []
  const freeText = isFreeText ? freeTextCoverage(primaryFacet) : null
  const freeTextSignalThemes = isFreeText ? freeTextSignalTags(judges) : []
  const freeTextDisplayThemes =
    freeTextSignalThemes.length > 0 ? freeTextSignalThemes : (freeText?.themes ?? [])

  const reasonSamples = (explanationFacet?.textual?.samples ?? []).filter((sample) => sample.trim().length > 0)
  const reasonSummary =
    explanationFacet?.textual?.summary && !isHeuristicAggregationSummary(explanationFacet.textual.summary)
      ? explanationFacet.textual.summary
      : null
  const hasReasons = reasonSamples.length > 0 || Boolean(reasonSummary)
  const quoteCount = reasonSamples.length
  const crossFacetViews = crossFacetViewsForContext(context)
  const hasGroupedAnalysis = summaries.length > 0 || judges.length > 0 || crossFacetViews.length > 0
  const scoreNeedsDetail = scoreFacets.some(
    (facet) =>
      (facet.kind === "numerical" &&
        facet.numerical?.min != null &&
        facet.numerical?.max != null &&
        facet.numerical.min !== facet.numerical.max) ||
      (facet.kind === "categorical" && (facet.categorical?.counts?.length ?? 0) > 1) ||
      (facet.kind === "textual" && (facet.textual?.samples?.length ?? 0) > 0),
  )
  const typeChip =
    questionType === "likert"
      ? "Likert"
      : questionType === "single_choice"
        ? "Single choice"
        : questionType === "multi_choice"
          ? "Multi choice"
          : questionType === "free_text"
            ? "Free text"
            : null

  return (
    <section className="overflow-hidden rounded-xl border border-outline/50 bg-surface/35">
      <div className="px-4 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <FieldTitle field={context.label} />
            {typeChip ? <InlineBadge>{typeChip}</InlineBadge> : null}
            {primaryFacet?.presentCount != null ? (
              <span className="font-mono text-[13px] text-text-dim">
                {primaryFacet.presentCount} answered
                {primaryFacet.missingCount > 0 ? ` · ${primaryFacet.missingCount} missing` : ""}
              </span>
            ) : null}
          </div>
        </div>

        <div className="mt-3">
          {isFreeText && freeText ? (
            <div className="space-y-3">
              {(() => {
                const reportingSummary =
                  summaries.find((item) => item.overall?.summary)?.overall?.summary ??
                  judges.find((item) => item.overallAssessment)?.overallAssessment ??
                  null
                return (
                  <>
                    <p className="text-[15px] leading-relaxed text-text-main">
                      {reportingSummary || freeText.summary || "No written answers yet."}
                    </p>
                    <FreeTextThemeTags
                      themes={freeTextDisplayThemes}
                      label={freeTextSignalThemes.length > 0 ? "Signals" : "Themes"}
                    />
                  </>
                )
              })()}
            </div>
          ) : isLikert && primaryFacet?.kind === "numerical" ? (
            <LikertQuestionBody context={context} primary={primaryFacet} />
          ) : answerItems.length > 0 ? (
            <ChoiceCompositionChart
              items={answerItems}
              respondentCount={primaryFacet?.presentCount ?? answerTotal}
              multi={questionType === "multi_choice"}
            />
          ) : (
            <p className="text-[14px] text-text-variant">No response mix available.</p>
          )}
        </div>

        {scoreFacets.length > 0 && !scoreNeedsDetail ? (
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[14px] text-text-main">
            {scoreFacets.map((facet) => (
              <span key={facet.key} className="inline-flex items-baseline gap-1.5">
                <span className="text-text-dim">{facet.label}</span>
                <span className="font-mono">
                  {facet.kind === "numerical"
                    ? formatNumericalSummary(facet)
                    : facet.kind === "categorical"
                      ? formatCategoricalDistribution(facet)
                      : previewText(facet.textual?.summary ?? facet.textual?.samples?.[0] ?? "—", 48)}
                </span>
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {isFreeText && freeTextDisplayThemes.length > 0 ? (
        <div className="border-t border-outline/40">
          <button
            type="button"
            onClick={() => setQuotesOpen((value) => !value)}
            aria-expanded={quotesOpen}
            aria-controls={quotesPanelId}
            className={`flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-2.5 text-left transition-colors duration-200 hover:bg-surface/40 ${FOCUS_RING}`}
          >
            <div className="min-w-0">
              <div className="text-[14px] font-medium text-text-main">Examples by theme</div>
              <div className="mt-0.5 text-[13px] text-text-dim">
                {freeTextDisplayThemes.length} theme{freeTextDisplayThemes.length === 1 ? "" : "s"}
                {" · "}1–2 quotes each
              </div>
            </div>
            <Sym name={quotesOpen ? "expand_less" : "expand_more"} size={18} className="shrink-0 text-text-dim" />
          </button>
          {quotesOpen ? (
            <div id={quotesPanelId} className="border-t border-outline/35 bg-surface/20 px-4 py-3">
              <FreeTextThemeExamples themes={freeTextDisplayThemes} />
            </div>
          ) : null}
        </div>
      ) : null}

      {scoreFacets.length > 0 && scoreNeedsDetail ? (
        <div className="border-t border-outline/40">
          <button
            type="button"
            onClick={() => setScoresOpen((value) => !value)}
            aria-expanded={scoresOpen}
            aria-controls={scoresPanelId}
            className={`flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-2.5 text-left transition-colors duration-200 hover:bg-surface/40 ${FOCUS_RING}`}
          >
            <div className="min-w-0">
              <div className="text-[14px] font-medium text-text-main">
                {scoreFacets.length === 1 ? scoreFacets[0].label : "Scores"}
              </div>
              <div className="mt-0.5 text-[13px] text-text-dim">
                {scoreFacets
                  .map((facet) =>
                    facet.kind === "numerical"
                      ? `${facet.label} ${formatNumericalSummary(facet)}`
                      : facet.label,
                  )
                  .join(" · ")}
              </div>
            </div>
            <Sym name={scoresOpen ? "expand_less" : "expand_more"} size={18} className="shrink-0 text-text-dim" />
          </button>
          {scoresOpen ? (
            <div id={scoresPanelId} className="space-y-3 border-t border-outline/35 bg-surface/20 px-4 py-3">
              {scoreFacets.map((facet) => (
                <div key={facet.key} className="space-y-2">
                  {scoreFacets.length > 1 ? (
                    <div className="text-[14px] font-medium text-text-main">{facet.label}</div>
                  ) : null}
                  <FacetVisual field={facet} />
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {hasReasons ||
      (!isFreeText && hasGroupedAnalysis) ||
      (isFreeText && crossFacetViews.length > 0) ||
      leftoverFacets.length > 0 ? (
        <div className="border-t border-outline/40">
          {hasReasons ? (
            <>
              <button
                type="button"
                onClick={() => setReasonsOpen((value) => !value)}
                aria-expanded={reasonsOpen}
                aria-controls={reasonsPanelId}
                className={`flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-2.5 text-left transition-colors duration-200 hover:bg-surface/40 ${FOCUS_RING}`}
              >
                <div className="min-w-0">
                  <div className="text-[14px] font-medium text-text-main">Reasons</div>
                  <div className="mt-0.5 text-[13px] text-text-dim">
                    {quoteCount > 0
                      ? `${quoteCount} quote${quoteCount === 1 ? "" : "s"}`
                      : "Why personas answered this way"}
                  </div>
                </div>
                <Sym
                  name={reasonsOpen ? "expand_less" : "expand_more"}
                  size={18}
                  className="shrink-0 text-text-dim"
                />
              </button>
              {reasonsOpen ? (
                <div id={reasonsPanelId} className="space-y-3 border-t border-outline/35 bg-surface/20 px-4 py-3">
                  {reasonSummary ? (
                    <p className="text-[14px] leading-relaxed text-text-main">{reasonSummary}</p>
                  ) : null}
                  {reasonSamples.length > 0 ? <SampleList samples={reasonSamples} /> : null}
                </div>
              ) : null}
            </>
          ) : null}

          {hasGroupedAnalysis && !isFreeText ? (
            <div
              className={`space-y-2 px-4 py-3 ${
                hasReasons || (scoreFacets.length > 0 && scoreNeedsDetail)
                  ? "border-t border-outline/35"
                  : ""
              }`}
            >
              <div className="text-[13px] font-medium uppercase tracking-wide text-text-dim">
                Grouped analysis
              </div>
              {summaries.map((summary) => (
                <SummaryDisclosure key={summary.id} summary={summary} />
              ))}
              {judges.map((judge) => (
                <JudgeDisclosure key={judge.id} judge={judge} />
              ))}
              {crossFacetViews.map((crossFacetView, index) => (
                <CrossFacetViewDisclosure
                  key={`${context.key}-${crossFacetView.type}-${index}`}
                  crossFacetView={crossFacetView}
                />
              ))}
            </div>
          ) : null}
          {isFreeText && crossFacetViews.length > 0 ? (
            <div
              className={`space-y-2 px-4 py-3 ${
                hasReasons || (scoreFacets.length > 0 && scoreNeedsDetail) ? "border-t border-outline/35" : ""
              }`}
            >
              {crossFacetViews.map((crossFacetView, index) => (
                <CrossFacetViewDisclosure
                  key={`${context.key}-${crossFacetView.type}-${index}`}
                  crossFacetView={crossFacetView}
                />
              ))}
            </div>
          ) : null}

          {leftoverFacets.length > 0 ? (
            <div className={hasReasons || (!isFreeText && hasGroupedAnalysis) || (isFreeText && crossFacetViews.length > 0) ? "border-t border-outline/35" : ""}>
              <button
                type="button"
                onClick={() => setMoreOpen((value) => !value)}
                aria-expanded={moreOpen}
                aria-controls={morePanelId}
                className={`flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-2.5 text-left transition-colors duration-200 hover:bg-surface/40 ${FOCUS_RING}`}
              >
                <div className="min-w-0">
                  <div className="text-[14px] font-medium text-text-main">More signals</div>
                  <div className="mt-0.5 text-[13px] text-text-dim">
                    {leftoverFacets.length} additional field{leftoverFacets.length === 1 ? "" : "s"}
                  </div>
                </div>
                <Sym name={moreOpen ? "expand_less" : "expand_more"} size={18} className="shrink-0 text-text-dim" />
              </button>
              {moreOpen ? (
                <div id={morePanelId} className="space-y-3 border-t border-outline/35 bg-surface/20 px-4 py-3">
                  {leftoverFacets.map((facet) => (
                    <FacetCard key={facet.key} field={facet} />
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}


function feedbackFacetKey(field: AggregationField): string {
  return String(field.facetKey ?? field.key.split(".").pop() ?? field.key).trim().toLowerCase()
}

function defaultFeedbackCategories(field: AggregationField): string[] {
  const key = feedbackFacetKey(field)
  if (
    key.includes("need_constraint") ||
    key.includes("personal_preference") ||
    key.includes("clarity_of_next")
  ) {
    return ["yes", "partially", "no"]
  }
  const observed = (field.categorical?.counts ?? []).map((entry) => entry.value.toLowerCase())
  if (
    observed.every((value) => value === "true" || value === "false") ||
    key.includes("felt_understood") ||
    key.includes("clarification")
  ) {
    return ["true", "false"]
  }
  return field.categories?.map((item) => String(item)) ?? []
}

function feedbackChoiceItems(field: AggregationField): Array<CountBarItem & { id?: string }> {
  if (field.kind !== "categorical") return []
  const counts = field.categorical?.counts ?? []
  const byId = new Map(counts.map((entry) => [entry.value, entry.count]))
  const inventory = (field.categories?.length ? field.categories : defaultFeedbackCategories(field)).map(String)
  if (inventory.length === 0) {
    return counts.map((entry) => ({
      id: entry.value,
      label: formatBucketLabel(entry.value),
      count: entry.count,
    }))
  }
  const known = new Set(inventory)
  const rows = inventory.map((id) => ({
    id,
    label: formatBucketLabel(id),
    count: byId.get(id) ?? byId.get(id.toLowerCase()) ?? 0,
  }))
  for (const entry of counts) {
    if (!known.has(entry.value) && !known.has(entry.value.toLowerCase())) {
      rows.push({
        id: entry.value,
        label: formatBucketLabel(entry.value),
        count: entry.count,
      })
    }
  }
  return rows
}

function feedbackRatingContext(field: AggregationField): AggregationContext {
  const scaleMin =
    typeof field.scaleMin === "number"
      ? field.scaleMin
      : field.numerical?.min != null && field.numerical.min <= 1
        ? 1
        : 1
  const scaleMax =
    typeof field.scaleMax === "number"
      ? field.scaleMax
      : inferRatingScale(field) ?? (field.numerical?.max != null && field.numerical.max <= 10 ? 10 : 5)
  return {
    key: field.key,
    label: field.label,
    contextType: "user_feedback",
    scaleMin,
    scaleMax,
    facets: [field],
  }
}

function UserFeedbackBatchCard({ context }: { context: AggregationContext }) {
  const [moreOpen, setMoreOpen] = useState(false)
  const morePanelId = useId()
  const ratingFacets = context.facets.filter((facet) => facet.kind === "numerical")
  const choiceFacets = context.facets.filter((facet) => facet.kind === "categorical")
  const textFacets = context.facets.filter((facet) => facet.kind === "textual")
  const primaryRating =
    ratingFacets.find((facet) => facet.role === "primary") ??
    ratingFacets.find((facet) => feedbackFacetKey(facet).includes("overall_experience")) ??
    ratingFacets[0] ??
    null
  const otherRatings = ratingFacets.filter((facet) => facet.key !== primaryRating?.key)
  const summaries = context.summaries ?? []
  const judges = context.judges ?? []
  const crossFacetViews = crossFacetViewsForContext(context)
  const analysisCount = summaries.length + judges.length + crossFacetViews.length
  const explanation = explanationFacetForContext(context)
  const explanationLead =
    explanation?.textual?.summary && !isHeuristicAggregationSummary(explanation.textual.summary)
      ? previewText(explanation.textual.summary, 160)
      : explanation?.textual?.samples?.[0]
        ? previewText(explanation.textual.samples[0], 160)
        : null
  const ratingLead =
    primaryRating?.kind === "numerical"
      ? `${primaryRating.label}: avg ${formatNumericalSummary(primaryRating)}${
          typeof primaryRating.scaleMax === "number"
            ? `/${primaryRating.scaleMax}`
            : inferRatingScale(primaryRating)
              ? `/${inferRatingScale(primaryRating)}`
              : ""
        }`
      : null
  const leadText = explanationLead || ratingLead
  const typeDescription = contextTypeDescription(context)
  const respondentCount = Math.max(
    ...context.facets.map((facet) => facet.presentCount ?? 0),
    context.facets[0]?.presentCount ?? 0,
    1,
  )

  return (
    <section className="overflow-hidden rounded-xl border border-outline/50 bg-surface/35">
      <div className="space-y-4 px-4 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <FieldTitle field={context.label} />
            <InlineBadge>Persona self-report</InlineBadge>
            {analysisCount > 0 ? <InlineBadge>{analysisCount} analyses</InlineBadge> : null}
            <span className="font-mono text-[13px] text-text-dim">{respondentCount} personas</span>
          </div>
          {typeDescription ? (
            <p className="mt-1 text-[13px] leading-relaxed text-text-dim">{typeDescription}</p>
          ) : null}
          {leadText ? (
            <p className="mt-1.5 max-w-4xl text-[14px] leading-relaxed text-text-main">{leadText}</p>
          ) : null}
        </div>

        {primaryRating ? (
          <div className="rounded-xl border border-outline/40 bg-surface/55 p-3">
            <div className="mb-2 text-[13px] font-medium uppercase tracking-wide text-text-dim">
              {primaryRating.label}
            </div>
            <LikertQuestionBody context={feedbackRatingContext(primaryRating)} primary={primaryRating} />
          </div>
        ) : null}

        {choiceFacets.length > 0 ? (
          <div className="space-y-3">
            {choiceFacets.map((facet) => {
              const items = feedbackChoiceItems(facet)
              const total = Math.max(
                facet.presentCount,
                items.reduce((sum, item) => sum + item.count, 0),
                1,
              )
              return (
                <div key={facet.key} className="rounded-xl border border-outline/40 bg-surface/55 p-3">
                  <div className="mb-2 text-[13px] font-medium uppercase tracking-wide text-text-dim">
                    {facet.label}
                  </div>
                  <ChoiceCompositionChart items={items} respondentCount={total} />
                </div>
              )
            })}
          </div>
        ) : null}

        {otherRatings.length > 0 ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {otherRatings.map((facet) => (
              <div key={facet.key} className="rounded-xl border border-outline/40 bg-surface/55 p-3">
                <div className="mb-2 text-[13px] font-medium uppercase tracking-wide text-text-dim">
                  {facet.label}
                </div>
                <LikertQuestionBody context={feedbackRatingContext(facet)} primary={facet} />
              </div>
            ))}
          </div>
        ) : null}

        {textFacets.map((facet) => {
          const coverage = freeTextCoverage(facet)
          const signalThemes = freeTextSignalTags(
            judges.filter((judge) => judge.targetFacetKey === facet.facetKey || judge.targetFacetKey === facet.key),
          )
          const themes = signalThemes.length > 0 ? signalThemes : coverage.themes
          return (
            <div key={facet.key} className="space-y-2 rounded-xl border border-outline/40 bg-surface/55 p-3">
              <div className="text-[13px] font-medium uppercase tracking-wide text-text-dim">{facet.label}</div>
              {coverage.summary ? (
                <p className="text-[14px] leading-relaxed text-text-main">{coverage.summary}</p>
              ) : null}
              <FreeTextThemeTags themes={themes} label="Themes" />
              {(facet.textual?.samples?.length ?? 0) > 0 ? (
                <DisclosurePanel title={`Examples (${facet.textual?.samples?.length ?? 0})`}>
                  <SampleList samples={facet.textual?.samples ?? []} />
                </DisclosurePanel>
              ) : null}
            </div>
          )
        })}

        {analysisCount > 0 ? (
          <div>
            <button
              type="button"
              onClick={() => setMoreOpen((value) => !value)}
              aria-expanded={moreOpen}
              aria-controls={morePanelId}
              className={`inline-flex items-center gap-1 rounded-md border border-outline/50 bg-surface/60 px-2 py-1 text-[12px] uppercase tracking-wide text-text-dim hover:bg-surface/80 ${FOCUS_RING}`}
            >
              {moreOpen ? "Hide analyses" : "Show analyses"}
              <Sym name={moreOpen ? "expand_less" : "expand_more"} size={14} />
            </button>
            {moreOpen ? (
              <div id={morePanelId} className="mt-3 space-y-4 border-t border-outline/40 pt-3">
                {summaries.length > 0 ? (
                  <div className="space-y-3">
                    <SubsectionTitle title="Grouped summaries" />
                    {summaries.map((summary) => (
                      <SummaryDisclosure key={summary.id} summary={summary} />
                    ))}
                  </div>
                ) : null}
                {judges.length > 0 ? (
                  <div className="space-y-3">
                    <SubsectionTitle title="Judges" />
                    {judges.map((judge) => (
                      <JudgeDisclosure key={judge.id} judge={judge} />
                    ))}
                  </div>
                ) : null}
                {crossFacetViews.length > 0 ? (
                  <div className="space-y-3">
                    <SubsectionTitle title="Cross-facet views" />
                    {crossFacetViews.map((view, index) => (
                      <CrossFacetViewDisclosure
                        key={`${context.key}-${view.type}-${index}`}
                        crossFacetView={view}
                      />
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  )
}

function ContextCard({ context }: { context: AggregationContext }) {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const primaryFacet = primaryFacetForContext(context)
  const distributionItems = summaryBucketsForContext(context)
  const leadText = contextLeadText(context)
  const typeBadge = contextTypeBadgeLabel(context)
  const typeDescription = contextTypeDescription(context)
  const summaryCount = context.summaries?.length ?? 0
  const judgeCount = context.judges?.length ?? 0
  const crossFacetViewCount = crossFacetViewsForContext(context).length
  const unanimousPrimary =
    primaryFacet?.kind === "categorical" && primaryFacet != null && isUnanimousField(primaryFacet)
  const showDistribution =
    !unanimousPrimary && primaryFacet?.kind !== "categorical" && distributionItems.length > 0
  const analysisCount = summaryCount + judgeCount + crossFacetViewCount
  const showPrimaryPreview = primaryFacet?.kind === "numerical" || (!showDistribution && !unanimousPrimary)
  const primaryValue = primaryFacet?.categorical?.counts?.[0]?.value ?? null

  return (
    <section className="overflow-hidden rounded-xl border border-outline/50 bg-surface/35">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={panelId}
        className={`w-full px-4 py-3 text-left transition-colors hover:bg-surface/30 ${FOCUS_RING}`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <FieldTitle field={context.label} />
              {typeBadge ? <InlineBadge>{typeBadge}</InlineBadge> : null}
              {unanimousPrimary && primaryValue ? (
                <span className="inline-flex items-center gap-1 rounded-md border border-secondary/35 bg-secondary/10 px-2 py-0.5 text-[13px] font-medium text-secondary">
                  <Sym name="check_circle" size={12} fill={1} />
                  {primaryValue}
                </span>
              ) : null}
              {analysisCount > 0 ? <InlineBadge>{analysisCount} analyses</InlineBadge> : null}
            </div>
            {typeDescription ? (
              <p className="mt-1 text-[13px] leading-relaxed text-text-dim">{typeDescription}</p>
            ) : null}
            {leadText ? (
              <p className="mt-1.5 max-w-4xl text-[14px] leading-relaxed text-text-main">{leadText}</p>
            ) : null}
          </div>
          <span className="inline-flex items-center gap-1 rounded-md border border-outline/50 bg-surface/60 px-2 py-1 text-[12px] uppercase tracking-wide text-text-dim">
            {open ? "Collapse" : "Expand"}
            <Sym name={open ? "expand_less" : "expand_more"} size={14} />
          </span>
        </div>

        {!unanimousPrimary ? (
          <div className={`mt-3 grid gap-2 ${showPrimaryPreview && showDistribution ? "lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]" : ""}`}>
            {primaryFacet && showPrimaryPreview ? (
              <div className="rounded-xl border border-outline/40 bg-surface/55 p-2.5">
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <div className="text-[13px] font-medium uppercase tracking-wide text-text-dim">Primary signal</div>
                  {primaryFacet.role ? <InlineBadge>{primaryFacet.role}</InlineBadge> : null}
                </div>
                <FacetVisual field={primaryFacet} compact />
              </div>
            ) : null}

            {showDistribution ? (
              <div className="rounded-xl border border-outline/40 bg-surface/55 p-2.5">
                <div className="mb-1.5 text-[13px] font-medium uppercase tracking-wide text-text-dim">
                  Grouped responses
                </div>
                <CountBars
                  items={distributionItems.slice(0, 3)}
                  total={distributionItems.reduce((sum, item) => sum + item.count, 0)}
                  compact
                  showDetails={false}
                />
              </div>
            ) : null}

            {primaryFacet?.kind === "categorical" && !showPrimaryPreview && !showDistribution ? (
              <div className="rounded-xl border border-outline/40 bg-surface/55 p-2.5">
                <div className="mb-1.5 text-[13px] font-medium uppercase tracking-wide text-text-dim">
                  Distribution
                </div>
                <FacetVisual field={primaryFacet} compact />
              </div>
            ) : null}
          </div>
        ) : null}
      </button>

      {open ? (
        <div id={panelId} className="space-y-4 border-t border-outline/40 bg-surface/20 p-4">
          {context.facets.length > 0 ? (
            <div className="space-y-3">
              <SubsectionTitle
                title="Signals"
                subtitle="Quantitative summaries first; longer qualitative detail stays underneath."
              />
              <div className="grid gap-3 lg:grid-cols-2">
                {orderedFacets(context.facets).map((facet) => (
                  <FacetCard key={facet.key} field={facet} />
                ))}
              </div>
            </div>
          ) : null}

          {(context.summaries?.length ?? 0) > 0 ? (
            <div className="space-y-3">
              <SubsectionTitle
                title="Grouped summaries"
                subtitle="LLM-written rollups and bucketed evidence."
              />
              {context.summaries?.map((summary) => (
                <SummaryDisclosure key={summary.id} summary={summary} />
              ))}
            </div>
          ) : null}

          {(context.judges?.length ?? 0) > 0 ? (
            <div className="space-y-3">
              <SubsectionTitle
                title="Judges"
                subtitle="Scored checks and bucket-level assessments."
              />
              {context.judges?.map((judge) => (
                <JudgeDisclosure key={judge.id} judge={judge} />
              ))}
            </div>
          ) : null}

          {crossFacetViewsForContext(context).length > 0 ? (
            <div className="space-y-3">
              <SubsectionTitle
                title="Cross-facet views"
                subtitle="How one facet varies across another facet's groups."
              />
              {crossFacetViewsForContext(context).map((crossFacetView, index) => (
                <CrossFacetViewDisclosure
                  key={`${context.key}-${crossFacetView.type}-${index}`}
                  crossFacetView={crossFacetView}
                />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}

function FacetCard({ field }: { field: AggregationField }) {
  const textSummary = field.textual?.summary ?? null
  const textSamples = field.textual?.samples ?? []

  return (
    <div className="rounded-xl border border-outline/40 bg-surface/50 p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[15px] font-medium text-text-main">{field.label}</div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[12px] uppercase tracking-wide text-text-dim">
            <span>{field.kind}</span>
            {field.role ? <InlineBadge>{field.role}</InlineBadge> : null}
            <span>{field.presentCount} present</span>
            {field.missingCount > 0 ? <span>{field.missingCount} missing</span> : null}
          </div>
        </div>
      </div>

      <FacetVisual field={field} />

      {field.kind === "textual" && (textSummary || textSamples.length > 0) ? (
        <div className="mt-3 space-y-2">
          {textSummary ? (
            <p className="text-[14px] leading-relaxed text-text-main">{textSummary}</p>
          ) : null}
          {textSamples.length > 0 ? (
            <DisclosurePanel title="Evidence samples" subtitle={`${textSamples.length} captured`} badge="quotes">
              <SampleList samples={textSamples} />
            </DisclosurePanel>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

function SummaryDisclosure({ summary }: { summary: AggregationSummary }) {
  const total = summary.buckets.reduce((sum, bucket) => sum + bucket.count, 0)

  return (
    <DisclosurePanel
      title={summary.title}
      subtitle={summary.overall?.summary ? previewText(summary.overall.summary, 120) : undefined}
      badge={summary.status ? summary.status.replace(/_/g, " ") : undefined}
    >
      {summary.error ? <p className="text-[14px] leading-relaxed text-danger">{summary.error}</p> : null}
      {summary.overall?.summary ? (
        <p className="text-[14px] leading-relaxed text-text-main">{summary.overall.summary}</p>
      ) : null}
      {summary.buckets.length > 0 ? (
        <div className="mt-3 space-y-3">
          <CountBars
            items={summary.buckets.map((bucket) => ({
              label: bucket.bucket,
              count: bucket.count,
              detail: bucket.summary ?? null,
            }))}
            total={total}
          />
          <div className="space-y-2">
            {summary.buckets.map((bucket) => (
              <div key={`${summary.id}-${bucket.bucket}`} className="rounded-lg border border-outline/40 bg-surface/70 p-3">
                <div className="flex items-center justify-between gap-3 text-[14px]">
                  <span className="font-medium text-text-main">{bucket.bucket}</span>
                  <span className="font-mono text-text-variant">{bucket.count}</span>
                </div>
                {bucket.summary ? (
                  <p className="mt-2 text-[14px] leading-relaxed text-text-variant">{bucket.summary}</p>
                ) : null}
                {(bucket.samples?.length ?? 0) > 0 ? (
                  <div className="mt-2">
                    <SampleList samples={bucket.samples ?? []} />
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </DisclosurePanel>
  )
}

function JudgeDisclosure({ judge }: { judge: AggregationJudge }) {
  const total = judge.buckets.reduce((sum, bucket) => sum + bucket.count, 0)

  return (
    <DisclosurePanel
      title={judge.title}
      subtitle={judge.overallAssessment ? previewText(judge.overallAssessment, 120) : undefined}
      badge={judge.status ? judge.status.replace(/_/g, " ") : undefined}
    >
      {(judge.signals?.length ?? 0) > 0 ? (
        <div className="mb-3 flex flex-wrap gap-2">
          {judge.signals.map((signal) => (
            <span
              key={signal.key}
              className="rounded border border-outline/40 bg-surface/70 px-2 py-1 text-[13px] text-text-variant"
              title={signal.description ?? undefined}
            >
              {signal.label}
              {signal.valueType ? ` · ${signal.valueType}` : ""}
            </span>
          ))}
        </div>
      ) : null}
      {typeof judge.rubric === "string" && judge.rubric.trim() ? (
        <p className="mb-3 text-[14px] leading-relaxed text-text-variant">{judge.rubric}</p>
      ) : null}
      {judge.overallAssessment ? (
        <p className="mb-3 text-[14px] leading-relaxed text-text-main">{judge.overallAssessment}</p>
      ) : null}
      {judge.error ? <p className="mb-3 text-[14px] leading-relaxed text-danger">{judge.error}</p> : null}
      {judge.buckets.length > 0 ? (
        <div className="space-y-3">
          <CountBars
            items={judge.buckets.map((bucket) => ({
              label: bucket.bucket,
              count: bucket.count,
              detail: bucket.assessment ?? null,
            }))}
            total={total}
          />
          <div className="space-y-2">
            {judge.buckets.map((bucket) => (
              <div key={`${judge.id}-${bucket.bucket}`} className="rounded-lg border border-outline/40 bg-surface/70 p-3">
                <div className="flex items-center justify-between gap-3 text-[14px]">
                  <span className="font-medium text-text-main">{bucket.bucket}</span>
                  <span className="font-mono text-text-variant">{bucket.count}</span>
                </div>
                {bucket.assessment ? (
                  <p className="mt-2 text-[14px] leading-relaxed text-text-variant">{bucket.assessment}</p>
                ) : null}
                {(bucket.signals?.length ?? 0) > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {bucket.signals?.map((signal) => (
                      <span
                        key={`${judge.id}-${bucket.bucket}-${signal.key}`}
                        className={`rounded border px-2 py-1 text-[13px] ${
                          signal.present
                            ? "border-secondary/40 bg-secondary/10 text-secondary"
                            : "border-outline/40 bg-surface text-text-dim"
                        }`}
                        title={signal.evidence ?? undefined}
                      >
                        {signal.key}
                      </span>
                    ))}
                  </div>
                ) : null}
                {bucket.samples.length > 0 ? (
                  <div className="mt-2">
                    <SampleList samples={bucket.samples} />
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </DisclosurePanel>
  )
}

function CrossFacetViewDisclosure({
  crossFacetView,
}: {
  crossFacetView: AggregationCrossFacetView
}) {
  const buckets = crossFacetView.buckets ?? []
  const total = buckets.reduce((sum, bucket) => sum + bucket.count, 0)
  const title =
    crossFacetView.type === "text_by_primary_category"
      ? "Reasons by response group"
      : crossFacetView.type.replace(/_/g, " ")

  return (
    <DisclosurePanel
      title={title}
      subtitle={
        crossFacetView.primaryFacetKey && crossFacetView.textFacetKey
          ? `${crossFacetView.primaryFacetKey} × ${crossFacetView.textFacetKey}`
          : undefined
      }
      badge={`${buckets.length} buckets`}
    >
      <CountBars
        items={buckets.map((bucket) => ({
          label: bucket.category,
          count: bucket.count,
        }))}
        total={total}
      />
      <div className="mt-3 space-y-2">
        {buckets.map((bucket) => (
          <div key={`${crossFacetView.type}-${bucket.category}`} className="rounded-lg border border-outline/40 bg-surface/70 p-3">
            <div className="flex items-center justify-between gap-3 text-[14px]">
              <span className="font-medium text-text-main">{bucket.category}</span>
              <span className="font-mono text-text-variant">{bucket.count}</span>
            </div>
            {bucket.samples.length > 0 ? (
              <div className="mt-2">
                <SampleList samples={bucket.samples} />
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </DisclosurePanel>
  )
}

function FlatAggregationFallback({
  numerical,
  categorical,
  textual,
}: {
  numerical: AggregationField[]
  categorical: AggregationField[]
  textual: AggregationField[]
}) {
  return (
    <StudioGlassPanel className="overflow-hidden">
      <SectionHeader
        title="Field summaries"
        subtitle="This job has no structured contexts, so the report falls back to flat field aggregation."
      />
      <div className="space-y-5 p-4">
        {numerical.length > 0 ? (
          <div className="space-y-3">
            <SubsectionTitle title="Numerical" />
            <div className="grid gap-3 lg:grid-cols-2">
              {numerical.map((field) => (
                <FacetCard key={field.key} field={field} />
              ))}
            </div>
          </div>
        ) : null}
        {categorical.length > 0 ? (
          <div className="space-y-3">
            <SubsectionTitle title="Categorical" />
            <div className="grid gap-3 lg:grid-cols-2">
              {categorical.map((field) => (
                <FacetCard key={field.key} field={field} />
              ))}
            </div>
          </div>
        ) : null}
        {textual.length > 0 ? (
          <div className="space-y-3">
            <SubsectionTitle title="Textual" />
            <div className="grid gap-3 lg:grid-cols-2">
              {textual.map((field) => (
                <FacetCard key={field.key} field={field} />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </StudioGlassPanel>
  )
}

function FacetVisual({ field, compact = false }: { field: AggregationField; compact?: boolean }) {
  if (field.kind === "numerical") {
    const min = field.numerical?.min
    const max = field.numerical?.max
    const avg = field.numerical?.avg
    const hasRange = min != null && max != null && avg != null && max > min
    const avgPct =
      hasRange && min != null && max != null && avg != null
        ? Math.max(0, Math.min(100, ((avg - min) / (max - min)) * 100))
        : null

    return (
      <div className="space-y-3">
        <div className={`flex flex-wrap items-end justify-between gap-3 ${compact ? "sm:flex-nowrap" : ""}`}>
          <div>
            <div className="text-[12px] uppercase tracking-wide text-text-dim">Average</div>
            <div className={`${compact ? "text-[22px]" : "text-[30px]"} font-mono text-text-main`}>
              {metricValue(avg)}
            </div>
          </div>
          {compact ? (
            <div className="flex flex-wrap items-center gap-2 text-[13px] text-text-variant">
              <span>Std {metricValue(field.numerical?.std)}</span>
              <span>Present {field.presentCount}</span>
              {field.missingCount > 0 ? <span>Missing {field.missingCount}</span> : null}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 text-[14px] text-text-variant sm:min-w-[220px]">
              <MetricLine label="Std" value={metricValue(field.numerical?.std)} />
              <MetricLine label="Range" value={`${metricValue(min)} - ${metricValue(max)}`} />
              <MetricLine label="Present" value={String(field.presentCount)} />
              <MetricLine label="Missing" value={String(field.missingCount)} />
            </div>
          )}
        </div>
        {avgPct != null ? (
          <div className="space-y-1">
            <div className="relative h-2 rounded-full bg-surface-high">
              <div
                className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border border-primary/60 bg-primary shadow-sm"
                style={{ left: `${avgPct}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[13px] text-text-dim">
              <span>{metricValue(min)}</span>
              <span>{metricValue(max)}</span>
            </div>
          </div>
        ) : null}
      </div>
    )
  }

  if (field.kind === "categorical") {
    return (
      <CountBars
        items={(field.categorical?.counts ?? []).slice(0, compact ? 4 : 6).map((entry) => ({
          label: formatBucketLabel(entry.value),
          count: entry.count,
        }))}
        total={Math.max(field.presentCount, 1)}
        compact={compact}
        showDetails={!compact}
      />
    )
  }

  return (
    <div className="space-y-2">
      {field.textual?.summary ? (
        <p className="text-[14px] leading-relaxed text-text-main">
          {compact ? previewText(field.textual.summary, 90) : field.textual.summary}
        </p>
      ) : (
        <p className="text-[14px] text-text-variant">No text summary available.</p>
      )}
      {!compact && (field.textual?.samples?.length ?? 0) > 0 ? (
        <div className="text-[13px] text-text-dim">{field.textual?.samples.length} evidence samples available</div>
      ) : null}
    </div>
  )
}

function CountBars({
  items,
  total,
  compact = false,
  showDetails = true,
  showShare = false,
}: {
  items: CountBarItem[]
  total: number
  compact?: boolean
  showDetails?: boolean
  showShare?: boolean
}) {
  if (items.length === 0) {
    return <p className="text-[14px] text-text-variant">No distribution available.</p>
  }

  return (
    <div className={compact ? "space-y-1.5" : "space-y-2"}>
      {items.map((item) => {
        const share = Math.round((item.count / Math.max(total, 1)) * 100)
        return (
          <div key={`${item.label}-${item.count}`} className="space-y-1">
            <div className={`flex items-center justify-between gap-3 ${compact ? "text-[13px]" : "text-[14px]"}`}>
              <span className="truncate text-text-main">{item.label}</span>
              <span className="shrink-0 font-mono text-text-variant">
                {item.count}
                {showShare ? ` · ${share}%` : ""}
              </span>
            </div>
            <div className="h-2 rounded-full bg-surface-high">
              <div className="h-2 rounded-full bg-primary/75" style={{ width: ratioWidth(item.count, total) }} />
            </div>
            {showDetails && item.detail ? (
              <p className="text-[13px] leading-relaxed text-text-dim">{previewText(item.detail, compact ? 90 : 140)}</p>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}

function SampleList({ samples }: { samples: string[] }) {
  const [expanded, setExpanded] = useState(false)
  const shown = expanded ? samples : samples.slice(0, 2)

  return (
    <div className="space-y-2">
      {shown.map((sample, index) => (
        <div
          key={`${index}-${sample.slice(0, 24)}`}
          className="rounded-md border border-outline/40 bg-surface/60 px-3 py-2 text-[14px] leading-relaxed text-text-variant"
        >
          {sample}
        </div>
      ))}
      {samples.length > 2 ? (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className={`inline-flex items-center gap-1 rounded border border-outline/40 bg-surface/50 px-2 py-1 text-[13px] text-text-dim hover:bg-surface/70 ${FOCUS_RING}`}
        >
          <Sym name={expanded ? "expand_less" : "expand_more"} size={14} />
          {expanded ? "Show fewer quotes" : `Show ${samples.length - shown.length} more quotes`}
        </button>
      ) : null}
    </div>
  )
}

function DisclosurePanel({
  title,
  subtitle,
  badge,
  children,
  defaultOpen = false,
}: {
  title: string
  subtitle?: string | null
  badge?: string | null
  children: ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const panelId = useId()

  return (
    <div className="overflow-hidden rounded-xl border border-outline/40 bg-surface/45">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={panelId}
        className={`flex w-full items-center justify-between gap-3 px-3 py-3 text-left hover:bg-surface/40 ${FOCUS_RING}`}
      >
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-[14px] font-medium text-text-main">{title}</div>
            {badge ? <InlineBadge>{badge}</InlineBadge> : null}
          </div>
          {subtitle ? <p className="mt-1 text-[14px] leading-relaxed text-text-dim">{subtitle}</p> : null}
        </div>
        <span className="inline-flex items-center gap-1 text-[12px] uppercase tracking-wide text-text-dim">
          {open ? "Hide" : "View"}
          <Sym name={open ? "expand_less" : "expand_more"} size={14} />
        </span>
      </button>
      {open ? (
        <div id={panelId} className="space-y-3 border-t border-outline/40 bg-surface/20 p-3">
          {children}
        </div>
      ) : null}
    </div>
  )
}

function SectionHeader({
  title,
  subtitle,
}: {
  title: string
  subtitle?: string | null
}) {
  return (
    <div className="border-b border-outline/40 px-4 py-3">
      <div className="text-[12px] font-medium uppercase tracking-wide text-text-dim">{title}</div>
      {subtitle ? <p className="mt-1 text-[14px] leading-relaxed text-text-variant">{subtitle}</p> : null}
    </div>
  )
}

function SubsectionTitle({ title, subtitle }: { title: string; subtitle?: string | null }) {
  return (
    <div>
      <div className="text-[13px] font-medium uppercase tracking-wide text-text-dim">{title}</div>
      {subtitle ? <p className="mt-1 text-[14px] leading-relaxed text-text-variant">{subtitle}</p> : null}
    </div>
  )
}

function InlineBadge({ children }: { children: ReactNode }) {
  return (
    <span className="rounded border border-outline/50 bg-surface/60 px-1.5 py-0.5 text-[12px] uppercase tracking-wide text-text-dim">
      {children}
    </span>
  )
}

function CoverageTile({
  label,
  value,
  hint,
}: {
  label: string
  value: string | number
  hint?: string | null
}) {
  return (
    <div className="min-w-[108px] rounded-lg border border-outline/40 bg-surface/35 px-2.5 py-2">
      <div className="text-[11px] uppercase tracking-wide text-text-dim">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="font-mono text-[18px] text-text-main">{value}</span>
        {hint ? <span className="truncate text-[12px] text-text-variant">{hint}</span> : null}
      </div>
    </div>
  )
}

/** Same question-type chip language as single-trial survey debrief / scorecard. */
function SurveyQuestionTypesTile({ counts }: { counts: SurveyQuestionTypeCount[] }) {
  return (
    <div className="min-w-[140px] rounded-lg border border-outline/40 bg-surface/35 px-2.5 py-2">
      <div className="text-[11px] uppercase tracking-wide text-text-dim">Question types</div>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {counts.map((entry) => (
          <span
            key={entry.type}
            className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-[12px] ${surveyQuestionTypeChipClass(entry.type)}`}
          >
            <span className="font-mono font-semibold tabular-nums">{entry.count}</span>
            {entry.label}
          </span>
        ))}
      </div>
    </div>
  )
}

function FieldTitle({ field }: { field: string }) {
  return <div className="text-[14px] font-medium text-text-main">{field}</div>
}

function MetricLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-md bg-surface/50 px-2 py-1.5">
      <span>{label}</span>
      <span className="font-mono text-text-main">{value}</span>
    </div>
  )
}

export function HarborJobDetail({ jobName, onBack, onOpenTrial }: HarborJobDetailProps) {
  const query = useQuery<HarborJobDetail>({
    queryKey: ["harbor-job", jobName],
    queryFn: () => api.getHarborJob(jobName),
    refetchInterval: (ctx) => {
      const launch = ctx.state.data?.launch;
      const trials = ctx.state.data?.trials ?? [];
      const reporting = ctx.state.data?.aggregation?.reporting;
      const pending = trials.some((trial) => !trial.completed);
      if (
        launch?.status === "running" ||
        launch?.status === "queued" ||
        pending ||
        reporting?.status === "queued" ||
        reporting?.status === "running"
      ) {
        return 3000;
      }
      return false;
    },
  });

  const job = query.data;
  const launch = job?.launch;
  const trials = job?.trials ?? [];
  const aggregation = job?.aggregation ?? null;
  const pdfMeta = useMemo(() => buildBatchReportPdfMeta(jobName, job), [jobName, job]);

  const progress = useMemo(() => {
    const done = trials.filter((trial) => trial.completed && trial.succeeded !== false && !trial.error).length;
    const failed = trials.filter((trial) => trial.error || trial.succeeded === false).length;
    const running = trials.filter((trial) => !trial.completed).length;
    return { done, failed, running, total: trials.length };
  }, [trials]);

  return (
    <StudioPageFrame>
      <StudioPageHeader
        eyebrow="MatrAIx · Runs"
        title={jobName}
        subtitle={
          launch?.configPath
            ? undefined
            : "Open a trial for evaluation and the run transcript."
        }
        meta={
          launch?.status ? (
            <span className="rounded-lg border border-outline/50 bg-surface/60 px-2.5 py-1 font-mono text-[13px] text-text-variant backdrop-blur">
              {launch.status}
              {launch.exitCode != null ? ` · exit ${launch.exitCode}` : ""}
            </span>
          ) : null
        }
        actions={
          <>
            <StudioToolbarButton icon="arrow_back" onClick={onBack}>
              All jobs
            </StudioToolbarButton>
            <StudioToolbarButton
              icon="refresh"
              onClick={() => query.refetch()}
              disabled={query.isFetching}
            >
              Refresh
            </StudioToolbarButton>
          </>
        }
      />
      {launch?.configPath ? (
        <p className="-mt-3 mb-5 break-all font-mono text-[13px] leading-snug text-text-variant">
          Config: {launch.configPath}
        </p>
      ) : null}

      {query.isLoading ? (
        <p className="text-[15px] text-text-variant">Loading job…</p>
      ) : query.isError ? (
        <p className="text-[15px] text-danger">
          {query.error instanceof ApiError ? query.error.message : "Failed to load job."}
        </p>
      ) : (
        <>
          {launch?.error && (
            <div className="mb-4 rounded-lg border border-danger/40 bg-danger/10 px-4 py-3 text-[15px] text-danger">
              {launch.error}
            </div>
          )}

          {progress.total > 0 && !aggregation && (
            <StudioGlassPanel className="mb-5 flex flex-wrap items-center gap-3 px-4 py-3 text-[14px] text-text-variant">
              <span className="font-mono text-text-main">
                {progress.done}/{progress.total} trials finished
              </span>
              {progress.running > 0 && (
                <span className="inline-flex items-center gap-1 text-warn">
                  <span className="h-1.5 w-1.5 rounded-full bg-warn animate-pulse" />
                  {progress.running} running
                </span>
              )}
              {progress.failed > 0 && (
                <span className="inline-flex items-center gap-1 text-danger">
                  <span className="h-1.5 w-1.5 rounded-full bg-danger" />
                  {progress.failed} failed
                </span>
              )}
            </StudioGlassPanel>
          )}

          {aggregation && (
            <AggregationDashboard
              aggregation={aggregation}
              applicationType={job?.applicationType}
              pdfMeta={pdfMeta}
            />
          )}

          <StudioGlassPanel className="overflow-hidden rounded-xl">
            <div className="grid grid-cols-[minmax(0,1.4fr)_minmax(0,1.2fr)_5.5rem_2rem] gap-3 border-b border-outline/40 px-4 py-2.5 text-[12px] uppercase tracking-wide text-text-dim">
              <span>Persona</span>
              <span>Trial</span>
              <span>Status</span>
              <span className="sr-only">Open</span>
            </div>
            <ul className="divide-y divide-outline-dim">
              {trials.length === 0 ? (
                <li className="px-4 py-8 text-center text-[15px] text-text-variant">
                  {launch?.status === "running" || launch?.status === "queued"
                    ? "Trials are starting — they will appear here as they launch."
                    : "No trials yet."}
                </li>
              ) : (
                trials.map((trial) => {
                  const clickable = Boolean(onOpenTrial);
                  return (
                    <li key={trial.trialName}>
                      <button
                        type="button"
                        disabled={!clickable}
                        onClick={() => onOpenTrial?.(trial.trialName)}
                        className={`grid w-full grid-cols-[minmax(0,1.4fr)_minmax(0,1.2fr)_5.5rem_2rem] items-center gap-3 px-4 py-3 text-left text-[15px] ${
                          clickable ? "hover:bg-surface/40" : ""
                        } ${FOCUS_RING}`}
                      >
                        <TrialPersonaIdentity trial={trial} />
                        <span className="truncate font-mono text-[13px] text-text-variant">
                          {trial.trialName}
                        </span>
                        <TrialStatusBadge trial={trial} />
                        <Sym
                          name="chevron_right"
                          size={18}
                          className={clickable ? "text-text-dim" : "text-text-dim/40"}
                        />
                      </button>
                    </li>
                  );
                })
              )}
            </ul>
          </StudioGlassPanel>
        </>
      )}
    </StudioPageFrame>
  );
}

export default HarborJobDetail;
