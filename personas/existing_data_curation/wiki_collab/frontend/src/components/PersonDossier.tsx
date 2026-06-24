/**
 * CENTER column — the dossier for the selected person. A header of provenance
 * chips + an input-hash fingerprint + the external source link, then the
 * profile text rendered as a readable prose column (split on blank lines into
 * paragraphs). This is the v1 "clean page"; the richer /api/full-page loader
 * can replace `profile_text` later.
 */
import { Sym, FOCUS_RING } from "@/components/cockpit/cockpitShared";
import { Chip, Fingerprint } from "@/components/cockpit/Primitives";
import { fmtInt } from "@/lib/format";
import type { Profile } from "@/lib/types";

function paragraphs(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

export function PersonDossier({ profile }: { profile: Profile }) {
  const paras = paragraphs(profile.profile_text);

  return (
    <div className="custom-scrollbar h-full overflow-y-auto bg-surface">
      <div className="mx-auto flex max-w-3xl flex-col gap-lg px-lg py-lg">
        {/* Header */}
        <header className="flex flex-col gap-sm">
          <h1 className="font-display text-on-surface">{profile.title}</h1>
          <div className="flex flex-wrap items-center gap-1.5">
            <Chip tone="primary" title={profile.qid}>
              {profile.qid}
            </Chip>
            {profile.entity_type ? <Chip tone="neutral">{profile.entity_type}</Chip> : null}
            {profile.revision_id !== null ? (
              <Chip tone="neutral" title={profile.revision_timestamp ?? undefined}>
                rev {profile.revision_id}
              </Chip>
            ) : null}
            <Chip tone="neutral">idx {profile.global_idx}</Chip>
            <Chip tone="neutral" title="profile_text length">
              {fmtInt(profile.profile_text.length)} chars
            </Chip>
            <Fingerprint value={profile.input_sha256} label="sha" />
            {profile.source_url ? (
              <a
                href={profile.source_url}
                target="_blank"
                rel="noreferrer"
                className={`inline-flex items-center gap-xs rounded-md px-2 py-0.5 font-body-sm text-primary hover:underline ${FOCUS_RING}`}
              >
                source
                <Sym name="open_in_new" size={14} />
              </a>
            ) : null}
          </div>
        </header>

        {/* Body */}
        <article className="flex max-w-thread flex-col gap-md">
          {paras.length > 0 ? (
            paras.map((p, i) => (
              <p key={i} className="whitespace-pre-wrap font-body-lg text-on-surface">
                {p}
              </p>
            ))
          ) : (
            <p className="font-body-md italic text-on-surface-variant">No profile text available.</p>
          )}
        </article>

        <p className="flex items-center gap-xs rounded-lg border border-border-soft bg-surface-container-low px-3 py-2 font-body-sm text-on-surface-variant">
          <Sym name="info" size={16} className="text-outline" />
          The 4 demo profiles are short samples — the full clean-page loader will
          replace this preview text.
        </p>
      </div>
    </div>
  );
}
