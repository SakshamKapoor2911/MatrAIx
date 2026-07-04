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
};

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

function orderedContexts(contexts: AggregationContext[]): AggregationContext[] {
  return [...contexts].sort((a, b) => {
    const aOrder = contextTypeMeta(a.contextType)?.order ?? 99
    const bOrder = contextTypeMeta(b.contextType)?.order ?? 99
    if (aOrder !== bOrder) return aOrder - bOrder
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
  if (summary) return previewText(summary, 120)
  const explanation = explanationFacetForContext(context)
  if (explanation?.textual?.summary) return previewText(explanation.textual.summary, 120)
  if ((explanation?.textual?.samples?.length ?? 0) > 0) {
    return previewText(explanation?.textual?.samples?.[0] ?? "", 120)
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

function AggregationDashboard({ aggregation }: { aggregation: HarborJobAggregation }) {
  const [open, setOpen] = useState(false)
  const contexts = useMemo(() => orderedContexts(aggregation.contexts ?? []), [aggregation.contexts])
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
        {hasDetails ? (
          <div className="mt-3 space-y-2">
            <button
              type="button"
              onClick={() => setOpen((value) => !value)}
              aria-expanded={open}
              className={`glow flex w-full items-center justify-between gap-3 rounded-xl border px-3 py-3 text-left transition-colors ${FOCUS_RING} ${
                open
                  ? "border-primary bg-primary-dim text-on-primary hover:bg-primary"
                  : "border-primary bg-primary text-on-primary hover:bg-primary-dim"
              }`}
            >
              <div className="min-w-0">
                <div className="text-[12px] font-medium text-on-primary">
                  {open ? "Hide detailed report" : "Show detailed report"}
                </div>
                <div className="mt-1 text-[11px] leading-relaxed text-on-primary/80">
                  {detailCount} {detailLabel} of structured analysis
                </div>
              </div>
              <div className="inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/10 px-2.5 py-1.5 text-[11px] text-on-primary">
                <span>{open ? "Collapse" : "Expand"}</span>
                <Sym name={open ? "expand_less" : "expand_more"} size={16} />
              </div>
            </button>
            <p className="text-[11px] leading-relaxed text-text-dim">
              {open
                ? `Showing the full ${detailLabel === "contexts" ? "context" : "field"} report below.`
                : `The detailed ${detailLabel === "contexts" ? "context-level" : "field-level"} report is collapsed so the persona trial list stays visible.`}
            </p>
          </div>
        ) : null}
        {reporting?.error ? (
          <p className="mt-3 text-[12px] leading-relaxed text-danger">{reporting.error}</p>
        ) : null}
      </StudioGlassPanel>

      {open ? (
        contexts.length > 0 ? (
          <StudioGlassPanel className="overflow-hidden">
            <SectionHeader
              title="Contexts"
              subtitle="Context-first view: scan the top signal first, then expand for grouped reasons, judges, and evidence."
            />
            <div className="space-y-3 p-4">
              {contexts.map((context) => (
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
  const showDistribution = primaryFacet?.kind !== "categorical" && distributionItems.length > 0
  const analysisCount = summaryCount + judgeCount + relationshipCount
  const showPrimaryPreview = primaryFacet?.kind === "numerical" || !showDistribution

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
              <InlineBadge>{context.facets.length} signals</InlineBadge>
              {analysisCount > 0 ? <InlineBadge>{analysisCount} analyses</InlineBadge> : null}
            </div>
            {typeDescription ? (
              <p className="mt-1 text-[11px] leading-relaxed text-text-dim">{typeDescription}</p>
            ) : null}
            {leadText ? (
              <p className="mt-1.5 max-w-4xl text-[11px] leading-relaxed text-text-variant">{leadText}</p>
            ) : null}
          </div>
          <span className="inline-flex items-center gap-1 rounded-md border border-outline/50 bg-surface/60 px-2 py-1 text-[10px] uppercase tracking-wide text-text-dim">
            {open ? "Collapse" : "Expand"}
            <Sym name={open ? "expand_less" : "expand_more"} size={14} />
          </span>
        </div>

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
        </div>
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

          {aggregation && <AggregationDashboard aggregation={aggregation} />}

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
