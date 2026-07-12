/**
 * Layered drill-down subgraph: columns are center-relative longest-path
 * topological ranks (upstream left of the center node, downstream right), so
 * proposal direction always reads left-to-right. Nodes are labeled boxes;
 * edges are cubic curves with arrowheads. Click selects, double-click
 * re-centers.
 */
import { useId, useMemo, useState } from "react";

import type { SynthesisSubgraphResponse } from "@/lib/types";

const COL_WIDTH = 230;
const NODE_W = 176;
const NODE_H = 40;
const ROW_GAP = 14;
const PADDING = 24;
const LABEL_MAX_CHARS = 24;
const HIT_HEIGHT = 44;

function truncate(text: string): string {
  return text.length > LABEL_MAX_CHARS ? `${text.slice(0, LABEL_MAX_CHARS - 1)}…` : text;
}

export function DrilldownGraph({
  subgraph,
  selectedNode,
  onSelectNode,
  onRecenter,
}: {
  subgraph: SynthesisSubgraphResponse;
  selectedNode: string | null;
  onSelectNode: (id: string) => void;
  onRecenter: (id: string) => void;
}) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [focused, setFocused] = useState<string | null>(null);
  const markerScope = useId().replace(/:/g, "");
  const edgeArrowId = `synthesis-drilldown-${markerScope}-arrow`;
  const activeEdgeArrowId = `${edgeArrowId}-active`;

  const layout = useMemo(() => {
    const nodeById = new Map(subgraph.nodes.map((node) => [node.id, node]));
    const originalOrder = new Map(subgraph.nodes.map((node, index) => [node.id, index]));
    // The service payload order is stable (signed layer, topological order,
    // then id), so retain it whenever Kahn's algorithm has multiple choices.
    const compareNodeIds = (left: string, right: string): number => {
      const orderDifference =
        (originalOrder.get(left) ?? Number.MAX_SAFE_INTEGER) -
        (originalOrder.get(right) ?? Number.MAX_SAFE_INTEGER);
      if (orderDifference !== 0) return orderDifference;
      const layerDifference =
        (nodeById.get(left)?.layer ?? 0) - (nodeById.get(right)?.layer ?? 0);
      if (layerDifference !== 0) return layerDifference;
      return left.localeCompare(right);
    };

    const outgoing = new Map<string, string[]>(
      subgraph.nodes.map((node) => [node.id, []]),
    );
    const inDegree = new Map<string, number>(
      subgraph.nodes.map((node) => [node.id, 0]),
    );
    for (const edge of subgraph.edges) {
      if (!nodeById.has(edge.source) || !nodeById.has(edge.target)) continue;
      outgoing.get(edge.source)?.push(edge.target);
      inDegree.set(edge.target, (inDegree.get(edge.target) ?? 0) + 1);
    }
    for (const targets of outgoing.values()) targets.sort(compareNodeIds);

    const ready = subgraph.nodes
      .filter((node) => inDegree.get(node.id) === 0)
      .map((node) => node.id)
      .sort(compareNodeIds);
    const topologicalOrder: string[] = [];
    const rankById = new Map(subgraph.nodes.map((node) => [node.id, 0]));
    while (ready.length > 0) {
      const source = ready.shift();
      if (!source) break;
      topologicalOrder.push(source);
      const sourceRank = rankById.get(source) ?? 0;
      for (const target of outgoing.get(source) ?? []) {
        rankById.set(target, Math.max(rankById.get(target) ?? 0, sourceRank + 1));
        const remaining = (inDegree.get(target) ?? 0) - 1;
        inDegree.set(target, remaining);
        if (remaining !== 0) continue;
        const insertionIndex = ready.findIndex(
          (readyNode) => compareNodeIds(target, readyNode) < 0,
        );
        if (insertionIndex === -1) ready.push(target);
        else ready.splice(insertionIndex, 0, target);
      }
    }

    if (topologicalOrder.length !== subgraph.nodes.length) {
      return {
        positions: new Map<string, { x: number; y: number }>(),
        width: PADDING * 2 + NODE_W,
        height: PADDING * 2 + NODE_H,
        cycleDetected: true,
      };
    }

    const centerRank = rankById.get(subgraph.center) ?? 0;
    const layers = new Map<number, string[]>();
    for (const nodeId of topologicalOrder) {
      const centeredRank = (rankById.get(nodeId) ?? 0) - centerRank;
      const bucket = layers.get(centeredRank) ?? [];
      bucket.push(nodeId);
      layers.set(centeredRank, bucket);
    }
    const layerKeys = [...layers.keys()].sort((a, b) => a - b);
    const minLayer = layerKeys[0] ?? 0;
    const maxLayer = layerKeys[layerKeys.length - 1] ?? minLayer;
    const positions = new Map<string, { x: number; y: number }>();
    let maxRows = 1;
    for (const layer of layerKeys) {
      const ids = layers.get(layer) ?? [];
      maxRows = Math.max(maxRows, ids.length);
      ids.forEach((id, row) => {
        positions.set(id, {
          x: PADDING + (layer - minLayer) * COL_WIDTH,
          y: PADDING + row * (NODE_H + ROW_GAP),
        });
      });
    }
    return {
      positions,
      width: PADDING * 2 + Math.max(0, maxLayer - minLayer) * COL_WIDTH + NODE_W,
      height: PADDING * 2 + maxRows * (NODE_H + ROW_GAP) - ROW_GAP,
      cycleDetected: false,
    };
  }, [subgraph.center, subgraph.edges, subgraph.nodes]);

  const nodesById = useMemo(
    () => new Map(subgraph.nodes.map((node) => [node.id, node])),
    [subgraph.nodes],
  );
  const focus = focused ?? hovered ?? selectedNode;
  const neighborIds = useMemo(() => {
    if (!focus) return new Set<string>();
    const ids = new Set<string>([focus]);
    for (const edge of subgraph.edges) {
      if (edge.source === focus) ids.add(edge.target);
      if (edge.target === focus) ids.add(edge.source);
    }
    return ids;
  }, [focus, subgraph.edges]);

  if (layout.cycleDetected) {
    return (
      <div
        role="alert"
        className="grid h-full place-items-center px-6 text-center text-sm text-danger"
      >
        Unable to render a left-to-right layout because this subgraph contains a cycle.
      </div>
    );
  }

  return (
    <div className="custom-scrollbar h-full w-full overflow-auto">
      <svg
        width={layout.width}
        height={layout.height}
        className="block max-w-none"
        role="group"
        aria-label={`Dependency subgraph around ${subgraph.center}`}
      >
        <title>{`Dependency subgraph around ${subgraph.center}`}</title>
        <desc>
          Select a node with click, Enter, or Space. Double-click or press Shift+Enter to
          recenter the graph.
        </desc>
        <defs aria-hidden="true">
          <marker
            id={edgeArrowId}
            viewBox="0 0 8 8"
            refX="7"
            refY="4"
            markerWidth="7"
            markerHeight="7"
            markerUnits="userSpaceOnUse"
            orient="auto"
          >
            <path d="M 0 0 L 8 4 L 0 8 z" style={{ fill: "rgb(var(--outline))" }} />
          </marker>
          <marker
            id={activeEdgeArrowId}
            viewBox="0 0 8 8"
            refX="7"
            refY="4"
            markerWidth="7"
            markerHeight="7"
            markerUnits="userSpaceOnUse"
            orient="auto"
          >
            <path d="M 0 0 L 8 4 L 0 8 z" style={{ fill: "rgb(var(--primary))" }} />
          </marker>
        </defs>
        <g fill="none">
          {subgraph.edges.map((edge) => {
            const sourcePosition = layout.positions.get(edge.source);
            const targetPosition = layout.positions.get(edge.target);
            if (!sourcePosition || !targetPosition) return null;
            const x1 = sourcePosition.x + NODE_W;
            const y1 = sourcePosition.y + NODE_H / 2;
            const x2 = targetPosition.x;
            const y2 = targetPosition.y + NODE_H / 2;
            const midX = (x1 + x2) / 2;
            const active =
              focus !== null && (edge.source === focus || edge.target === focus);
            const sourceLabel = nodesById.get(edge.source)?.label ?? edge.source;
            const targetLabel = nodesById.get(edge.target)?.label ?? edge.target;
            return (
              <path
                key={`${edge.source}->${edge.target}:${edge.relation}`}
                d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                markerEnd={`url(#${active ? activeEdgeArrowId : edgeArrowId})`}
                style={{
                  stroke: active ? "rgb(var(--primary))" : "rgb(var(--outline))",
                  strokeOpacity: focus === null ? 0.55 : active ? 0.95 : 0.18,
                  strokeWidth: active ? 1.8 : 1.1,
                }}
              >
                <title>{`${sourceLabel} → ${targetLabel} (${edge.relation}, w=${edge.weight})`}</title>
              </path>
            );
          })}
        </g>
        {subgraph.nodes.map((node) => {
          const position = layout.positions.get(node.id);
          if (!position) return null;
          const isCenter = node.id === subgraph.center;
          const isSelected = node.id === selectedNode;
          const isFocus = node.id === focus;
          const dimmed = focus !== null && !neighborIds.has(node.id);
          const accessibleLabel = `${node.label} (${node.category}) — in ${node.inDegree} / out ${node.outDegree}${node.emit ? "" : " · latent/helper"}${isCenter ? " · current center" : ""}. Double-click or press Shift+Enter to recenter.`;
          return (
            <g
              key={node.id}
              className="cursor-pointer transition-opacity duration-150 motion-reduce:transition-none"
              role="button"
              tabIndex={0}
              aria-label={accessibleLabel}
              aria-pressed={isSelected}
              aria-current={isCenter ? "true" : undefined}
              opacity={dimmed ? 0.35 : 1}
              onPointerEnter={() => setHovered(node.id)}
              onPointerLeave={() => setHovered(null)}
              onFocus={() => setFocused(node.id)}
              onBlur={() => setFocused(null)}
              onClick={() => onSelectNode(node.id)}
              onDoubleClick={() => onRecenter(node.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && event.shiftKey) {
                  event.preventDefault();
                  onRecenter(node.id);
                  return;
                }
                if (event.key !== "Enter" && event.key !== " ") return;
                event.preventDefault();
                onSelectNode(node.id);
              }}
            >
              <title>{accessibleLabel}</title>
              <rect
                x={position.x - 2}
                y={position.y - (HIT_HEIGHT - NODE_H) / 2}
                width={NODE_W + 4}
                height={HIT_HEIGHT}
                rx={10}
                fill="transparent"
              />
              <rect
                x={position.x}
                y={position.y}
                width={NODE_W}
                height={NODE_H}
                rx={8}
                className="transition-colors duration-150 motion-reduce:transition-none"
                style={{
                  fill:
                    isCenter || isFocus
                      ? "rgb(var(--primary) / 0.14)"
                      : "rgb(var(--surface-high))",
                  stroke:
                    isSelected || isCenter || isFocus
                      ? "rgb(var(--primary))"
                      : "rgb(var(--outline))",
                  strokeWidth: isSelected ? 2 : isCenter || isFocus ? 1.6 : 1.2,
                  strokeDasharray: node.emit ? undefined : "4 3",
                }}
              />
              <text
                x={position.x + 10}
                y={position.y + 17}
                style={{ fontSize: 11.5, fill: "rgb(var(--text-main))" }}
              >
                {truncate(node.label)}
              </text>
              <text
                x={position.x + 10}
                y={position.y + 31}
                className="font-mono"
                style={{ fontSize: 9.5, fill: "rgb(var(--text-dim))" }}
              >
                {truncate(node.id)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
