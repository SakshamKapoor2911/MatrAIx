/**
 * Synthesis Studio: read-only browsing of the Persona Full DAG.
 *
 * Three panes: category overview graph → drill-down subgraph → detail rail.
 * Phase 1 of docs/superpowers/specs/2026-07-11-persona-dag-studio-design.md.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SynthesisOverviewResponse, SynthesisSubgraphResponse } from "@/lib/types";
import { CategoryAttributeList } from "./CategoryAttributeList";
import { CategoryOverviewGraph } from "./CategoryOverviewGraph";
import { DrilldownGraph } from "./DrilldownGraph";
import { NodeDetailRail } from "./NodeDetailRail";
import { FOCUS_RING } from "../cockpit/cockpitShared";
import {
  StudioGlassPanel,
  StudioMeshShell,
  StudioPageFrame,
  StudioPageHeader,
} from "../studio/StudioShell";

export function SynthesisStudioView() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [centerNode, setCenterNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hops, setHops] = useState<{ up: number; down: number }>({ up: 1, down: 1 });
  const overviewQuery = useQuery<SynthesisOverviewResponse>({
    queryKey: ["synthesis", "overview"],
    queryFn: api.getSynthesisOverview,
    staleTime: Infinity,
  });
  const subgraphQuery = useQuery<SynthesisSubgraphResponse>({
    queryKey: ["synthesis", "subgraph", centerNode, hops.up, hops.down],
    queryFn: () => api.getSynthesisSubgraph(centerNode as string, hops.up, hops.down),
    enabled: centerNode !== null,
    staleTime: Infinity,
  });
  const overview = overviewQuery.data ?? null;
  const selectedCategoryData =
    overview?.categories.find((cat) => cat.name === selectedCategory) ?? null;

  return (
    <StudioMeshShell>
      <StudioPageFrame>
        <StudioPageHeader
          eyebrow="MatrAIx · Synthesis"
          title="Persona DAG Studio"
          subtitle={
            overview
              ? `${overview.counts.graphNodes.toLocaleString()} nodes · ${overview.counts.directedEdges.toLocaleString()} directed edges · ${overview.counts.categories} categories`
              : "Loading the Persona Full DAG…"
          }
        />
        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)_minmax(0,3fr)]">
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            {overview ? (
              <CategoryOverviewGraph
                overview={overview}
                selectedCategory={selectedCategory}
                onSelectCategory={(name) => {
                  setSelectedCategory(name);
                  setSelectedNode(null);
                }}
              />
            ) : (
              <div className="grid h-full place-items-center text-sm text-text-dim">
                {overviewQuery.isError ? "Failed to load the graph overview." : "Loading…"}
              </div>
            )}
          </StudioGlassPanel>
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            {centerNode === null ? (
              <div className="grid h-full place-items-center px-6 text-center text-sm text-text-dim">
                Pick a category, then an attribute, to see its dependency neighborhood.
              </div>
            ) : (
              <div className="flex h-full min-h-0 flex-col">
                <div className="flex flex-none items-center gap-3 border-b border-outline-dim px-3 py-2">
                  <span className="hud text-text-dim">Hops</span>
                  {(["up", "down"] as const).map((direction) => (
                    <label
                      key={direction}
                      className="flex items-center gap-1.5 text-xs text-text-variant"
                    >
                      {direction}
                      <select
                        value={hops[direction]}
                        onChange={(event) =>
                          setHops((previous) => ({
                            ...previous,
                            [direction]: Number(event.target.value),
                          }))
                        }
                        className={`h-7 rounded border border-outline bg-field px-1.5 text-xs text-text-main ${FOCUS_RING}`}
                      >
                        {[0, 1, 2, 3, 4].map((hopCount) => (
                          <option key={hopCount} value={hopCount}>
                            {hopCount}
                          </option>
                        ))}
                      </select>
                    </label>
                  ))}
                  {subgraphQuery.data?.truncated ? (
                    <span className="text-[11px] text-warn">
                      truncated to nearest 60/direction
                    </span>
                  ) : null}
                </div>
                <div className="min-h-0 flex-1">
                  {subgraphQuery.data ? (
                    <DrilldownGraph
                      subgraph={subgraphQuery.data}
                      selectedNode={selectedNode}
                      onSelectNode={setSelectedNode}
                      onRecenter={(id) => {
                        setCenterNode(id);
                        setSelectedNode(id);
                      }}
                    />
                  ) : (
                    <div className="grid h-full place-items-center text-sm text-text-dim">
                      {subgraphQuery.isError ? "Failed to load subgraph." : "Loading…"}
                    </div>
                  )}
                </div>
              </div>
            )}
          </StudioGlassPanel>
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            {selectedNode ? (
              <div className="flex h-full min-h-0 flex-col">
                <button
                  type="button"
                  onClick={() => setSelectedNode(null)}
                  className={`flex-none px-4 pt-3 text-left text-[11px] text-text-dim transition-colors hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
                >
                  ← back to category list
                </button>
                <div className="min-h-0 flex-1">
                  <NodeDetailRail
                    nodeId={selectedNode}
                    onJumpToNode={(id) => {
                      setCenterNode(id);
                      setSelectedNode(id);
                    }}
                  />
                </div>
              </div>
            ) : selectedCategoryData ? (
              <CategoryAttributeList
                key={selectedCategoryData.name}
                category={selectedCategoryData}
                onSelectAttribute={(id) => {
                  setCenterNode(id);
                  setSelectedNode(id);
                }}
              />
            ) : (
              <div className="grid h-full place-items-center px-6 text-center text-sm text-text-dim">
                Click a category to list its attributes.
              </div>
            )}
          </StudioGlassPanel>
        </div>
      </StudioPageFrame>
    </StudioMeshShell>
  );
}

export default SynthesisStudioView;
