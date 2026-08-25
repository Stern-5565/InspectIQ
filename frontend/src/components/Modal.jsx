/**
 * Generic modal shell (backdrop + Escape/backdrop-click to close), sharing ConfirmationDialog's
 * .dialog-backdrop/.dialog CSS but with a free-form body instead of a fixed message +
 * confirm/cancel footer - a form needs its own field layout and submit handling, which
 * ConfirmationDialog's API has no room for. Used by CreateMaintenanceIssueModal/
 * CreateRiskAssessmentModal (Sub-phase C) so that shell isn't duplicated per form.
 */
import { useEffect } from "react";

export function Modal({ open, title, onClose, children }) {
  useEffect(() => {
    if (!open) {
      return;
    }
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="modal-dialog-title" className="dialog__title">
          {title}
        </h2>
        {children}
      </div>
    </div>
  );
}
