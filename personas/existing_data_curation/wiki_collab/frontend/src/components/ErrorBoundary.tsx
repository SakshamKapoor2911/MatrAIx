/**
 * ErrorBoundary — a top-level React error boundary so an uncaught render error
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
    console.error("RecBot Studio crashed:", error, info.componentStack);
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
      <div className="grid min-h-screen place-items-center bg-background p-6 text-on-surface">
        <div className="w-full max-w-md rounded-xl border border-border-soft bg-surface-container-lowest p-6 shadow-pop">
          <div className="flex items-center gap-2.5">
            <Sym name="error" fill={1} size={22} className="flex-none text-error" />
            <h1 className="text-headline-md font-headline-md text-on-surface">Something went wrong</h1>
          </div>
          <p className="mt-2 text-body-md leading-relaxed text-on-surface-variant">
            The Studio hit an unexpected error and stopped rendering. Your data is safe — you can
            recover the view or reload the app.
          </p>
          {error.message && (
            <pre className="mt-3 max-h-32 overflow-auto rounded-md border border-border-soft bg-surface-container-low px-3 py-2 font-mono-sm text-mono-sm leading-relaxed text-on-surface-variant">
              {error.message}
            </pre>
          )}
          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              onClick={this.handleReset}
              className={`inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-label-md font-label-md text-on-primary shadow-sm transition-colors hover:bg-primary-container ${FOCUS_RING}`}
            >
              <Sym name="refresh" size={16} />
              Try again
            </button>
            <button
              type="button"
              onClick={this.handleReload}
              className={`inline-flex items-center gap-1.5 rounded-md border border-outline-variant px-4 py-2 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface ${FOCUS_RING}`}
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
