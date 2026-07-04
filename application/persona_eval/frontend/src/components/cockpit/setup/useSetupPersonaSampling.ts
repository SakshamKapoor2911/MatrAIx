import { useCallback, useEffect, useState } from "react";

import type { HarborCockpitTaskKind } from "@/lib/harborCockpitMappers";
import type { ConfigOptionsResponse, PersonaEvalPersona } from "@/lib/types";

import {
  readCockpitPersonaSetup,
  writeCockpitPersonaSetup,
} from "./cockpitPersonaSetupStorage";
import {
  type PersonaDimensionFilters,
  type PersonaSamplingMode,
} from "./personaSamplingTypes";

export function useSetupPersonaSampling(
  options: ConfigOptionsResponse | null,
  taskKind: HarborCockpitTaskKind,
) {
  const fallbackPersonaModel =
    taskKind === "os-app"
      ? "anthropic/claude-sonnet-4-6"
      : options?.environment.personaModel ?? "anthropic/claude-haiku-4-5";
  const [initial] = useState(() => readCockpitPersonaSetup(taskKind, fallbackPersonaModel));

  const [personaModel, setPersonaModel] = useState<string>(initial.personaModel);
  const [samplingMode, setSamplingMode] = useState<PersonaSamplingMode>(initial.samplingMode);
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<string[]>(initial.selectedPersonaIds);
  const [groupFilters, setGroupFilters] = useState<PersonaDimensionFilters>(initial.groupFilters);
  const [stratifyFields, setStratifyFields] = useState<string[]>(initial.stratifyFields);
  const [sampleSize, setSampleSize] = useState(initial.sampleSize);
  const [seed] = useState(42);
  const [parallelTrials, setParallelTrials] = useState(initial.parallelTrials);
  const [persona, setPersona] = useState<PersonaEvalPersona | null>(null);

  useEffect(() => {
    writeCockpitPersonaSetup(taskKind, {
      selectedPersonaIds,
      samplingMode,
      groupFilters,
      stratifyFields,
      sampleSize,
      parallelTrials,
      personaModel,
    });
  }, [
    taskKind,
    selectedPersonaIds,
    samplingMode,
    groupFilters,
    stratifyFields,
    sampleSize,
    parallelTrials,
    personaModel,
  ]);

  useEffect(() => {
    const id = selectedPersonaIds[0];
    if (!id) {
      setPersona(null);
      return;
    }
    setPersona({
      id,
      name: `persona-${id}`,
      source: "bench-dev-sample",
    });
  }, [selectedPersonaIds]);

  const isBatchRun = samplingMode !== "single" || selectedPersonaIds.length > 1;

  const personaModelKnob = options?.knobs.find((k) => k.key === "personaModel");
  const personaModelOptions =
    personaModelKnob?.options.map((o) => ({
      value: o.value,
      label: o.label,
      summary: o.description?.trim() || undefined,
    })) ?? [{ value: personaModel, label: personaModel }];

  const togglePersona = useCallback(
    (personaId: string) => {
      if (samplingMode === "single") {
        setSelectedPersonaIds((prev) => (prev.includes(personaId) ? [] : [personaId]));
        return;
      }
      setSelectedPersonaIds((prev) =>
        prev.includes(personaId) ? prev.filter((id) => id !== personaId) : [...prev, personaId],
      );
    },
    [samplingMode],
  );

  return {
    persona,
    personaModel,
    setPersonaModel,
    personaModelOptions,
    samplingMode,
    setSamplingMode,
    selectedPersonaIds,
    setSelectedPersonaIds,
    togglePersona,
    groupFilters,
    setGroupFilters,
    stratifyFields,
    setStratifyFields,
    sampleSize,
    setSampleSize,
    seed,
    parallelTrials,
    setParallelTrials,
    isBatchRun,
  };
}
