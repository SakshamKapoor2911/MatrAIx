/**
 * MatrAIx application shell.
 *
 * Routes: Home · Playground · Runs · Persona World.
 */
import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { TopBar, type StudioMode } from "@/components/TopBar";
import { PlaygroundCockpit } from "@/components/cockpit/PlaygroundCockpit";
import { HomeView } from "@/components/HomeView";
import { PersonaStoreView } from "@/components/PersonaStoreView";
import { RunsView } from "@/components/RunsView";
import { AppFooter } from "@/components/AppFooter";

import { api } from "@/lib/api";
import { useUrlState } from "@/lib/useUrlState";
import type { ConfigOptionsResponse, Domain } from "@/lib/types";

function parseMode(value: string | null): StudioMode {
  if (value === "playground") return "playground";
  return "home";
}

export default function App() {
  const { state: urlState, setState: setUrlState } = useUrlState();
  const mode = parseMode(urlState.mode);
  const activeHarborJobId = urlState.harborJob;
  const activeHarborTrialId = urlState.harborTrial;
  const storeViewActive = urlState.view === "store";
  const runsViewActive =
    urlState.view === "runs" || activeHarborJobId !== null || activeHarborTrialId !== null;

  const [, setPlaygroundDomain] = useState<Domain>("movie");
  const [playgroundFooter, setPlaygroundFooter] = useState<string>("survey");

  const optionsQuery = useQuery<ConfigOptionsResponse>({
    queryKey: ["config", "options"],
    queryFn: api.getConfigOptions,
    staleTime: Infinity,
  });

  const openHome = useCallback(() => {
    setUrlState({
      mode: null,
      view: null,
      harborJob: null,
      harborTrial: null,
    });
  }, [setUrlState]);

  const openPersonaStore = useCallback(() => {
    setUrlState({ view: "store", harborJob: null, harborTrial: null });
  }, [setUrlState]);

  const openRunsList = useCallback(() => {
    setUrlState({ view: "runs", harborJob: null, harborTrial: null });
  }, [setUrlState]);

  const openHarborJob = useCallback(
    (jobName: string) => {
      setUrlState({ view: "runs", harborJob: jobName, harborTrial: null });
    },
    [setUrlState],
  );

  const openHarborTrial = useCallback(
    (jobName: string, trialName: string) => {
      setUrlState({
        view: "runs",
        harborJob: jobName,
        harborTrial: trialName,
      });
    },
    [setUrlState],
  );

  const backToRunsList = useCallback(() => {
    setUrlState({ view: "runs", harborJob: null, harborTrial: null });
  }, [setUrlState]);

  const backToHarborJob = useCallback(() => {
    setUrlState({ view: "runs", harborTrial: null });
  }, [setUrlState]);

  const closeRunsView = useCallback(() => {
    setUrlState({ view: null, harborJob: null, harborTrial: null });
  }, [setUrlState]);

  const setMode = useCallback(
    (next: StudioMode) => {
      setUrlState({
        mode: next === "home" ? null : next,
        view: null,
        harborJob: null,
        harborTrial: null,
      });
    },
    [setUrlState],
  );

  const shellFooterContext = storeViewActive
    ? "persona world"
    : runsViewActive
      ? "runs"
      : mode === "playground"
        ? playgroundFooter
        : "home";

  const topBar = (
    <TopBar
      mode={mode}
      onModeChange={setMode}
      runsActive={runsViewActive}
      storeActive={storeViewActive}
      onOpenHome={openHome}
      onOpenRuns={openRunsList}
      onOpenPersonaStore={openPersonaStore}
    />
  );

  if (storeViewActive) {
    return (
      <div className="flex h-screen flex-col">
        {topBar}
        <PersonaStoreView />
        <AppFooter context={shellFooterContext} />
      </div>
    );
  }

  if (runsViewActive) {
    if (mode === "playground") {
      return (
        <div className="flex h-screen flex-col">
          {topBar}
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="hidden min-h-0 flex-1">
              <PlaygroundCockpit
                options={optionsQuery.data ?? null}
                onOpenRuns={openRunsList}
                onOpenHarborJob={openHarborJob}
                onOpenHarborTrial={openHarborTrial}
                onDomainChange={setPlaygroundDomain}
                onFooterContextChange={setPlaygroundFooter}
              />
            </div>
            <RunsView
              harborJobId={activeHarborJobId}
              harborTrialId={activeHarborTrialId}
              openHarborJob={openHarborJob}
              openHarborTrial={openHarborTrial}
              backToList={backToRunsList}
              backToHarborJob={backToHarborJob}
              onClose={closeRunsView}
              backLabel="Back to playground"
            />
          </div>
          <AppFooter context={shellFooterContext} />
        </div>
      );
    }

    return (
      <div className="flex h-screen flex-col">
        {topBar}
        <RunsView
          harborJobId={activeHarborJobId}
          harborTrialId={activeHarborTrialId}
          openHarborJob={openHarborJob}
          openHarborTrial={openHarborTrial}
          backToList={backToRunsList}
          backToHarborJob={backToHarborJob}
          onClose={closeRunsView}
          backLabel="Back to home"
        />
        <AppFooter context={shellFooterContext} />
      </div>
    );
  }

  if (mode === "home") {
    return (
      <div className="flex h-screen flex-col">
        {topBar}
        <HomeView onOpenPlayground={() => setMode("playground")} />
        <AppFooter context={shellFooterContext} />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      {topBar}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <PlaygroundCockpit
          options={optionsQuery.data ?? null}
          onOpenRuns={openRunsList}
          onOpenHarborJob={openHarborJob}
          onOpenHarborTrial={openHarborTrial}
          onDomainChange={setPlaygroundDomain}
          onFooterContextChange={setPlaygroundFooter}
        />
      </div>
      <AppFooter context={shellFooterContext} />
    </div>
  );
}
