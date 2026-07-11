import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { HarborCockpitTaskKind } from "@/lib/harborCockpitMappers";
import type { ConfigOptionsResponse, PlaygroundPersona, TaskPersonaStrategy } from "@/lib/types";

import {
  defaultPersonaSetup,
  hasStoredPersonaSetup,
  readCockpitPersonaSetup,
  setupFromPersonaStrategy,
  writeCockpitPersonaSetup,
} from "./cockpitPersonaSetupStorage";
import {
  type PersonaDimensionFilters,
  type PersonaSamplingMode,
} from "./personaSamplingTypes";

export function useSetupPersonaSampling(
  options: ConfigOptionsResponse | null,
  taskKind: HarborCockpitTaskKind,
  taskPath: string | null = null,
) {
  const fallbackPersonaModel =
    taskKind === "os-app"
      ? "anthropic/claude-sonnet-4-6"
      : options?.environment.personaModel ?? "anthropic/claude-haiku-4-5";
  const normalizedPath = taskPath?.trim() || null;
  const [initial] = useState(() =>
    readCockpitPersonaSetup(taskKind, fallbackPersonaModel, normalizedPath),
  );

  const [personaModel, setPersonaModel] = useState<string>(initial.personaModel);
  const [samplingMode, setSamplingMode] = useState<PersonaSamplingMode>(initial.samplingMode);
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<string[]>(initial.selectedPersonaIds);
  const [groupFilters, setGroupFilters] = useState<PersonaDimensionFilters>(initial.groupFilters);
  const [stratifyFields, setStratifyFields] = useState<string[]>(initial.stratifyFields);
  const [sampleSize, setSampleSize] = useState(initial.sampleSize);
  const [seed] = useState(42);
  const [parallelTrials, setParallelTrials] = useState(initial.parallelTrials);
  const [persona, setPersona] = useState<PlaygroundPersona | null>(null);
  const [taskPersonaStrategy, setTaskPersonaStrategy] = useState<TaskPersonaStrategy | null>(null);
  const [useTaskDefaultStrategy, setUseTaskDefaultStrategyState] = useState(
    initial.useTaskDefaultStrategy,
  );
  const hydratedPathRef = useRef<string | null>(null);
  const skipNextPersistRef = useRef(false);

  const strategyQuery = useQuery({
    queryKey: ["task-persona-strategy", normalizedPath],
    queryFn: async () => {
      if (!normalizedPath) return null;
      const detail = await api.getTaskDetail(normalizedPath);
      return detail.personaStrategy ?? null;
    },
    enabled: Boolean(normalizedPath),
    staleTime: 60_000,
  });

  const applySetupRecord = useCallback((record: ReturnType<typeof defaultPersonaSetup>) => {
    skipNextPersistRef.current = true;
    setSamplingMode(record.samplingMode);
    setSelectedPersonaIds(record.selectedPersonaIds);
    setGroupFilters(record.groupFilters);
    setStratifyFields(record.stratifyFields);
    setSampleSize(record.sampleSize);
    setPersonaModel(record.personaModel);
    setParallelTrials(record.parallelTrials);
    setUseTaskDefaultStrategyState(record.useTaskDefaultStrategy);
  }, []);

  const resetToTaskStrategy = useCallback(() => {
    const strategy = strategyQuery.data ?? taskPersonaStrategy;
    const applied = setupFromPersonaStrategy(strategy, fallbackPersonaModel, {
      ...defaultPersonaSetup(fallbackPersonaModel),
      personaModel,
      parallelTrials,
    });
    applySetupRecord(applied);
    setTaskPersonaStrategy(strategy);
  }, [
    applySetupRecord,
    fallbackPersonaModel,
    parallelTrials,
    personaModel,
    strategyQuery.data,
    taskPersonaStrategy,
  ]);

  const setUseTaskDefaultStrategy = useCallback(
    (next: boolean) => {
      if (next) {
        resetToTaskStrategy();
        return;
      }
      setUseTaskDefaultStrategyState(false);
    },
    [resetToTaskStrategy],
  );

  useEffect(() => {
    setTaskPersonaStrategy(strategyQuery.data ?? null);
  }, [strategyQuery.data]);

  useEffect(() => {
    const path = normalizedPath;
    if (!path) {
      hydratedPathRef.current = null;
      return;
    }
    if (hydratedPathRef.current === path) return;

    // Wait for strategy fetch so default-on can re-apply persona_strategy.json.
    if (strategyQuery.isFetching || strategyQuery.isLoading) return;

    const stored = readCockpitPersonaSetup(taskKind, fallbackPersonaModel, path);
    if (hasStoredPersonaSetup(path)) {
      if (stored.useTaskDefaultStrategy && strategyQuery.data) {
        const applied = setupFromPersonaStrategy(strategyQuery.data, fallbackPersonaModel, {
          ...defaultPersonaSetup(fallbackPersonaModel),
          personaModel: stored.personaModel,
          parallelTrials: stored.parallelTrials,
        });
        applySetupRecord(applied);
      } else {
        applySetupRecord({
          ...stored,
          useTaskDefaultStrategy: stored.useTaskDefaultStrategy && Boolean(strategyQuery.data),
        });
      }
      hydratedPathRef.current = path;
      return;
    }

    const applied = setupFromPersonaStrategy(strategyQuery.data, fallbackPersonaModel, {
      ...defaultPersonaSetup(fallbackPersonaModel),
      personaModel: stored.personaModel,
      parallelTrials: stored.parallelTrials,
    });
    applySetupRecord(applied);
    hydratedPathRef.current = path;
  }, [
    applySetupRecord,
    fallbackPersonaModel,
    normalizedPath,
    strategyQuery.data,
    strategyQuery.isFetching,
    strategyQuery.isLoading,
    taskKind,
  ]);

  useEffect(() => {
    if (skipNextPersistRef.current) {
      skipNextPersistRef.current = false;
      return;
    }
    writeCockpitPersonaSetup(
      taskKind,
      {
        selectedPersonaIds,
        samplingMode,
        groupFilters,
        stratifyFields,
        sampleSize,
        parallelTrials,
        personaModel,
        useTaskDefaultStrategy,
      },
      normalizedPath,
    );
  }, [
    taskKind,
    normalizedPath,
    selectedPersonaIds,
    samplingMode,
    groupFilters,
    stratifyFields,
    sampleSize,
    parallelTrials,
    personaModel,
    useTaskDefaultStrategy,
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

  const hasTaskStrategy = Boolean(taskPersonaStrategy);

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
    hasTaskStrategy,
    taskPersonaStrategy,
    useTaskDefaultStrategy: hasTaskStrategy && useTaskDefaultStrategy,
    setUseTaskDefaultStrategy,
  };
}
