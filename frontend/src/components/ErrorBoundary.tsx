import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallbackLabel: string;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`${this.props.fallbackLabel} crashed:`, error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <section className="panel-error-fallback" aria-live="polite">
          <span className="section-kicker">{this.props.fallbackLabel}</span>
          <p>This panel failed to load and has been disabled so the rest of the dashboard keeps working.</p>
          <small>{this.state.error.message}</small>
        </section>
      );
    }
    return this.props.children;
  }
}
