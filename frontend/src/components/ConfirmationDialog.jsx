/**
 * Modal "are you sure?" prompt for destructive/irreversible actions (deactivating a property,
 * ...). Deliberately not a full focus-trap implementation - no third-party dialog library.
 * What it does do: moves focus to Cancel on open (so an accidental Enter press doesn't confirm
 * a destructive action), closes on Escape, and closes on backdrop click.
 */
import { useEffect, useRef } from "react";

export function ConfirmationDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  danger = false,
  confirmDisabled = false,
}) {
  const cancelButtonRef = useRef(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    cancelButtonRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onCancel();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" onClick={onCancel}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirmation-dialog-title"
        aria-describedby="confirmation-dialog-message"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="confirmation-dialog-title" className="dialog__title">
          {title}
        </h2>
        <p id="confirmation-dialog-message">{message}</p>
        <div className="dialog__actions">
          <button type="button" ref={cancelButtonRef} className="button button--secondary" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={danger ? "button button--danger" : "button"}
            onClick={onConfirm}
            disabled={confirmDisabled}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
