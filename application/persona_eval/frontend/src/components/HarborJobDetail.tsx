/**
 * Harbor batch job detail — trial index only; open a trial for evaluation + run content.
 */
import { type ReactNode, useId, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { HarborJobAggregation, HarborJobDetail } from "@/lib/types";
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
type AggregationRelationship = NonNullable<AggregationContext["relationships"]>[number];
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
    badge: "Question response",
    description: "Persona answers and their supporting rationale.",
    order: 0,
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
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide ${style.className}`}
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

function trialPersonaLabel(trial: HarborTrialRow): string {
  if (trial.personaName) return trial.personaName;
  if (trial.personaId) return `persona-${trial.personaId}`;
  return trial.trialName;
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
    /^Collected \d+ text responses across \d+ unique values/i.test(normalized)
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

function formatCategoricalDistribution(field: AggregationField | null): string {
  const counts = field?.categorical?.counts ?? []
  if (counts.length === 0) return "—"
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

function formatBucketLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
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

function looksLikeRatingFacet(field: AggregationField): boolean {
  const scale = inferRatingScale(field)
  if (scale == null) return false
  const haystack = `${field.facetKey} ${field.label}`.toLowerCase()
  return haystack.includes("rating") || haystack.includes("score") || scale === 10
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
    const suffix = scale === 10 ? "/10" : scale === 5 ? "/5" : ""
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
  dimensionLabel: string
  rows: Array<{ label: string; count: number }>
  annotationField: AggregationField | null
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

function findBreakdownAnnotationField(
  context: AggregationContext,
  dimensionKey: string,
): AggregationField | null {
  const candidates = context.facets.filter(
    (facet) =>
      facet.key !== dimensionKey &&
      facet.kind === "categorical" &&
      (facet.role === "primary" || facet.role === "evidence"),
  )
  return (
    candidates.sort(
      (a, b) => (a.categorical?.distinctCount ?? 99) - (b.categorical?.distinctCount ?? 99),
    )[0] ?? null
  )
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
    dimensionLabel: dimension.label,
    rows,
    annotationField: findBreakdownAnnotationField(context, dimension.key),
    detailField: findBreakdownDetailField(context, dimension.key),
  }
}

function buildDistributionBreakdowns(
  contexts: AggregationContext[],
  trialCount: number,
  category: ReportingCategory,
): DistributionBreakdown[] {
  const breakdowns: DistributionBreakdown[] = []
  for (const context of orderedContextsForBreakdown(contexts, category)) {
    if (shouldCompactContext(context, category)) continue
    const breakdown = buildContextDistributionBreakdown(context, trialCount)
    if (!breakdown) continue
    if (breakdown.rows.length === 1 && trialCount <= 1) continue
    breakdowns.push(breakdown)
    if (breakdowns.length >= 2) break
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
): InsightChipProps[] {
  const chips: InsightChipProps[] = [
    {
      label: "Completed",
      value: `${coverage.completedTrials}/${coverage.trialCount}`,
      variant: "semantic",
      tone: coverage.completedTrials === coverage.trialCount ? "success" : "warn",
    },
  ]
  const seen = new Set<string>()
  for (const context of orderedContexts(contexts, category)) {
    if (shouldCompactContext(context, category)) continue
    for (const facet of insightFacetsForContext(context)) {
      if (seen.has(facet.key)) continue
      seen.add(facet.key)
      const chip = facetToInsightChip(facet)
      if (chip) chips.push(chip)
      if (chips.length >= 8) return chips
    }
  }
  return chips
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
      label: entry.value,
      count: entry.count,
    }))
  }
  const relationship = context.relationships?.find((item) => (item.buckets?.length ?? 0) > 0)
  return (relationship?.buckets ?? []).map((bucket) => ({
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
      <div className="text-[9px] uppercase tracking-wide text-text-dim">{label}</div>
      <div className={`mt-0.5 text-[12px] font-medium ${colored ? toneTextClass[tone] : "text-text-main"}`}>
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

  return (
    <div className="mt-3 space-y-3 rounded-xl border border-primary/30 bg-primary/10 p-3">
      <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wide text-primary">
        <Sym name="insights" size={14} />
        Batch insights
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
  const chips = buildHeadlineInsightChips(contexts, aggregation.coverage, category)
  const distributionBreakdowns = buildDistributionBreakdowns(contexts, trialCount, category)
  const scoreStats = buildScoreMetricStrip(contexts)
  const snapshotFields = buildPersonaSnapshotFields(contexts)
  const showSnapshots = trialCount <= 8 && snapshotFields.length > 0

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {chips.map((chip) => (
          <InsightChip key={`${chip.label}-${chip.value}`} {...chip} />
        ))}
      </div>

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
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-text-main">
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
        <div className="text-[10px] font-medium uppercase tracking-wide text-text-dim">{breakdown.contextLabel}</div>
      </div>
      <div className="grid gap-2 border-b border-outline/35 bg-surface/30 px-3 py-1.5 text-[9px] uppercase tracking-wide text-text-dim sm:grid-cols-[minmax(0,1.4fr)_auto_auto_auto]">
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
              <div className="truncate text-[13px] font-medium text-text-main">{row.label}</div>
              {breakdown.annotationField ? (
                <div className="mt-0.5 text-[11px] text-text-dim">
                  {breakdown.annotationField.label}:{" "}
                  {formatCategoricalDistribution(breakdown.annotationField)}
                </div>
              ) : null}
            </div>
            <div className="text-[12px] font-mono text-text-main sm:text-right">{row.count}</div>
            <div className="text-[11px] text-text-dim sm:text-right">
              {Math.round((row.count / Math.max(trialCount, 1)) * 100)}%
            </div>
            <div className="truncate text-[11px] text-text-variant sm:text-right">
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
      <div className="border-b border-outline/35 px-3 py-2 text-[10px] font-medium uppercase tracking-wide text-text-dim">
        Persona voice
      </div>
      <div className="divide-y divide-outline/30">
        {Array.from({ length: visibleRows }, (_, index) => (
          <div key={`snapshot-${index}`} className="space-y-2 px-3 py-2.5">
            <div className="font-mono text-[10px] uppercase tracking-wide text-text-dim">
              Persona {index + 1}
            </div>
            {fields.map((field) => {
              const sample = field.textual?.samples?.[index]
              if (!sample) return null
              return (
                <div key={`${field.key}-${index}`}>
                  <div className="text-[10px] uppercase tracking-wide text-text-dim">{field.label}</div>
                  <p className="mt-0.5 text-[12px] leading-relaxed text-text-main">
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
          <div className="text-[13px] font-medium text-text-main">Execution checks</div>
          <p className="mt-1 text-[11px] text-text-dim">
            {contexts.length} contexts · all personas agreed
          </p>
        </div>
        <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wide text-text-dim">
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
                <div className="text-[12px] font-medium text-text-main">{context.label}</div>
                {contextTypeDescription(context) ? (
                  <div className="truncate text-[10px] text-text-dim">{contextTypeDescription(context)}</div>
                ) : null}
              </div>
              <div className="shrink-0 text-right">
                <div className="text-[12px] font-medium text-text-main">{value}</div>
                <div className="font-mono text-[10px] text-text-dim">{primary?.presentCount ?? 0}/{primary?.presentCount ?? 0}</div>
              </div>
            </div>
          )
        })}
      </div>
      {!open && contexts.length > 4 ? (
        <div className="border-t border-outline/35 px-4 py-2 text-[11px] text-text-dim">
          +{contexts.length - 4} more unanimous checks
        </div>
      ) : null}
    </section>
  )
}

function AggregationDashboard({
  aggregation,
  applicationType,
}: {
  aggregation: HarborJobAggregation
  applicationType?: string | null
}) {
  const [open, setOpen] = useState(false)
  const allContexts = useMemo(() => aggregation.contexts ?? [], [aggregation.contexts])
  const category = useMemo(
    () => inferReportingCategory(allContexts, applicationType),
    [allContexts, applicationType],
  )
  const { headline: headlineContexts, compact: compactContexts } = useMemo(
    () => splitContexts(allContexts, category),
    [allContexts, category],
  )
  const contexts = allContexts
  const numerical = aggregation.fields.filter((field) => field.kind === "numerical")
  const categorical = aggregation.fields.filter((field) => field.kind === "categorical")
  const textual = aggregation.fields.filter((field) => field.kind === "textual")
  const coverage = aggregation.coverage
  const reporting = aggregation.reporting ?? null
  const reportingChip = reportingSummary(reporting)
  const hasDetails = contexts.length > 0 || numerical.length > 0 || categorical.length > 0 || textual.length > 0
  const detailCount = contexts.length > 0 ? contexts.length : numerical.length + categorical.length + textual.length
  const detailLabel = contexts.length > 0 ? "contexts" : "fields"
  const trialHint =
    coverage.pendingTrials > 0
      ? `${coverage.completedTrials}/${coverage.trialCount} complete`
      : `${coverage.completedTrials} completed`
  const showArtifactsChip =
    coverage.completedWithoutArtifactTrials > 0 || coverage.artifactReadyTrials !== coverage.trialCount
  const showPendingChip = coverage.pendingTrials > 0

  return (
    <div className="mb-5 space-y-5">
      <StudioGlassPanel className="px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-[12px] font-medium text-text-main">
            <Sym name="analytics" size={16} className="text-primary" />
            Batch report
          </div>
          {reporting ? (
            <span
              className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide ${reportingStatusClassName(
                reporting.status,
              )}`}
            >
              <Sym
                name={reporting.status === "queued" || reporting.status === "running" ? "autorenew" : "analytics"}
                size={12}
                className={reporting.status === "queued" || reporting.status === "running" ? "animate-rb-spin" : ""}
              />
              Reporting {reportingStatusLabel(reporting.status)}
            </span>
          ) : null}
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <CoverageTile label="Trials" value={coverage.trialCount} hint={trialHint} />
          <CoverageTile
            label="Contexts"
            value={contexts.length}
            hint={contexts.length > 0 ? "Structured context view" : "Fallback field view"}
          />
          {showArtifactsChip ? (
            <CoverageTile
              label="Artifacts"
              value={coverage.artifactReadyTrials}
              hint={coverage.completedWithoutArtifactTrials > 0 ? `${coverage.completedWithoutArtifactTrials} missing` : "Ready"}
            />
          ) : null}
          {showPendingChip ? <CoverageTile label="Pending" value={coverage.pendingTrials} hint="Still running" /> : null}
          {reportingChip ? (
            <CoverageTile label="Reporting" value={reportingChip.value} hint={reportingChip.hint} />
          ) : null}
        </div>
        {reporting?.error ? (
          <p className="mt-3 text-[12px] leading-relaxed text-danger">{reporting.error}</p>
        ) : null}
        {contexts.length > 0 ? <BatchInsightsPanel aggregation={aggregation} category={category} /> : null}
        {hasDetails ? (
          <div className={`space-y-2 ${contexts.length > 0 ? "mt-3 border-t border-outline/35 pt-3" : "mt-3"}`}>
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
                <div className="text-[12px] font-medium text-on-primary">
                  {open ? "Hide detailed report" : "Show detailed report"}
                </div>
                <div className="mt-0.5 text-[11px] leading-relaxed text-on-primary/80">
                  {detailCount} {detailLabel} · signals, grouped summaries, and evidence
                </div>
              </div>
              <div className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-white/15 bg-white/10 px-2.5 py-1.5 text-[11px] text-on-primary">
                <span>{open ? "Collapse" : "Expand"}</span>
                <Sym name={open ? "expand_less" : "expand_more"} size={16} />
              </div>
            </button>
          </div>
        ) : null}
      </StudioGlassPanel>

      {open ? (
        contexts.length > 0 ? (
          <StudioGlassPanel className="overflow-hidden">
            <SectionHeader
              title="Detailed contexts"
              subtitle="Decision and feedback first. Expand any card for signals, grouped summaries, and evidence."
            />
            <div className="space-y-3 p-4">
              {compactContexts.length > 0 ? <CompactContextGroup contexts={compactContexts} /> : null}
              {headlineContexts.map((context) => (
                <ContextCard key={context.key} context={context} />
              ))}
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
  const relationshipCount = context.relationships?.length ?? 0
  const unanimousPrimary =
    primaryFacet?.kind === "categorical" && primaryFacet != null && isUnanimousField(primaryFacet)
  const showDistribution =
    !unanimousPrimary && primaryFacet?.kind !== "categorical" && distributionItems.length > 0
  const analysisCount = summaryCount + judgeCount + relationshipCount
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
                <span className="inline-flex items-center gap-1 rounded-md border border-secondary/35 bg-secondary/10 px-2 py-0.5 text-[11px] font-medium text-secondary">
                  <Sym name="check_circle" size={12} fill={1} />
                  {primaryValue}
                </span>
              ) : null}
              {analysisCount > 0 ? <InlineBadge>{analysisCount} analyses</InlineBadge> : null}
            </div>
            {typeDescription ? (
              <p className="mt-1 text-[11px] leading-relaxed text-text-dim">{typeDescription}</p>
            ) : null}
            {leadText ? (
              <p className="mt-1.5 max-w-4xl text-[12px] leading-relaxed text-text-main">{leadText}</p>
            ) : null}
          </div>
          <span className="inline-flex items-center gap-1 rounded-md border border-outline/50 bg-surface/60 px-2 py-1 text-[10px] uppercase tracking-wide text-text-dim">
            {open ? "Collapse" : "Expand"}
            <Sym name={open ? "expand_less" : "expand_more"} size={14} />
          </span>
        </div>

        {!unanimousPrimary ? (
          <div className={`mt-3 grid gap-2 ${showPrimaryPreview && showDistribution ? "lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]" : ""}`}>
            {primaryFacet && showPrimaryPreview ? (
              <div className="rounded-xl border border-outline/40 bg-surface/55 p-2.5">
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <div className="text-[11px] font-medium uppercase tracking-wide text-text-dim">Primary signal</div>
                  {primaryFacet.role ? <InlineBadge>{primaryFacet.role}</InlineBadge> : null}
                </div>
                <FacetVisual field={primaryFacet} compact />
              </div>
            ) : null}

            {showDistribution ? (
              <div className="rounded-xl border border-outline/40 bg-surface/55 p-2.5">
                <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-text-dim">
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
                <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-text-dim">
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

          {(context.relationships?.length ?? 0) > 0 ? (
            <div className="space-y-3">
              <SubsectionTitle
                title="Relationships"
                subtitle="How explanations vary across response groups."
              />
              {context.relationships?.map((relationship, index) => (
                <RelationshipDisclosure
                  key={`${context.key}-${relationship.type}-${index}`}
                  relationship={relationship}
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
          <div className="text-[13px] font-medium text-text-main">{field.label}</div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-wide text-text-dim">
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
            <p className="text-[12px] leading-relaxed text-text-main">{textSummary}</p>
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
      {summary.error ? <p className="text-[12px] leading-relaxed text-danger">{summary.error}</p> : null}
      {summary.overall?.summary ? (
        <p className="text-[12px] leading-relaxed text-text-main">{summary.overall.summary}</p>
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
                <div className="flex items-center justify-between gap-3 text-[12px]">
                  <span className="font-medium text-text-main">{bucket.bucket}</span>
                  <span className="font-mono text-text-variant">{bucket.count}</span>
                </div>
                {bucket.summary ? (
                  <p className="mt-2 text-[12px] leading-relaxed text-text-variant">{bucket.summary}</p>
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
              className="rounded border border-outline/40 bg-surface/70 px-2 py-1 text-[11px] text-text-variant"
              title={signal.description ?? undefined}
            >
              {signal.label}
              {signal.valueType ? ` · ${signal.valueType}` : ""}
            </span>
          ))}
        </div>
      ) : null}
      {typeof judge.rubric === "string" && judge.rubric.trim() ? (
        <p className="mb-3 text-[12px] leading-relaxed text-text-variant">{judge.rubric}</p>
      ) : null}
      {judge.overallAssessment ? (
        <p className="mb-3 text-[12px] leading-relaxed text-text-main">{judge.overallAssessment}</p>
      ) : null}
      {judge.error ? <p className="mb-3 text-[12px] leading-relaxed text-danger">{judge.error}</p> : null}
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
                <div className="flex items-center justify-between gap-3 text-[12px]">
                  <span className="font-medium text-text-main">{bucket.bucket}</span>
                  <span className="font-mono text-text-variant">{bucket.count}</span>
                </div>
                {bucket.assessment ? (
                  <p className="mt-2 text-[12px] leading-relaxed text-text-variant">{bucket.assessment}</p>
                ) : null}
                {(bucket.signals?.length ?? 0) > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {bucket.signals?.map((signal) => (
                      <span
                        key={`${judge.id}-${bucket.bucket}-${signal.key}`}
                        className={`rounded border px-2 py-1 text-[11px] ${
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

function RelationshipDisclosure({ relationship }: { relationship: AggregationRelationship }) {
  const buckets = relationship.buckets ?? []
  const total = buckets.reduce((sum, bucket) => sum + bucket.count, 0)
  const title =
    relationship.type === "text_by_primary_category"
      ? "Reasons by response group"
      : relationship.type.replace(/_/g, " ")

  return (
    <DisclosurePanel
      title={title}
      subtitle={
        relationship.primaryFacetKey && relationship.textFacetKey
          ? `${relationship.primaryFacetKey} × ${relationship.textFacetKey}`
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
          <div key={`${relationship.type}-${bucket.category}`} className="rounded-lg border border-outline/40 bg-surface/70 p-3">
            <div className="flex items-center justify-between gap-3 text-[12px]">
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
            <div className="text-[10px] uppercase tracking-wide text-text-dim">Average</div>
            <div className={`${compact ? "text-[22px]" : "text-[30px]"} font-mono text-text-main`}>
              {metricValue(avg)}
            </div>
          </div>
          {compact ? (
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-text-variant">
              <span>Std {metricValue(field.numerical?.std)}</span>
              <span>Present {field.presentCount}</span>
              {field.missingCount > 0 ? <span>Missing {field.missingCount}</span> : null}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 text-[12px] text-text-variant sm:min-w-[220px]">
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
            <div className="flex items-center justify-between text-[11px] text-text-dim">
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
          label: entry.value,
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
        <p className="text-[12px] leading-relaxed text-text-main">
          {compact ? previewText(field.textual.summary, 90) : field.textual.summary}
        </p>
      ) : (
        <p className="text-[12px] text-text-variant">No text summary available.</p>
      )}
      {!compact && (field.textual?.samples?.length ?? 0) > 0 ? (
        <div className="text-[11px] text-text-dim">{field.textual?.samples.length} evidence samples available</div>
      ) : null}
    </div>
  )
}

function CountBars({
  items,
  total,
  compact = false,
  showDetails = true,
}: {
  items: CountBarItem[]
  total: number
  compact?: boolean
  showDetails?: boolean
}) {
  if (items.length === 0) {
    return <p className="text-[12px] text-text-variant">No distribution available.</p>
  }

  return (
    <div className={compact ? "space-y-1.5" : "space-y-2"}>
      {items.map((item) => (
        <div key={`${item.label}-${item.count}`} className="space-y-1">
          <div className={`flex items-center justify-between gap-3 ${compact ? "text-[11px]" : "text-[12px]"}`}>
            <span className={`truncate ${compact ? "text-text-main" : "text-text-main"}`}>{item.label}</span>
            <span className="font-mono text-text-variant">{item.count}</span>
          </div>
          <div className="h-2 rounded-full bg-surface-high">
            <div className="h-2 rounded-full bg-primary/75" style={{ width: ratioWidth(item.count, total) }} />
          </div>
          {showDetails && item.detail ? (
            <p className="text-[11px] leading-relaxed text-text-dim">{previewText(item.detail, compact ? 90 : 140)}</p>
          ) : null}
        </div>
      ))}
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
          className="rounded-md border border-outline/40 bg-surface/60 px-3 py-2 text-[12px] leading-relaxed text-text-variant"
        >
          {sample}
        </div>
      ))}
      {samples.length > 2 ? (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className={`inline-flex items-center gap-1 rounded border border-outline/40 bg-surface/50 px-2 py-1 text-[11px] text-text-dim hover:bg-surface/70 ${FOCUS_RING}`}
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
            <div className="text-[12px] font-medium text-text-main">{title}</div>
            {badge ? <InlineBadge>{badge}</InlineBadge> : null}
          </div>
          {subtitle ? <p className="mt-1 text-[12px] leading-relaxed text-text-dim">{subtitle}</p> : null}
        </div>
        <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wide text-text-dim">
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
      <div className="text-[10px] font-medium uppercase tracking-wide text-text-dim">{title}</div>
      {subtitle ? <p className="mt-1 text-[12px] leading-relaxed text-text-variant">{subtitle}</p> : null}
    </div>
  )
}

function SubsectionTitle({ title, subtitle }: { title: string; subtitle?: string | null }) {
  return (
    <div>
      <div className="text-[11px] font-medium uppercase tracking-wide text-text-dim">{title}</div>
      {subtitle ? <p className="mt-1 text-[12px] leading-relaxed text-text-variant">{subtitle}</p> : null}
    </div>
  )
}

function InlineBadge({ children }: { children: ReactNode }) {
  return (
    <span className="rounded border border-outline/50 bg-surface/60 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-text-dim">
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
      <div className="text-[9px] uppercase tracking-wide text-text-dim">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="font-mono text-[18px] text-text-main">{value}</span>
        {hint ? <span className="truncate text-[10px] text-text-variant">{hint}</span> : null}
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
          launch?.configPath ? (
            <span className="font-mono text-[11px]">Config: {launch.configPath}</span>
          ) : (
            "Open a trial for evaluation and the run transcript."
          )
        }
        meta={
          launch?.status ? (
            <span className="rounded-lg border border-outline/50 bg-surface/60 px-2.5 py-1 font-mono text-[11px] text-text-variant backdrop-blur">
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

      {query.isLoading ? (
        <p className="text-[13px] text-text-variant">Loading job…</p>
      ) : query.isError ? (
        <p className="text-[13px] text-danger">
          {query.error instanceof ApiError ? query.error.message : "Failed to load job."}
        </p>
      ) : (
        <>
          {launch?.error && (
            <div className="mb-4 rounded-lg border border-danger/40 bg-danger/10 px-4 py-3 text-[13px] text-danger">
              {launch.error}
            </div>
          )}

          {progress.total > 0 && !aggregation && (
            <StudioGlassPanel className="mb-5 flex flex-wrap items-center gap-3 px-4 py-3 text-[12px] text-text-variant">
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
              applicationType={(job as { applicationType?: string | null } | undefined)?.applicationType}
            />
          )}

          <StudioGlassPanel className="overflow-hidden rounded-xl">
            <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_5.5rem_2rem] gap-3 border-b border-outline/40 px-4 py-2.5 text-[10px] uppercase tracking-wide text-text-dim">
              <span>Persona</span>
              <span>Trial</span>
              <span>Status</span>
              <span className="sr-only">Open</span>
            </div>
            <ul className="divide-y divide-outline-dim">
              {trials.length === 0 ? (
                <li className="px-4 py-8 text-center text-[13px] text-text-variant">
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
                        className={`grid w-full grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_5.5rem_2rem] items-center gap-3 px-4 py-3 text-left text-[13px] ${
                          clickable ? "hover:bg-surface/40" : ""
                        } ${FOCUS_RING}`}
                      >
                        <span className="truncate font-medium text-text-main">
                          {trialPersonaLabel(trial)}
                        </span>
                        <span className="truncate font-mono text-[11px] text-text-variant">
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
