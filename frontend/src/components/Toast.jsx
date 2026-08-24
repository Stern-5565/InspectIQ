/**
 * Transient success/error banner shown after an action completes (e.g. "Property created.").
 * Pages own their own toast state (`useState(null)`) rather than this reaching into a global
 * store - a page navigating away is a perfectly good way for a toast to disappear.
 */
import { useEffect } from "react";

export function Toast({ message, tone = "success", onDismiss, durationMs = 4000 }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, durationMs);
    return () => clearTimeout(timer);
  }, [onDismiss, durationMs]);

  return (
    <div className={`toast toast--${tone}`} role="status">
      <span>{message}</span>
      <button type="button" className="toast__dismiss" onClick={onDismiss} aria-label="Dismiss notification">
        ×
      </button>
    </div>
  );
}
