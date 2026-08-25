/**
 * Minimal quick-create modal for "raise a maintenance issue from this question" (scope §17).
 * Only InspectionResponseId is sent as linkage - app/services/maintenance_service.py derives
 * Property/Inspection/Location itself from the response (never trusted from the client
 * alongside it, per app/schemas/maintenance.py's own comment), so this form only asks for what
 * the backend can't infer: what's wrong, how bad, what kind. Fuller fields (AssignedUserId,
 * DueDate, ...) are left to the eventual Maintenance module frontend, not built yet.
 *
 * Gating is the caller's job, deliberately NOT `editable` (the assigned-inspector-or-Admin/
 * Manager rule InspectionQuestionPage uses for answering/photos) - create_issue only requires
 * CAN_CONDUCT_INSPECTIONS company membership (confirmed by reading maintenance_service.py:
 * it resolves the inspection via inspection_service.get_inspection, a VIEW-level lookup, never
 * ensure_can_edit), so any Administrator/Manager/Inspector at the company can raise an issue
 * against any response - not just the inspector assigned to that specific inspection.
 */
import { useEffect, useState } from "react";
import { ErrorMessage } from "./ErrorMessage";
import { FormField } from "./FormField";
import { Modal } from "./Modal";
import { SelectField } from "./SelectField";
import { MAINTENANCE_CATEGORY_OPTIONS, MAINTENANCE_PRIORITY_OPTIONS } from "../constants/maintenanceOptions";
import { createMaintenanceIssue } from "../services/maintenanceService";
import { getErrorMessage } from "../utilities/apiError";

export function CreateMaintenanceIssueModal({ open, inspectionResponseId, defaultTitle, onClose, onCreated }) {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState("Medium");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      setTitle(defaultTitle ?? "");
      setCategory("");
      setPriority("Medium");
      setDescription("");
      setError(null);
    }
  }, [open, defaultTitle]);

  function handleClose() {
    if (!submitting) {
      onClose();
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!title.trim() || !category) {
      setError("Title and category are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    createMaintenanceIssue({
      inspectionResponseId,
      title: title.trim(),
      category,
      priority,
      description: description.trim() || undefined,
    })
      .then(onCreated)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  return (
    <Modal open={open} title="Create Maintenance Issue" onClose={handleClose}>
      <form onSubmit={handleSubmit}>
        {error && <ErrorMessage message={error} />}
        <FormField label="Title" name="title" value={title} onChange={(event) => setTitle(event.target.value)} required />
        <SelectField
          label="Category"
          name="category"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          options={MAINTENANCE_CATEGORY_OPTIONS}
          placeholder="Choose a category"
          required
        />
        <SelectField
          label="Priority"
          name="priority"
          value={priority}
          onChange={(event) => setPriority(event.target.value)}
          options={MAINTENANCE_PRIORITY_OPTIONS}
        />
        <label className="form-field">
          <span>Description</span>
          <textarea
            className="form-field__input answer-textarea"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        <div className="dialog__actions">
          <button type="button" className="button button--secondary" onClick={handleClose} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Creating…" : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
