/**
 * RIGHT inspector — the 1339-dimension review for the selected person.
 *
 * Joins the static dimension catalog (GET /api/dimensions, may 404) against the
 * person's attributed fields (a Map<field_id, ResultField> built from
 * result_preview). Renders a coverage headline, a 39-cell category heatmap, and
 * a per-category accordion of dimension rows.
 *
 * Kept linear: catalog dimensions are iterated once per category; field lookups
 * are O(1) Map gets — no O(n^2) scanning across 1339 rows.
 */
import { useMemo } from "react";

import { Sym, scoreBand, SCORE_BAND_CLASS, humanizeToken } from "@/components/cockpit/cockpitShared";
import { Bar, Chip, Empty, MetricTile, SectionLabel } from "@/components/cockpit/Primitives";
import type { ChipTone } from "@/components/cockpit/Primitives";
import { fmtInt, pct } from "@/lib/format";
import { ApiError } from "@/lib/api";
import type {
  CatalogCategory,
  CatalogDimension,
  DimensionCatalog,
  ResultField,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Assignment-type → tone mapping
// ---------------------------------------------------------------------------

function assignmentTone(type: string | null): ChipTone {
  switch (type) {
    case "direct":
      return "success";
    case "structured_claim":
      return "primary";
    case "summary_inference":
      return "warning";
    case "unsupported":
    default:
      return "neutral";
  }
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((v) => formatValue(v)).join(", ");
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

// ---------------------------------------------------------------------------
// Per-category coverage
// ---------------------------------------------------------------------------

interface CategoryCoverage {
  category: CatalogCategory;
  attributed: number;
}

function shortCategoryName(name: string): string {
  const human = humanizeToken(name);
  return human.length > 22 ? `${human.slice(0, 21)}…` : human;
}

// ---------------------------------------------------------------------------
// A single dimension row
// ---------------------------------------------------------------------------

function DimensionRow({ dim, field }: { dim: CatalogDimension; field: ResultField | undefined }) {
  const label = dim.label || humanizeToken(dim.id);

  if (!field) {
    return (
      <div className="flex items-center justify-between gap-sm border-b border-border-soft px-2 py-1.5 last:border-b-0">
        <span className="font-body-sm text-on-surface">{label}</span>
        <span className="font-body-sm italic text-outline">not yet attempted</span>
      </div>
    );
  }

  const type = typeof field.assignment_type === "string" ? field.assignment_type : null;
  const value = formatValue(field.value);

  return (
    <div className="flex flex-col gap-1 border-b border-border-soft px-2 py-2 last:border-b-0">
      <div className="flex items-start justify-between gap-sm">
        <span className="font-body-sm font-medium text-on-surface">{label}</span>
        {type ? (
          <Chip tone={assignmentTone(type)} title={field.plain_meaning || type}>
            {humanizeToken(type)}
          </Chip>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-sm">
        <span
          className="max-w-[60%] truncate rounded-md bg-surface-container-high px-2 py-0.5 font-mono-sm text-on-surface"
          title={value}
        >
          {value}
        </span>
        <Bar value={field.confidence} />
      </div>
      {field.evidence ? (
        <p
          className="line-clamp-2 font-body-sm italic text-on-surface-variant"
          title={field.evidence}
        >
          “{field.evidence}”
        </p>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// A category accordion
// ---------------------------------------------------------------------------

function CategorySection({
  cov,
  fields,
  defaultOpen,
}: {
  cov: CategoryCoverage;
  fields: Map<string, ResultField>;
  defaultOpen: boolean;
}) {
  const { category, attributed } = cov;
  return (
    <details
      open={defaultOpen}
      className="group/cat overflow-hidden rounded-lg border border-border-soft bg-surface-container-lowest"
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-sm px-3 py-2 hover:bg-surface-container-low">
        <span className="flex items-center gap-xs">
          <Sym
            name="chevron_right"
            size={18}
            className="text-outline transition-transform group-open/cat:rotate-90"
          />
          <span className="font-body-md text-on-surface">{humanizeToken(category.category)}</span>
        </span>
        <Chip tone={attributed > 0 ? "primary" : "neutral"} title="attributed / total">
          {attributed}/{category.count}
        </Chip>
      </summary>
      <div className="border-t border-border-soft">
        {category.dimensions.map((dim) => (
          <DimensionRow key={dim.id} dim={dim} field={fields.get(dim.id)} />
        ))}
      </div>
    </details>
  );
}

// ---------------------------------------------------------------------------
// Coverage heatmap cell
// ---------------------------------------------------------------------------

function HeatCell({ cov }: { cov: CategoryCoverage }) {
  const { category, attributed } = cov;
  const ratio = category.count > 0 ? attributed / category.count : 0;
  const band = attributed === 0 ? "none" : scoreBand(ratio);
  const cls = SCORE_BAND_CLASS[band];
  return (
    <div
      title={`${humanizeToken(category.category)} — ${attributed}/${category.count}`}
      className={`flex flex-col gap-0.5 rounded-md px-1.5 py-1 ${cls.soft}`}
    >
      <span className={`truncate font-label-md ${cls.text}`}>{shortCategoryName(category.category)}</span>
      <span className={`font-mono-sm tabular-nums ${cls.text}`}>
        {attributed}/{category.count}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

export function DimensionsPanel({
  catalog,
  catalogError,
  fields,
}: {
  catalog: DimensionCatalog | undefined;
  catalogError: unknown;
  fields: Map<string, ResultField>;
}) {
  const coverage = useMemo<CategoryCoverage[]>(() => {
    if (!catalog) return [];
    return catalog.categories.map((category) => {
      let attributed = 0;
      for (const dim of category.dimensions) {
        if (fields.has(dim.id)) attributed += 1;
      }
      return { category, attributed };
    });
  }, [catalog, fields]);

  const totalAttributed = useMemo(
    () => coverage.reduce((sum, c) => sum + c.attributed, 0),
    [coverage],
  );

  // Expand the first category that has any attribution (others collapsed).
  const firstAttributedKey = useMemo(
    () => coverage.find((c) => c.attributed > 0)?.category.slug ?? null,
    [coverage],
  );

  if (!catalog) {
    const status = catalogError instanceof ApiError ? `(${catalogError.status}) ` : "";
    return (
      <div className="p-md">
        <Empty
          icon="dataset"
          title="Dimension catalog unavailable"
          hint={`${status}GET /api/dimensions is not available on this backend — run the per-category protocols or update the backend to expose the 1339-dim catalog.`}
        />
      </div>
    );
  }

  const totalDims = catalog.total_dimensions;
  const coveragePct = Math.round(pct(totalAttributed, totalDims));

  return (
    <div className="flex flex-col gap-md p-md">
      {/* Coverage headline */}
      <div className="flex flex-col gap-sm">
        <SectionLabel>Dimension coverage</SectionLabel>
        <div className="grid grid-cols-2 gap-sm">
          <MetricTile
            label="Attributed"
            value={`${fmtInt(totalAttributed)} / ${fmtInt(totalDims)}`}
            hint={`${coveragePct}% of catalog`}
          />
          <MetricTile label="Categories" value={fmtInt(catalog.category_count)} hint="protocol groups" />
        </div>
      </div>

      {/* Category heatmap */}
      <div className="flex flex-col gap-sm">
        <SectionLabel>Category heatmap</SectionLabel>
        <div className="grid grid-cols-3 gap-1">
          {coverage.map((cov) => (
            <HeatCell key={cov.category.slug} cov={cov} />
          ))}
        </div>
      </div>

      {/* Per-category accordion */}
      <div className="flex flex-col gap-sm">
        <SectionLabel>Per-category review</SectionLabel>
        <div className="flex flex-col gap-1.5">
          {coverage.map((cov) => (
            <CategorySection
              key={cov.category.slug}
              cov={cov}
              fields={fields}
              defaultOpen={cov.category.slug === firstAttributedKey}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
