/**
 * ErrorBoundary: a top-level React error boundary so an uncaught render error
 * shows a recoverable fallback instead of a white screen.
 *
 * Wraps `<App/>` in `main.tsx`. A render-time exception is caught, the message
 * is surfaced, and the operator can "Try again" (re-mount the subtree) or
 * "Reload" (hard refresh). Data-fetch errors are handled in-pane by React Query;
 * this is the last-resort net for component crashes.
 */
import { Component, type ErrorInfo, type ReactNode } from "react";

import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Surface the crash for local debugging; in a research tool the console is
    // the operator's primary log.
    // eslint-disable-next-line no-console
    console.error("PersonaEval crashed:", error, info.componentStack);
  }

  private handleReset = (): void => {
    this.setState({ error: null });
  };

  private handleReload = (): void => {
    if (typeof window !== "undefined") window.location.reload();
  };

  render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="grid min-h-screen place-items-center bg-surface-dim p-6 text-text-main">
        <div className="panel rise-in w-full max-w-md rounded-md border border-outline bg-surface p-6 shadow-2xl">
          <div className="flex items-center gap-2.5">
            <Sym name="error" fill={1} size={22} className="flex-none text-danger" />
            <h1 className="font-display text-lg font-bold tracking-tight text-text-main">Something went wrong</h1>
          </div>
          <p className="mt-2 text-[13px] leading-relaxed text-text-variant">
            PersonaEval hit an unexpected error and stopped rendering. Your data is safe. You can
            recover the view or reload the app.
          </p>
          {error.message && (
            <pre className="mt-3 max-h-32 overflow-auto whitespace-pre-wrap break-words rounded-md border border-outline bg-field px-3 py-2 font-mono text-[11px] leading-relaxed text-text-variant">
              {error.message}
            </pre>
          )}
          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              onClick={this.handleReset}
              className={`inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-xs font-medium text-on-primary transition hover:bg-primary-dim active:scale-[0.98] ${FOCUS_RING}`}
            >
              <Sym name="refresh" size={16} />
              Try again
            </button>
            <button
              type="button"
              onClick={this.handleReload}
              className={`inline-flex items-center gap-1.5 rounded-md border border-outline px-4 py-2 text-xs font-medium text-text-variant transition hover:bg-surface-low hover:text-text-main active:scale-[0.98] ${FOCUS_RING}`}
            >
              Reload
            </button>
          </div>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
