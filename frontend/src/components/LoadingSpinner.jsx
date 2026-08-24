/**
 * Generic loading indicator - used both as a full-page state (e.g. while AuthContext restores
 * a session) and inline within a page. `size` only changes the circle's dimensions, not the
 * markup/behavior, so every consumer stays this one component.
 */
export function LoadingSpinner({ label = "Loading…", fullPage = false, size = "medium" }) {
  const spinner = (
    <div className={`loading-spinner loading-spinner--${size}`} role="status" aria-live="polite">
      <span className="loading-spinner__circle" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );

  if (!fullPage) {
    return spinner;
  }

  return <div className="loading-spinner__page">{spinner}</div>;
}
