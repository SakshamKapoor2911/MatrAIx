/**
 * Persona Curation Cockpit — the application shell.
 *
 * A full-viewport flex column: a top bar (product name, backend-status dot,
 * protocol id/version), the lineage rail + control strip, then a three-column
 * cockpit (catalog · dossier · inspector). The inspector is a segmented
 * Profile / Dimensions / Audit tab set. Selection is a `global_idx` so it
 * survives catalog re-sorting; the dimensions/audit inspectors join the
 * selected person back to `result_preview` by QID.
 */
import { useMemo, useState } from "react";

import { Sym, FOCUS_RING, humanizeToken } from "@/components/cockpit/cockpitShared";
import { Chip, Empty, Fingerprint, MetricTile, SectionLabel, Spinner } from "@/components/cockpit/Primitives";
import { LineageRail } from "@/components/LineageRail";
import { ControlStrip } from "@/components/ControlStrip";
import { PersonaCatalog } from "@/components/PersonaCatalog";
import { PersonDossier } from "@/components/PersonDossier";
import { DimensionsPanel } from "@/components/DimensionsPanel";
import { AuditPanel } from "@/components/AuditPanel";
import { useAppState, useDimensions } from "@/lib/hooks";
import { fmtInt } from "@/lib/format";
import { ApiError } from "@/lib/api";
import type { AppState, Profile, ResultField, ResultRow } from "@/lib/types";

type Tab = "profile" | "dimensions" | "audit";

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: "profile", label: "Profile", icon: "badge" },
  { key: "dimensions", label: "Dimensions", icon: "tune" },
  { key: "audit", label: "Audit", icon: "fact_check" },
];

// ---------------------------------------------------------------------------
// Field join: select the result row for the active person, build a field Map.
// ---------------------------------------------------------------------------

function rowForProfile(state: AppState, profile: Profile | undefined): ResultRow | undefined {
  const preview = state.result_preview;
  if (!preview || preview.rows.length === 0) return undefined;
  if (profile) {
    const byQid = preview.rows.find((r) => r.qid !== null && r.qid === profile.qid);
    if (byQid) return byQid;
  }
  return preview.rows[0];
}

function fieldMap(row: ResultRow | undefined): Map<string, ResultField> {
  const map = new Map<string, ResultField>();
  if (!row) return map;
  for (const field of row.fields) {
    if (field.field_id) map.set(field.field_id, field);
  }
  return map;
}

// ---------------------------------------------------------------------------
// Top bar
// ---------------------------------------------------------------------------

function TopBar({ state }: { state: AppState }) {
  const { backend_status, protocol_manifest } = state;
  const ready = Boolean(backend_status.claude_bin);
  return (
    <header className="flex items-center justify-between gap-md border-b border-border-soft bg-surface-container-lowest px-md py-sm">
      <div className="flex items-center gap-sm">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-on-primary">
          <Sym name="hub" size={18} fill={1} />
        </span>
        <h1 className="font-headline-md text-on-surface">Persona Curation Cockpit</h1>
      </div>
      <div className="flex items-center gap-md">
        <div className="flex items-center gap-xs" title={ready ? "claude binary detected" : "claude binary not found"}>
          <span className={`h-2 w-2 rounded-full ${ready ? "bg-success" : "bg-warning"}`} />
          <code className="font-mono-sm text-on-surface-variant">{backend_status.claude_command}</code>
        </div>
        <Chip tone="primary" title={`protocol ${protocol_manifest.protocol_id}`}>
          {protocol_manifest.protocol_id} · v{protocol_manifest.protocol_version}
        </Chip>
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// Profile inspector tab — compact provenance summary
// ---------------------------------------------------------------------------

function ProfileInspector({
  profile,
  fields,
}: {
  profile: Profile | undefined;
  fields: Map<string, ResultField>;
}) {
  if (!profile) {
    return (
      <div className="p-md">
        <Empty icon="person_off" title="No person selected" />
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-md p-md">
      <div className="flex flex-col gap-sm">
        <SectionLabel>Provenance</SectionLabel>
        <div className="flex flex-wrap items-center gap-1.5">
          <Chip tone="primary" title={profile.qid}>
            {profile.qid}
          </Chip>
          {profile.entity_type ? <Chip tone="neutral">{profile.entity_type}</Chip> : null}
          <Chip tone="neutral">idx {profile.global_idx}</Chip>
          {profile.revision_id !== null ? <Chip tone="neutral">rev {profile.revision_id}</Chip> : null}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Fingerprint value={profile.input_sha256} label="input sha" />
        </div>
        {profile.tags.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1">
            {profile.tags.map((t) => (
              <Chip key={t} tone="neutral">
                {humanizeToken(t)}
              </Chip>
            ))}
          </div>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-sm">
        <MetricTile label="Characters" value={fmtInt(profile.profile_text.length)} hint="profile_text" />
        <MetricTile label="Fields" value={fmtInt(fields.size)} hint="attributed" />
      </div>

      {profile.source_url ? (
        <a
          href={profile.source_url}
          target="_blank"
          rel="noreferrer"
          className={`inline-flex items-center gap-xs font-body-md text-primary hover:underline ${FOCUS_RING}`}
        >
          {profile.source_url}
          <Sym name="open_in_new" size={14} />
        </a>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inspector with the segmented tab control
// ---------------------------------------------------------------------------

function Inspector({
  state,
  profile,
  fields,
}: {
  state: AppState;
  profile: Profile | undefined;
  fields: Map<string, ResultField>;
}) {
  const [tab, setTab] = useState<Tab>("profile");
  const dims = useDimensions();

  return (
    <div className="flex h-full flex-col border-l border-border-soft bg-surface-container-low">
      <div className="border-b border-border-soft px-md py-sm">
        <div className="inline-flex rounded-lg border border-border-soft bg-surface-container p-0.5">
          {TABS.map((t) => {
            const active = t.key === tab;
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                aria-pressed={active}
                className={[
                  "inline-flex items-center gap-xs rounded-md px-3 py-1.5 font-body-sm transition-colors",
                  FOCUS_RING,
                  active
                    ? "bg-surface-container-lowest text-on-surface shadow-soft"
                    : "text-on-surface-variant hover:text-on-surface",
                ].join(" ")}
              >
                <Sym name={t.icon} size={16} fill={active ? 1 : 0} />
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="custom-scrollbar flex-1 overflow-y-auto">
        {tab === "profile" ? <ProfileInspector profile={profile} fields={fields} /> : null}
        {tab === "dimensions" ? (
          <DimensionsPanel catalog={dims.data} catalogError={dims.error} fields={fields} />
        ) : null}
        {tab === "audit" ? <AuditPanel report={state.audit_report} /> : null}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const stateQuery = useAppState();
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const state = stateQuery.data;
  const profiles = state?.profiles ?? [];

  // Default selection: the first profile's global_idx, once data lands.
  const activeIdx = useMemo(() => {
    if (selectedIdx !== null) return selectedIdx;
    return profiles[0]?.global_idx ?? 0;
  }, [selectedIdx, profiles]);

  const profile = useMemo(
    () => profiles.find((p) => p.global_idx === activeIdx),
    [profiles, activeIdx],
  );

  const fields = useMemo(
    () => (state ? fieldMap(rowForProfile(state, profile)) : new Map<string, ResultField>()),
    [state, profile],
  );

  if (stateQuery.isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-sm text-on-surface-variant">
          <Spinner size={28} className="text-primary" />
          <p className="font-body-md">Loading cockpit state…</p>
        </div>
      </div>
    );
  }

  if (stateQuery.isError || !state) {
    const err = stateQuery.error;
    const message =
      err instanceof ApiError
        ? `${err.status ? `${err.status}: ` : ""}${err.message}`
        : err instanceof Error
          ? err.message
          : "Failed to load cockpit state.";
    return (
      <div className="flex h-full items-center justify-center bg-background px-md">
        <div className="flex max-w-md flex-col items-center gap-md rounded-xl border border-border-soft bg-surface-container-lowest p-lg text-center shadow-soft">
          <Sym name="cloud_off" size={32} className="text-error" />
          <h2 className="font-headline-md text-on-surface">Couldn’t load state</h2>
          <p className="font-body-md text-on-surface-variant">{message}</p>
          <button
            type="button"
            onClick={() => void stateQuery.refetch()}
            className={`inline-flex items-center gap-xs rounded-lg bg-primary px-4 py-2 font-body-md text-on-primary hover:bg-primary-container ${FOCUS_RING}`}
          >
            <Sym name="refresh" size={18} />
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background text-on-surface">
      <TopBar state={state} />
      <LineageRail state={state} />
      <ControlStrip state={state} />

      <main className="grid min-h-0 flex-1 grid-cols-[320px_minmax(0,1fr)_420px]">
        <PersonaCatalog profiles={profiles} selectedIdx={activeIdx} onSelect={setSelectedIdx} />
        <section className="min-h-0 overflow-hidden">
          {profile ? (
            <PersonDossier profile={profile} />
          ) : (
            <div className="flex h-full items-center justify-center">
              <Empty icon="person_search" title="No profiles" hint="The catalog is empty." />
            </div>
          )}
        </section>
        <Inspector state={state} profile={profile} fields={fields} />
      </main>
    </div>
  );
}
