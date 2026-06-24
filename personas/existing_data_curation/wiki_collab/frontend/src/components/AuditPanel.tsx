/**
 * RIGHT inspector — the audit report for the latest returned archives. Summary
 * tiles (accept/reject, valid/failed, duplicates), a coverage line, the
 * assignment-type + confidence distributions as labelled count bars, and a
 * per-archive breakdown. Null report → an instructive empty state.
 */
import { humanizeToken } from "@/components/cockpit/cockpitShared";
import { Chip, Empty, MetricTile, SectionLabel } from "@/components/cockpit/Primitives";
import { fmtInt, pct } from "@/lib/format";
import type { AuditArchive, AuditReport, CountMap } from "@/lib/types";

function basename(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

function CountBars({ title, counts }: { title: string; counts: CountMap }) {
  const entries = Object.entries(counts);
  const max = entries.reduce((m, [, n]) => Math.max(m, n), 0);
  return (
    <div className="flex flex-col gap-sm">
      <SectionLabel>{title}</SectionLabel>
      {entries.length === 0 ? (
        <p className="font-body-sm italic text-on-surface-variant">none</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {entries.map(([label, n]) => (
            <li key={label} className="flex items-center gap-sm">
              <span className="w-28 shrink-0 truncate font-body-sm text-on-surface" title={label}>
                {humanizeToken(label)}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-container-high">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${max > 0 ? pct(n, max) : 0}%` }}
                />
              </div>
              <span className="w-10 shrink-0 text-right font-mono-sm tabular-nums text-on-surface-variant">
                {fmtInt(n)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ArchiveCard({ archive }: { archive: AuditArchive }) {
  const errors = archive.errors.slice(0, 2);
  return (
    <li className="flex flex-col gap-sm rounded-lg border border-border-soft bg-surface-container-lowest px-3 py-2 shadow-soft">
      <div className="flex items-center justify-between gap-sm">
        <span className="truncate font-mono-sm text-on-surface" title={archive.archive_path}>
          {basename(archive.archive_path)}
        </span>
        <Chip tone={archive.accepted ? "success" : "error"}>
          {archive.accepted ? "accepted" : "rejected"}
        </Chip>
      </div>
      <div className="flex flex-wrap items-center gap-1">
        <Chip tone="neutral">{fmtInt(archive.valid_rows)} valid</Chip>
        {archive.failed_rows > 0 ? (
          <Chip tone="warning">{fmtInt(archive.failed_rows)} failed</Chip>
        ) : null}
        {archive.worker_id ? (
          <span className="font-mono-sm text-outline" title="worker">
            {archive.worker_id}
          </span>
        ) : null}
      </div>
      {errors.length > 0 ? (
        <ul className="flex flex-col gap-0.5">
          {errors.map((err, i) => (
            <li key={i} className="font-body-sm text-on-error-container" title={err}>
              <span className="line-clamp-1">{err}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export function AuditPanel({ report }: { report: AuditReport | null }) {
  if (!report) {
    return (
      <div className="p-md">
        <Empty
          icon="fact_check"
          title="No audit yet"
          hint="Run → Return → Audit first to validate worker output and produce an audit report."
        />
      </div>
    );
  }

  const { summary, coverage, archives } = report;
  const coveredPct = Math.round(pct(coverage.covered_rows, coverage.assigned_rows));

  return (
    <div className="flex flex-col gap-md p-md">
      <div className="flex flex-col gap-sm">
        <SectionLabel>Audit summary</SectionLabel>
        <div className="grid grid-cols-2 gap-sm">
          <MetricTile
            label="Archives"
            value={`${fmtInt(summary.accepted_archives)} / ${fmtInt(summary.archive_count)}`}
            hint={`${fmtInt(summary.rejected_archives)} rejected`}
          />
          <MetricTile
            label="Rows"
            value={`${fmtInt(summary.valid_rows)} valid`}
            hint={`${fmtInt(summary.failed_rows)} failed`}
          />
          <MetricTile label="Duplicates" value={fmtInt(summary.duplicate_rows)} hint="repeated rows" />
          <MetricTile
            label="Coverage"
            value={`${fmtInt(coverage.covered_rows)} / ${fmtInt(coverage.assigned_rows)}`}
            hint={`${coveredPct}% · ${fmtInt(coverage.missing_assigned_rows)} missing`}
          />
        </div>
      </div>

      <CountBars title="Assignment types" counts={summary.assignment_type_counts} />
      <CountBars title="Confidence buckets" counts={summary.confidence_buckets} />

      <div className="flex flex-col gap-sm">
        <SectionLabel>Archives</SectionLabel>
        {archives.length === 0 ? (
          <p className="font-body-sm italic text-on-surface-variant">no archives</p>
        ) : (
          <ul className="flex flex-col gap-sm">
            {archives.map((a) => (
              <ArchiveCard key={a.archive_path} archive={a} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
