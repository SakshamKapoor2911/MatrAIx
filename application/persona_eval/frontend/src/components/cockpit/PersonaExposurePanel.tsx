/**
 * PersonaExposurePanel: generic structured fields visible on an app turn.
 *
 * Renders task-configured ``personaExposure`` entries (item lists, text, JSON).
 * The platform does not hard-code recommender semantics; tasks declare fields in
 * ``input/chatbot.yaml``.
 */
import type { PersonaExposureField } from "@/lib/types";

export interface ExposureItem {
  itemId: string;
  rank?: number | null;
  title?: string | null;
  meta?: string | null;
  score?: number | null;
}

function exposureItems(field: PersonaExposureField): ExposureItem[] {
  if (field.format !== "item_list" || !Array.isArray(field.value)) return [];
  return field.value.flatMap((raw, index) => {
    if (!raw || typeof raw !== "object") return [];
    const record = raw as Record<string, unknown>;
    const itemId = String(record.itemId ?? record.id ?? "").trim();
    if (!itemId) return [];
    return [
      {
        itemId,
        title: typeof record.title === "string" ? record.title : null,
        rank: typeof record.rank === "number" ? record.rank : index + 1,
        meta: typeof record.meta === "string" ? record.meta : null,
        score: typeof record.score === "number" ? record.score : null,
      },
    ];
  });
}

function formatValue(field: PersonaExposureField): string {
  const value = field.value;
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function ItemListField({ field }: { field: PersonaExposureField }) {
  const items = exposureItems(field);
  if (items.length === 0) return null;
  const label = field.label ?? field.key ?? "Details";
  return (
    <div>
      <div className="hud mb-2 text-[9px] text-text-dim">{label}</div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {items.map((item) => {
          const title = item.title ?? item.itemId;
          const isFirst = item.rank === 1;
          return (
            <div
              key={`${item.itemId}-${item.rank}`}
              className="relative rounded border border-outline bg-surface-low p-3 transition-colors hover:border-primary/60"
            >
              {isFirst && (
                <div className="hud absolute right-0 top-0 rounded-bl border-b border-l border-secondary/25 bg-secondary/10 px-1 py-0.5 text-[7px] text-secondary">
                  Top
                </div>
              )}
              <div className="mb-1 flex items-start gap-2">
                <span className="shrink-0 font-mono text-[10px] font-bold text-primary">
                  {String(item.rank ?? 1).padStart(2, "0")}
                </span>
                <span
                  className={`min-w-0 break-words text-[12px] font-semibold text-text-main ${isFirst ? "pr-12" : ""}`}
                  title={title}
                >
                  {title}
                </span>
              </div>
              {item.meta && <p className="text-[11px] leading-snug text-text-variant">{item.meta}</p>}
              {item.title && (
                <p className="mt-1 truncate font-mono text-[10px] text-text-dim" title={item.itemId}>
                  {item.itemId}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TextField({ field }: { field: PersonaExposureField }) {
  const text = formatValue(field).trim();
  if (!text) return null;
  const label = field.label ?? field.key ?? "Details";
  return (
    <div>
      <div className="hud mb-2 text-[9px] text-text-dim">{label}</div>
      <pre className="overflow-x-auto rounded border border-outline bg-surface-low p-3 text-[11px] leading-relaxed text-text-variant whitespace-pre-wrap">
        {text}
      </pre>
    </div>
  );
}

export function exposureItemLists(exposure: PersonaExposureField[] | undefined): ExposureItem[] {
  const items: ExposureItem[] = [];
  for (const field of exposure ?? []) {
    items.push(...exposureItems(field));
  }
  return items;
}

export interface PersonaExposurePanelProps {
  exposure: PersonaExposureField[];
}

export function PersonaExposurePanel({ exposure }: PersonaExposurePanelProps) {
  if (!exposure.length) return null;
  return (
    <div className="space-y-4">
      {exposure.map((field, index) => {
        const key = field.key ?? field.label ?? String(index);
        if (field.format === "item_list") {
          return <ItemListField key={key} field={field} />;
        }
        return <TextField key={key} field={field} />;
      })}
    </div>
  );
}

export default PersonaExposurePanel;
