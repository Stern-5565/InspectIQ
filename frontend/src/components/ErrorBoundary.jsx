/**
 * Global render-error safety net. React error boundaries must be class components - there is
 * no hooks equivalent - so this is the one class component in the codebase, by necessity
 * rather than style.
 *
 * This only catches errors thrown while RENDERING (a component crashing). It does NOT catch
 * API/network errors - those are handled per-request via utilities/apiError.js and shown
 * inline in whichever component made the call, since "the server said no" is a normal,
 * recoverable state, not an application crash.
 */
import { Component } from "react";

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Unhandled error in component tree:", error, info);
  }

  handleReset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary">
          <h1>Something went wrong</h1>
          <p>An unexpected error occurred. Try again, or reload the page.</p>
          <div className="error-boundary__actions">
            <button type="button" className="button" onClick={this.handleReset}>
              Try again
            </button>
            <button type="button" className="button button--secondary" onClick={() => window.location.reload()}>
              Reload
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
