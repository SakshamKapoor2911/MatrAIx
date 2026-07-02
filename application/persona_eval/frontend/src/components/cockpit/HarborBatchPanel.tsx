/**
 * Launch a Harbor job from the cockpit — single selected persona or sampled batch.
 */
import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import { FOCUS_RING, Sym } from "./cockpitShared";
import {
  PersonaGroupBuilder,
  emptyPersonaGroupFilters,
  type PersonaGroupFilters,
} from "./PersonaGroupBuilder";

export type HarborLaunchMode = "auto" | "force_docker";

export interface HarborBatchPanelProps {
  taskPath: string;
  personaModel: string;
  /** When set, launch exactly this persona (Harbor N=1). */
  personaId?: string | null;
  defaultSampleSize?: number;
  onLaunched?: (jobName: string) => void;
}

function activeDimensionFilters(filters: PersonaGroupFilters): Record<string, string> | undefined {
  const entries = Object.entries(filters.dimensionFilters).filter(([, value]) => value.trim());
  return entries.length ? Object.fromEntries(entries) : undefined;
}

export function HarborBatchPanel({
  taskPath,
  personaModel,
  personaId = null,
  defaultSampleSize = 4,
  onLaunched,
}: HarborBatchPanelProps) {
  const useSelectedPersona = Boolean(personaId);
  const [sampleSize, setSampleSize] = useState(defaultSampleSize);
  const [seed, setSeed] = useState(42);
  const [mode, setMode] = useState<HarborLaunchMode>("auto");
  const [groupFilters, setGroupFilters] = useState<PersonaGroupFilters>(emptyPersonaGroupFilters);
  const [selectedCohortId, setSelectedCohortId] = useState<string | null>(null);
  const [lastJob, setLastJob] = useState<string | null>(null);
  const [lastConfigPath, setLastConfigPath] = useState<string | null>(null);
  const [lastJobsDir, setLastJobsDir] = useState<string | null>(null);
  const [lastProfile, setLastProfile] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const launchLabel = useMemo(() => {
    if (useSelectedPersona) return "Launch Harbor job (selected persona)";
    return "Launch Harbor job";
  }, [useSelectedPersona]);

  const mutation = useMutation({
    mutationFn: () => {
      const trialCount = useSelectedPersona ? 1 : sampleSize;
      const dimensionFilters = activeDimensionFilters(groupFilters);
      const personaSources = groupFilters.sources.length ? groupFilters.sources : undefined;
      return api.launchHarborJob({
        taskPath,
        sampleSize: trialCount,
        seed,
        personaModel,
        personaIds: useSelectedPersona && personaId ? [personaId] : undefined,
        personaSources: selectedCohortId ? undefined : personaSources,
        personaFilters: selectedCohortId ? undefined : dimensionFilters,
        cohortId: selectedCohortId,
        nConcurrentTrials: Math.min(4, trialCount),
        mode,
      });
    },
    onSuccess: (data) => {
      setLastJob(data.jobName);
      setLastConfigPath(data.configPath ?? null);
      setLastJobsDir(data.jobsDir ?? null);
      setLastProfile(data.trialProfile ?? null);
      setError(null);
      onLaunched?.(data.jobName);
    },
    onError: (err: unknown) => {
      setError(err instanceof ApiError ? err.message : "Launch failed.");
    },
  });

  return (
    <div className="rounded-md border border-outline bg-surface-low/60 px-4 py-3">
      <div className="mb-2 flex items-center gap-2">
        <Sym name="batch_prediction" size={18} className="text-primary" />
        <h3 className="text-[13px] font-semibold text-text-main">Harbor job</h3>
      </div>
      {useSelectedPersona ? (
        <p className="mb-3 text-[12px] leading-relaxed text-text-variant">
          Run the selected persona through Harbor (
          <span className="font-mono">{personaId}</span>). Artifacts land in{" "}
          <span className="font-mono">jobs/</span>.
        </p>
      ) : (
        <p className="mb-3 text-[12px] leading-relaxed text-text-variant">
          Filters pick a persona group; launch freezes it into a Harbor job YAML under{" "}
          <span className="font-mono">configs/jobs/application-task-job-recipe/</span>. Trial
          artifacts land in <span className="font-mono">jobs/</span>.
        </p>
      )}
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-[11px] text-text-variant">
          Mode
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as HarborLaunchMode)}
            className="h-9 rounded-md border border-outline bg-surface px-2 font-mono text-[12px] text-text-main"
          >
            <option value="auto">auto</option>
            <option value="force_docker">force_docker</option>
          </select>
        </label>
        {!useSelectedPersona && (
          <>
            <label className="flex flex-col gap-1 text-[11px] text-text-variant">
              Personas
              <input
                type="number"
                min={1}
                max={500}
                value={sampleSize}
                onChange={(e) => setSampleSize(Number(e.target.value) || 1)}
                className="h-9 w-24 rounded-md border border-outline bg-surface px-2 font-mono text-[13px] text-text-main"
              />
            </label>
            <label className="flex flex-col gap-1 text-[11px] text-text-variant">
              Seed
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value) || 42)}
                className="h-9 w-24 rounded-md border border-outline bg-surface px-2 font-mono text-[13px] text-text-main"
              />
            </label>
          </>
        )}
        <button
          type="button"
          disabled={mutation.isPending || (useSelectedPersona && !personaId)}
          onClick={() => mutation.mutate()}
          className={`flex h-9 items-center gap-1.5 rounded-md bg-primary px-4 text-[12px] text-on-primary hover:bg-primary-dim disabled:opacity-55 ${FOCUS_RING}`}
        >
          <Sym name="rocket_launch" size={16} />
          {mutation.isPending ? "Launching…" : launchLabel}
        </button>
      </div>

      {!useSelectedPersona && (
        <PersonaGroupBuilder
          sampleSize={sampleSize}
          seed={seed}
          filters={groupFilters}
          selectedCohortId={selectedCohortId}
          onFiltersChange={setGroupFilters}
          onSeedChange={setSeed}
          onSampleSizeChange={setSampleSize}
          onCohortChange={setSelectedCohortId}
        />
      )}

      {error && <p className="mt-2 text-[12px] text-danger">{error}</p>}
      {lastJob && !error && (
        <div className="mt-2 space-y-1 font-mono text-[11px] text-text-variant">
          <p>
            Job <span className="text-primary">{lastJob}</span>
            {lastProfile ? ` · profile ${lastProfile}` : ""}
          </p>
          {lastConfigPath && (
            <p>
              Recipe <span className="text-text-main">{lastConfigPath}</span>
            </p>
          )}
          {lastJobsDir && (
            <p>
              Artifacts <span className="text-text-main">{lastJobsDir}/{lastJob}/</span>
            </p>
          )}
          <p className="text-text-dim">Open Runs → Harbor jobs to monitor trials.</p>
        </div>
      )}
    </div>
  );
}

export default HarborBatchPanel;
