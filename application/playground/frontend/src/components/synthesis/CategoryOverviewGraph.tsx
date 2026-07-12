/**
 * Container-aware category overview of the Persona Full DAG.
 *
 * Categories retain their clockwise average-topological-order sequence on a
 * vertically relaxed ellipse. Node size encodes attribute count; aggregated
 * cross-category edges curve through the middle with width/opacity by edge
 * count. Always-on labels occupy collision-relaxed side columns connected by
 * leader lines, while color remains reserved for hover/selection.
 */
import { useLayoutEffect, useMemo, useRef, useState } from "react";

import type { SynthesisCategoryEdge, SynthesisOverviewResponse } from "@/lib/types";

const BASE_MIN_NODE_R = 7;
const BASE_MAX_NODE_R = 22;
const LABEL_MAX_CHARS = 20;
const LABEL_FONT_SIZE = 10.5;
const BASE_LABEL_CHAR_WIDTH = 5.7;
const MIN_LABEL_CHAR_WIDTH = 4.5;
const LABEL_ROW_GAP = 18;
const CANVAS_PADDING = 12;
const MIN_RING_X_RADIUS = 34;
const LABEL_LEADER_GAP = 7;
const LABEL_LINE_GAP = 4;
const MIN_HIT_R = 22;
const HIT_PADDING = 10;
const EDGE_NODE_GAP = 2;
const ARROW_SIZE = 8;
const EDGE_ARROW_ID = "synthesis-category-edge-arrow";
const ACTIVE_EDGE_ARROW_ID = "synthesis-category-edge-arrow-active";

interface Point {
  x: number;
  y: number;
}

type LabelSide = "left" | "right";

interface PlacedCategory {
  name: string;
  x: number;
  y: number;
  r: number;
  attributeCount: number;
  nodeCount: number;
  label: string;
  labelSide: LabelSide;
  labelX: number;
  labelY: number;
  labelWidth: number;
}

interface CanvasSize {
  width: number;
  height: number;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

function truncate(text: string): string {
  return text.length > LABEL_MAX_CHARS ? `${text.slice(0, LABEL_MAX_CHARS - 1)}…` : text;
}

function pointToward(from: Point, toward: Point, distance: number): Point {
  const dx = toward.x - from.x;
  const dy = toward.y - from.y;
  const length = Math.hypot(dx, dy);
  if (length === 0) return from;
  return {
    x: from.x + (dx / length) * distance,
    y: from.y + (dy / length) * distance,
  };
}

/** Approximate equal-arc-length positions so nodes do not bunch at ellipse ends. */
function evenlySpacedEllipseAngles(count: number, radiusX: number, radiusY: number): number[] {
  if (count === 0) return [];
  const startAngle = -Math.PI / 2;
  const sampleCount = Math.max(720, count * 32);
  const angles = new Array<number>(sampleCount + 1);
  const arcLengths = new Array<number>(sampleCount + 1);
  angles[0] = startAngle;
  arcLengths[0] = 0;
  let previous = { x: radiusX * Math.cos(startAngle), y: radiusY * Math.sin(startAngle) };
  for (let sample = 1; sample <= sampleCount; sample += 1) {
    const angle = startAngle + (sample / sampleCount) * Math.PI * 2;
    const point = { x: radiusX * Math.cos(angle), y: radiusY * Math.sin(angle) };
    angles[sample] = angle;
    arcLengths[sample] = arcLengths[sample - 1] + Math.hypot(
      point.x - previous.x,
      point.y - previous.y,
    );
    previous = point;
  }

  const perimeter = arcLengths[sampleCount];
  const result: number[] = [];
  let sample = 1;
  for (let index = 0; index < count; index += 1) {
    const target = (index / count) * perimeter;
    while (sample < sampleCount && arcLengths[sample] < target) sample += 1;
    const previousLength = arcLengths[sample - 1];
    const segmentLength = arcLengths[sample] - previousLength;
    const progress = segmentLength === 0 ? 0 : (target - previousLength) / segmentLength;
    result.push(angles[sample - 1] + (angles[sample] - angles[sample - 1]) * progress);
  }
  return result;
}

/** Preserve vertical order while enforcing a minimum label-to-label gap. */
function relaxLabelColumn(
  categories: PlacedCategory[],
  minimumY: number,
  maximumY: number,
): Map<string, number> {
  const ordered = [...categories].sort((left, right) => left.y - right.y);
  const positions = ordered.map((category) => clamp(category.y, minimumY, maximumY));
  for (let index = 1; index < positions.length; index += 1) {
    positions[index] = Math.max(positions[index], positions[index - 1] + LABEL_ROW_GAP);
  }
  if (positions.length > 0 && positions[positions.length - 1] > maximumY) {
    positions[positions.length - 1] = maximumY;
    for (let index = positions.length - 2; index >= 0; index -= 1) {
      positions[index] = Math.min(positions[index], positions[index + 1] - LABEL_ROW_GAP);
    }
  }
  if (positions.length > 0 && positions[0] < minimumY) {
    positions[0] = minimumY;
    for (let index = 1; index < positions.length; index += 1) {
      positions[index] = Math.max(positions[index], positions[index - 1] + LABEL_ROW_GAP);
    }
  }
  return new Map(ordered.map((category, index) => [category.name, positions[index]]));
}

export function CategoryOverviewGraph({
  overview,
  selectedCategory,
  onSelectCategory,
}: {
  overview: SynthesisOverviewResponse;
  selectedCategory: string | null;
  onSelectCategory: (name: string | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [canvasSize, setCanvasSize] = useState<CanvasSize | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [focused, setFocused] = useState<string | null>(null);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const updateSize = (width: number, height: number) => {
      const next = {
        width: Math.max(1, Math.round(width * 10) / 10),
        height: Math.max(1, Math.round(height * 10) / 10),
      };
      setCanvasSize((previous) =>
        previous?.width === next.width && previous.height === next.height ? previous : next,
      );
    };
    const rect = container.getBoundingClientRect();
    updateSize(rect.width, rect.height);
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) updateSize(entry.contentRect.width, entry.contentRect.height);
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const layout = useMemo(() => {
    if (!canvasSize) return null;
    const { width, height } = canvasSize;
    const categories = overview.categories;
    const center = { x: width / 2, y: height / 2 };
    const nodeScale = clamp(width / 620, 0.72, 1);
    const minimumNodeRadius = BASE_MIN_NODE_R * nodeScale;
    const maximumNodeRadius = BASE_MAX_NODE_R * nodeScale;
    const labelBudget =
      width / 2 -
      CANVAS_PADDING -
      MIN_RING_X_RADIUS -
      maximumNodeRadius -
      LABEL_LEADER_GAP;
    const labelCharWidth = clamp(
      labelBudget / LABEL_MAX_CHARS,
      MIN_LABEL_CHAR_WIDTH,
      BASE_LABEL_CHAR_WIDTH,
    );
    const maximumLabelWidth = LABEL_MAX_CHARS * labelCharWidth;
    const radiusX = Math.max(
      MIN_RING_X_RADIUS,
      width / 2 -
        CANVAS_PADDING -
        maximumLabelWidth -
        LABEL_LEADER_GAP -
        maximumNodeRadius,
    );
    const radiusY = Math.max(
      120,
      height / 2 - CANVAS_PADDING - maximumNodeRadius - LABEL_LEADER_GAP,
    );
    const maxAttr = Math.max(1, ...categories.map((category) => category.attributeCount));
    const angles = evenlySpacedEllipseAngles(categories.length, radiusX, radiusY);
    const placedCategories: PlacedCategory[] = categories.map((category, index) => {
      const angle = angles[index];
      const labelSide: LabelSide = index < Math.ceil(categories.length / 2) ? "right" : "left";
      const label = truncate(category.name);
      return {
        name: category.name,
        x: center.x + radiusX * Math.cos(angle),
        y: center.y + radiusY * Math.sin(angle),
        r:
          minimumNodeRadius +
          (maximumNodeRadius - minimumNodeRadius) *
            Math.sqrt(category.attributeCount / maxAttr),
        attributeCount: category.attributeCount,
        nodeCount: category.nodeCount,
        label,
        labelSide,
        labelX: labelSide === "left" ? CANVAS_PADDING : width - CANVAS_PADDING,
        labelY: 0,
        labelWidth: label.length * labelCharWidth,
      };
    });

    const minimumLabelY = CANVAS_PADDING + LABEL_FONT_SIZE;
    const maximumLabelY = height - CANVAS_PADDING - LABEL_FONT_SIZE;
    const leftLabels = relaxLabelColumn(
      placedCategories.filter((category) => category.labelSide === "left"),
      minimumLabelY,
      maximumLabelY,
    );
    const rightLabels = relaxLabelColumn(
      placedCategories.filter((category) => category.labelSide === "right"),
      minimumLabelY,
      maximumLabelY,
    );
    for (const category of placedCategories) {
      category.labelY =
        (category.labelSide === "left" ? leftLabels : rightLabels).get(category.name) ??
        category.y;
    }
    return {
      center,
      height,
      width,
      labelCharWidth,
      byName: new Map(placedCategories.map((category) => [category.name, category])),
    };
  }, [canvasSize, overview]);

  const maxEdgeCount = useMemo(
    () => Math.max(1, ...overview.edges.map((edge) => edge.count)),
    [overview],
  );
  const focus = hovered ?? focused ?? selectedCategory;

  if (!layout) {
    return (
      <div
        ref={containerRef}
        className="h-[70vh] min-h-[620px] max-h-[700px] w-full overflow-hidden"
        aria-busy="true"
      />
    );
  }
  const resolvedLayout = layout;

  function edgePath(edge: SynthesisCategoryEdge): string {
    const source = resolvedLayout.byName.get(edge.source);
    const target = resolvedLayout.byName.get(edge.target);
    if (!source || !target) return "";
    const midpoint = { x: (source.x + target.x) / 2, y: (source.y + target.y) / 2 };
    const control = {
      x: midpoint.x + (resolvedLayout.center.x - midpoint.x) * 0.45,
      y: midpoint.y + (resolvedLayout.center.y - midpoint.y) * 0.45,
    };
    const start = pointToward(source, control, source.r + EDGE_NODE_GAP);
    const end = pointToward(target, control, target.r + EDGE_NODE_GAP);
    return `M ${start.x} ${start.y} Q ${control.x} ${control.y} ${end.x} ${end.y}`;
  }

  function selectCategory(name: string, isSelected: boolean): void {
    onSelectCategory(isSelected ? null : name);
  }

  return (
    <div
      ref={containerRef}
      className="h-[70vh] min-h-[620px] max-h-[700px] w-full overflow-hidden"
    >
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        className="block h-full w-full"
        role="group"
        aria-label="Persona DAG category overview"
        onClick={() => onSelectCategory(null)}
      >
        <defs aria-hidden="true">
          <marker
            id={EDGE_ARROW_ID}
            viewBox={`0 0 ${ARROW_SIZE} ${ARROW_SIZE}`}
            markerWidth={ARROW_SIZE}
            markerHeight={ARROW_SIZE}
            refX={ARROW_SIZE}
            refY={ARROW_SIZE / 2}
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path
              d={`M 0 0 L ${ARROW_SIZE} ${ARROW_SIZE / 2} L 0 ${ARROW_SIZE} Z`}
              style={{ fill: "rgb(var(--outline))" }}
            />
          </marker>
          <marker
            id={ACTIVE_EDGE_ARROW_ID}
            viewBox={`0 0 ${ARROW_SIZE} ${ARROW_SIZE}`}
            markerWidth={ARROW_SIZE}
            markerHeight={ARROW_SIZE}
            refX={ARROW_SIZE}
            refY={ARROW_SIZE / 2}
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path
              d={`M 0 0 L ${ARROW_SIZE} ${ARROW_SIZE / 2} L 0 ${ARROW_SIZE} Z`}
              style={{ fill: "rgb(var(--primary))" }}
            />
          </marker>
        </defs>
        <g fill="none">
          {overview.edges.map((edge) => {
            const active = focus !== null && (edge.source === focus || edge.target === focus);
            const edgeStrength = Math.sqrt(edge.count / maxEdgeCount);
            const width = 0.8 + 2.4 * edgeStrength;
            const baselineOpacity = 0.12 + 0.36 * edgeStrength;
            const opacity =
              focus === null
                ? baselineOpacity
                : active
                  ? Math.min(0.92, 0.35 + baselineOpacity * 1.15)
                  : baselineOpacity * 0.18;
            return (
              <path
                key={`${edge.source}->${edge.target}`}
                d={edgePath(edge)}
                markerEnd={`url(#${active ? ACTIVE_EDGE_ARROW_ID : EDGE_ARROW_ID})`}
                style={{
                  stroke: active ? "rgb(var(--primary))" : "rgb(var(--outline))",
                  opacity,
                  strokeWidth: active ? width + 0.6 : width,
                  transition: "opacity 150ms ease-out",
                }}
              />
            );
          })}
        </g>
        {[...layout.byName.values()].map((category) => {
          const isFocus = focus === category.name;
          const isSelected = selectedCategory === category.name;
          const leaderEndX =
            category.labelSide === "left"
              ? category.labelX + category.labelWidth + LABEL_LINE_GAP
              : category.labelX - category.labelWidth - LABEL_LINE_GAP;
          const leaderEnd = { x: leaderEndX, y: category.labelY };
          const leaderStart = pointToward(
            category,
            leaderEnd,
            category.r + EDGE_NODE_GAP,
          );
          const leaderControlX = (leaderStart.x + leaderEnd.x) / 2;
          const accessibleLabel = `${category.name} — ${category.attributeCount} attributes / ${category.nodeCount} nodes`;
          return (
            <g
              key={category.name}
              className="cursor-pointer"
              role="button"
              tabIndex={0}
              aria-label={accessibleLabel}
              aria-pressed={isSelected}
              onPointerEnter={() => setHovered(category.name)}
              onPointerLeave={() => setHovered(null)}
              onFocus={() => setFocused(category.name)}
              onBlur={() => setFocused(null)}
              onClick={(event) => {
                event.stopPropagation();
                selectCategory(category.name, isSelected);
              }}
              onKeyDown={(event) => {
                if (event.key !== "Enter" && event.key !== " ") return;
                event.preventDefault();
                event.stopPropagation();
                selectCategory(category.name, isSelected);
              }}
            >
              <title>{accessibleLabel}</title>
              <path
                d={`M ${leaderStart.x} ${leaderStart.y} Q ${leaderControlX} ${category.labelY} ${leaderEnd.x} ${leaderEnd.y}`}
                fill="none"
                pointerEvents="none"
                style={{
                  stroke: isFocus || isSelected ? "rgb(var(--primary))" : "rgb(var(--outline))",
                  strokeOpacity: isFocus || isSelected ? 0.75 : 0.42,
                  strokeWidth: isFocus || isSelected ? 1.2 : 0.8,
                  transition: "stroke 150ms ease-out, stroke-opacity 150ms ease-out",
                }}
              />
              <circle
                cx={category.x}
                cy={category.y}
                r={Math.max(MIN_HIT_R, category.r + HIT_PADDING)}
                fill="transparent"
              />
              <circle
                cx={category.x}
                cy={category.y}
                r={category.r}
                style={{
                  fill: isFocus
                    ? "rgb(var(--primary) / 0.18)"
                    : "rgb(var(--surface-high))",
                  stroke:
                    isFocus || isSelected ? "rgb(var(--primary))" : "rgb(var(--outline))",
                  strokeWidth: isSelected ? 2 : 1.2,
                  transition: "fill 150ms ease-out, stroke 150ms ease-out",
                }}
              />
              <text
                x={category.labelX}
                y={category.labelY}
                textAnchor={category.labelSide === "left" ? "start" : "end"}
                dominantBaseline="middle"
                className="font-mono"
                textLength={category.label.length * layout.labelCharWidth}
                lengthAdjust="spacingAndGlyphs"
                style={{
                  fontSize: LABEL_FONT_SIZE,
                  fill:
                    isFocus || isSelected
                      ? "rgb(var(--text-main))"
                      : "rgb(var(--text-dim))",
                }}
              >
                {category.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
