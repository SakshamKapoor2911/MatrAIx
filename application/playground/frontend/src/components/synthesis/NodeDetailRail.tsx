/**
 * Detail rail for one graph node: values with prior bars, and the
 * strongest incoming/outgoing edges (click to jump).
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SynthesisNodeDetail, SynthesisNodeEdgeView } from "@/lib/types";
import { FOCUS_RING } from "../cockpit/cockpitShared";

function EdgeList({
  title,
  edges,
  onJumpToNode,
}: {
  title: string;
  edges: SynthesisNodeEdgeView[];
  onJumpToNode: (id: string) => void;
}) {
  if (edges.length === 0) return null;
  return (
    <div>
      <div className="hud mb-1 text-text-dim">{title}</div>
      <ul className="space-y-0.5">
        {edges.map((edge) => (
          <li key={edge.id}>
            <button
              type="button"
              onClick={() => onJumpToNode(edge.id)}
              className={`flex w-full items-baseline justify-between gap-2 rounded px-2 py-1 text-left transition-colors hover:bg-surface-low motion-reduce:transition-none ${FOCUS_RING}`}
            >
              <span className="min-w-0 truncate text-xs text-text-variant">{edge.label}</span>
              <span className="flex-none font-mono text-[10px] text-text-dim">
                w {edge.weight}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function NodeDetailRail({
  nodeId,
  onJumpToNode,
}: {
  nodeId: string;
  onJumpToNode: (id: string) => void;
}) {
  const detailQuery = useQuery<SynthesisNodeDetail>({
    queryKey: ["synthesis", "node", nodeId],
    queryFn: () => api.getSynthesisNode(nodeId),
    staleTime: Infinity,
  });
  const detail = detailQuery.data ?? null;

  if (detailQuery.isError) {
    return (
      <div role="alert" className="grid h-full place-items-center text-sm text-danger">
        Failed to load node detail.
      </div>
    );
  }
  if (!detail) {
    return (
      <div role="status" className="grid h-full place-items-center text-sm text-text-dim">
        Loading…
      </div>
    );
  }

  const maxPrior = Math.max(0.0001, ...detail.prior);
  return (
    <div className="custom-scrollbar flex h-full min-h-0 flex-col gap-4 overflow-y-auto p-4">
      <div>
        <div className="hud text-text-dim">{detail.type}</div>
        <h3 className="font-display text-base text-text-main">{detail.label}</h3>
        <p className="font-mono text-[11px] text-text-dim">{detail.id}</p>
        <p className="mt-1 text-xs text-text-dim">
          {detail.category} · in {detail.inDegree} / out {detail.outDegree}
        </p>
        {detail.description ? (
          <p className="mt-2 text-xs leading-relaxed text-text-variant">{detail.description}</p>
        ) : null}
      </div>
      {detail.values.length > 0 ? (
        <div>
          <div className="hud mb-1 text-text-dim">Base prior</div>
          <ul className="space-y-1">
            {detail.values.map((value, index) => {
              const prior = detail.prior[index] ?? 0;
              return (
                <li key={value} className="flex items-center gap-2">
                  <span className="w-28 flex-none truncate text-xs text-text-variant" title={value}>
                    {value}
                  </span>
                  <span className="h-2 min-w-0 flex-1 rounded-sm bg-surface-high" aria-hidden="true">
                    <span
                      className="block h-full rounded-sm"
                      style={{
                        width: `${Math.round((prior / maxPrior) * 100)}%`,
                        background: "rgb(var(--primary) / 0.55)",
                      }}
                    />
                  </span>
                  <span className="w-12 flex-none text-right font-mono text-[10px] text-text-dim">
                    {(prior * 100).toFixed(1)}%
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
      <EdgeList title="Strongest incoming" edges={detail.inEdges} onJumpToNode={onJumpToNode} />
      <EdgeList title="Strongest outgoing" edges={detail.outEdges} onJumpToNode={onJumpToNode} />
    </div>
  );
}
