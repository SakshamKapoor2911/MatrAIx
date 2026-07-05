import { useEffect, useState } from "react";

import type { WebTrace, WebTraceEvent } from "@/lib/types";

import { FOCUS_RING, Sym } from "./cockpitShared";

function summarizeAction(event: WebTraceEvent): string | null {
  const action = event.actions[0];
  if (!action?.name) return null;
  const name = action.name.toLowerCase();
  const args = action.arguments ?? {};
  let target: string | null = null;
  for (const value of Object.values(args)) {
    if (typeof value === "string" && value.trim()) {
      target = value.trim();
      break;
    }
  }
  const clip = (text: string) => (text.length > 28 ? `${text.slice(0, 27)}…` : text);
  if (name.includes("click")) return target ? `clicked ${clip(target)}` : "clicked";
  if (name.includes("type") || name.includes("fill") || name.includes("input")) {
    return target ? `typed “${clip(target)}”` : "typed";
  }
  if (name.includes("nav") || name.includes("goto") || name.includes("visit") || name.includes("open")) {
    return target ? `went to ${clip(target)}` : "navigated";
  }
  if (name.includes("launch") || name.includes("swipe") || name.includes("tap")) {
    return target ? `${name} ${clip(target)}` : name.replace(/_/g, " ");
  }
  if (name.includes("search")) return target ? `searched ${clip(target)}` : "searched";
  if (name.includes("select")) return "selected an option";
  if (name.includes("submit")) return "submitted the form";
  if (name.includes("scroll")) return "scrolled";
  if (name.includes("back")) return "went back";
  return name.replace(/_/g, " ");
}

function actionSignature(event: WebTraceEvent): string {
  const action = event.actions[0];
  if (action?.name) {
    const args = action.arguments ?? {};
    let arg = "";
    for (const value of Object.values(args)) {
      if (typeof value === "string" && value.trim()) {
        arg = value.trim();
        break;
      }
    }
    if (arg.length > 22) arg = `${arg.slice(0, 21)}…`;
    return `${action.name}(${arg})`;
  }
  const message = (event.message ?? "").trim();
  return message.length > 28 ? `${message.slice(0, 27)}…` : message;
}

export interface HarborTraceReplayProps {
  trace: WebTrace;
  autoFollowLatest?: boolean;
  emptyMessage?: string;
}

/** Screenshot scrubber + tile grid for Harbor web/CUA trajectories. */
export function HarborTraceReplay({
  trace,
  autoFollowLatest = false,
  emptyMessage = "This run finished without recording any steps.",
}: HarborTraceReplayProps) {
  const [scrubIndex, setScrubIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [lightboxStep, setLightboxStep] = useState<number | null>(null);
  const events = trace.events;

  useEffect(() => {
    if (!autoFollowLatest || isPlaying) return;
    setScrubIndex(Math.max(0, events.length - 1));
  }, [autoFollowLatest, events.length, isPlaying]);

  useEffect(() => {
    if (!isPlaying) return;
    const id = window.setInterval(() => {
      setScrubIndex((prev) => {
        if (prev >= events.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        const next = prev + 1;
        if (next >= events.length - 1) setIsPlaying(false);
        return next;
      });
    }, 1200);
    return () => window.clearInterval(id);
  }, [isPlaying, events.length]);

  useEffect(() => {
    setScrubIndex((prev) => Math.min(prev, Math.max(0, events.length - 1)));
  }, [events.length]);

  if (events.length === 0) {
    return (
      <div className="rise-in rounded-md border border-dashed border-outline bg-surface-low px-4 py-6 text-center text-[12px] text-text-variant">
        {emptyMessage}
      </div>
    );
  }

  const previewEvent = events[Math.min(scrubIndex, events.length - 1)];
  const activeStep = previewEvent.step;
  const lightboxEvent = lightboxStep != null ? events.find((event) => event.step === lightboxStep) ?? null : null;

  return (
    <div className="space-y-3">
      <TraceHeroScreenshot
        event={previewEvent}
        onOpenImage={() => setLightboxStep(previewEvent.step)}
      />

      <div className="flex flex-wrap items-center gap-3 rounded-md border border-outline/50 bg-surface-low px-3 py-2">
        <button
          type="button"
          onClick={() => {
            if (isPlaying) {
              setIsPlaying(false);
              return;
            }
            if (scrubIndex >= events.length - 1) {
              setScrubIndex(0);
            }
            setIsPlaying(true);
          }}
          aria-label={isPlaying ? "Pause trace replay" : "Play trace replay"}
          className={`grid h-8 w-8 place-items-center rounded-full border border-outline/60 text-primary transition hover:border-primary/50 active:scale-95 ${FOCUS_RING}`}
        >
          <Sym name={isPlaying ? "pause_circle" : "play_circle"} size={18} />
        </button>
        <input
          type="range"
          min={0}
          max={Math.max(0, events.length - 1)}
          value={scrubIndex}
          onChange={(e) => {
            setIsPlaying(false);
            setScrubIndex(Number(e.target.value));
          }}
          className="min-w-[120px] flex-1 accent-primary"
        />
        <span className="font-mono text-[10px] text-text-dim">
          Step {previewEvent.step} / {events.length}
        </span>
      </div>

      <TraceStepDetail key={previewEvent.step} event={previewEvent} />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {events.map((event, index) => (
          <TraceTile
            key={event.step}
            index={index}
            event={event}
            active={event.step === activeStep}
            onClick={() => {
              setIsPlaying(false);
              setScrubIndex(index);
            }}
          />
        ))}
      </div>

      {lightboxEvent?.screenshotUrl && (
        <TraceImageLightbox event={lightboxEvent} onClose={() => setLightboxStep(null)} />
      )}
    </div>
  );
}

function TraceHeroScreenshot({
  event,
  onOpenImage,
}: {
  event: WebTraceEvent;
  onOpenImage: () => void;
}) {
  const [imgError, setImgError] = useState(false);
  const showImage = Boolean(event.screenshotUrl) && !imgError;

  useEffect(() => {
    setImgError(false);
  }, [event.step, event.screenshotUrl]);

  return (
    <div className="overflow-hidden rounded-md border border-outline bg-surface-low">
      {showImage ? (
        <button
          type="button"
          onClick={onOpenImage}
          className={`block w-full cursor-zoom-in ${FOCUS_RING}`}
          aria-label={`Open full-size screenshot for step ${event.step}`}
        >
          <img
            src={event.screenshotUrl as string}
            alt={`Step ${event.step}`}
            className="max-h-[360px] w-full bg-surface-lowest object-contain"
            onError={() => setImgError(true)}
          />
        </button>
      ) : (
        <div className="grid aspect-video max-h-[360px] w-full place-items-center bg-surface-lowest text-text-dim">
          <div className="text-center">
            <Sym name="image" size={28} className="text-text-dim" />
            <p className="mt-1 text-[12px] text-text-variant">Screenshot unavailable for this step.</p>
          </div>
        </div>
      )}
      {event.screenshotFile && showImage && (
        <div className="border-t border-outline px-2 py-1 font-mono text-[11px] text-text-variant">
          {event.screenshotFile}
        </div>
      )}
    </div>
  );
}

function TraceStepDetail({ event }: { event: WebTraceEvent }) {
  const message = event.message.trim();
  return (
    <div className="rounded-md border border-outline bg-surface p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="hud text-[10px] text-primary">
          Step {event.step} · {summarizeAction(event) ?? event.source ?? "agent"}
        </span>
        <span className="truncate font-mono text-[10px] text-text-dim">{actionSignature(event)}</span>
      </div>
      <div className="min-w-0 rounded-md border border-outline bg-surface-low p-2">
        {message && (
          <p className="whitespace-pre-wrap break-words text-[12px] leading-relaxed text-text-variant">{message}</p>
        )}
        {event.actions.length > 0 && (
          <pre
            className={`${message ? "mt-2" : ""} max-h-52 overflow-auto whitespace-pre-wrap break-words rounded bg-field p-2 font-mono text-[11px] text-text-variant`}
          >
            {JSON.stringify(event.actions, null, 2)}
          </pre>
        )}
        {!message && event.actions.length === 0 && (
          <p className="text-[12px] text-text-variant">No extra detail recorded for this step.</p>
        )}
      </div>
    </div>
  );
}

function TraceTile({
  index,
  event,
  active,
  onClick,
}: {
  index: number;
  event: WebTraceEvent;
  active: boolean;
  onClick: () => void;
}) {
  const [imgError, setImgError] = useState(false);
  const hint = summarizeAction(event);
  const showImage = Boolean(event.screenshotUrl) && !imgError;

  useEffect(() => {
    setImgError(false);
  }, [event.step, event.screenshotUrl]);

  return (
    <button
      type="button"
      onClick={onClick}
      style={{ animationDelay: `${Math.min(index, 6) * 30}ms` }}
      className={`rise-in overflow-hidden rounded-md border bg-surface text-left transition active:scale-[0.98] ${FOCUS_RING} ${
        active ? "border-primary" : "border-outline hover:border-primary/60 hover:bg-surface-low"
      }`}
    >
      <div className="grid aspect-video place-items-center border-b border-outline bg-surface-low text-text-dim">
        {showImage ? (
          <img
            src={event.screenshotUrl as string}
            alt={`Screenshot for step ${event.step}`}
            className="h-full w-full bg-surface-lowest object-cover"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        ) : (
          <Sym name="image" size={24} />
        )}
      </div>
      <div className="p-2.5">
        <div className="hud truncate text-[8px] text-text-dim">
          Step {event.step} · {hint ?? event.source ?? "agent"}
        </div>
        <div className="mt-0.5 truncate font-mono text-[10px] text-text-variant">{actionSignature(event)}</div>
      </div>
    </button>
  );
}

function TraceImageLightbox({
  event,
  onClose,
}: {
  event: WebTraceEvent;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={`Full-size screenshot for step ${event.step}`}
      onClick={onClose}
    >
      <div
        className="flex max-h-full w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-outline bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 border-b border-outline px-4 py-3">
          <div className="min-w-0">
            <div className="hud text-[10px] text-primary">
              Step {event.step} · {summarizeAction(event) ?? event.source ?? "agent"}
            </div>
            {event.screenshotFile && (
              <div className="truncate font-mono text-[11px] text-text-variant">
                {event.screenshotFile}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close full-size screenshot"
            className={`grid h-8 w-8 shrink-0 place-items-center rounded-md border border-outline text-text-variant transition hover:border-primary hover:text-text-main active:scale-95 ${FOCUS_RING}`}
          >
            <Sym name="close" size={16} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto bg-surface-low p-3">
          <img
            src={event.screenshotUrl ?? undefined}
            alt={`Full-size screenshot for step ${event.step}`}
            className="mx-auto max-h-[85vh] w-auto max-w-full object-contain"
          />
        </div>
      </div>
    </div>
  );
}
