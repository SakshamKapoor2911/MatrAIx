import { useCallback, useEffect, useState } from "react";

import type { ConfigOptionsResponse, PersonaEvalPersona } from "@/lib/types";
import {
  emptyPersonaDimensionFilters,
  type PersonaDimensionFilters,
  type PersonaSamplingMode,
} from "./personaSamplingTypes";

export function useSetupPersonaSampling(options: ConfigOptionsResponse | null) {
  const [personaModel, setPersonaModel] = useState<string>(
    options?.environment.personaModel ?? "anthropic/claude-haiku-4-5",
  );
  const [samplingMode, setSamplingMode] = useState<PersonaSamplingMode>("single");
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<string[]>([]);
  const [groupFilters, setGroupFilters] = useState<PersonaDimensionFilters>(emptyPersonaDimensionFilters());
  const [stratifyFields, setStratifyFields] = useState<string[]>(["age_bracket", "region"]);
  const [sampleSize, setSampleSize] = useState(4);
  const [seed] = useState(42);
  const [parallelTrials, setParallelTrials] = useState(2);
  const [persona, setPersona] = useState<PersonaEvalPersona | null>(null);

  useEffect(() => {
    if (!options?.environment.personaModel) return;
    setPersonaModel(options.environment.personaModel);
  }, [options?.environment.personaModel]);

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
    personaModelKnob?.options.map((o) => ({ value: o.value, label: o.label })) ?? [
      { value: personaModel, label: personaModel },
    ];

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
