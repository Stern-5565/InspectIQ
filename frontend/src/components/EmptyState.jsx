/**
 * Generic "nothing here" placeholder - used by DataTable when a list comes back empty, and
 * reusable standalone anywhere else the same pattern applies.
 */
export function EmptyState({ message = "Nothing to show yet.", actionLabel, onAction }) {
  return (
    <div className="empty-state">
      <p>{message}</p>
      {actionLabel && onAction && (
        <button type="button" className="button" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
