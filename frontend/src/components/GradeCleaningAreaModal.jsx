/**
 * The "Grade Cleaning Area" gateway quick-action (scope §16), available throughout the
 * inspection - not tied to one question, the same "gateway section only asks for confirmation"
 * reasoning as AddEmptyUnitModal.jsx (see that file's own header comment for the full story).
 * Minimal fields (CleaningArea/Grade/CleaningRequired/Urgent/Notes) - Assigned cleaner/Due date/
 * Status are workflow fields better suited to a dedicated Cleaning module screen, the same
 * "defer the fuller fields" call Sub-phase C's two quick-create modals made (Status also has no
 * field to set here at all: it starts "Pending" automatically per cleaning_service.py, since no
 * AssignedUserId is supplied). Photos/Videos are scope items too, deliberately deferred for the
 * same reason.
 *
 * Gated by the caller on `editable`, NOT `canRaiseIssues` - confirmed by reading
 * cleaning_service.create_cleaning_inspection first: it calls inspection_service.ensure_can_edit,
 * the same rule AddEmptyUnitModal's create action needs (both gateway actions happened to land
 * on the same tier, verified independently rather than assumed from one another).
 */
import { useEffect, useState } from "react";
import { ErrorMessage } from "./ErrorMessage";
import { Modal } from "./Modal";
import { SelectField } from "./SelectField";
import { listCleaningAreas, createCleaningInspection } from "../services/cleaningService";
import { CLEANING_GRADE_OPTIONS } from "../constants/cleaningOptions";
import { getErrorMessage } from "../utilities/apiError";

export function GradeCleaningAreaModal({ open, inspectionId, propertyId, onClose, onCreated }) {
  const [areas, setAreas] = useState([]);
  const [loadingAreas, setLoadingAreas] = useState(true);
  const [cleaningAreaId, setCleaningAreaId] = useState("");
  const [grade, setGrade] = useState("");
  const [cleaningRequired, setCleaningRequired] = useState(false);
  const [urgent, setUrgent] = useState(false);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setCleaningAreaId("");
    setGrade("");
    setCleaningRequired(false);
    setUrgent(false);
    setNotes("");
    setError(null);
    setLoadingAreas(true);
    listCleaningAreas(propertyId)
      .then(setAreas)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoadingAreas(false));
  }, [open, propertyId]);

  function handleClose() {
    if (!submitting) {
      onClose();
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!cleaningAreaId || !grade) {
      setError("Choose an area and a grade.");
      return;
    }
    setSubmitting(true);
    setError(null);
    createCleaningInspection(inspectionId, {
      cleaningAreaId: Number(cleaningAreaId),
      grade,
      cleaningRequired,
      urgent,
      notes: notes.trim(),
    })
      .then(onCreated)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  return (
    <Modal open={open} title="Grade Cleaning Area" onClose={handleClose}>
      <form onSubmit={handleSubmit}>
        {error && <ErrorMessage message={error} />}

        <SelectField
          label="Area"
          name="cleaningAreaId"
          value={cleaningAreaId}
          onChange={(event) => setCleaningAreaId(event.target.value)}
          options={areas.map((a) => ({ value: String(a.CleaningAreaId), label: a.AreaName }))}
          placeholder={loadingAreas ? "Loading areas…" : areas.length === 0 ? "No cleaning areas configured" : "Choose an area"}
          required
        />
        <SelectField
          label="Grade"
          name="grade"
          value={grade}
          onChange={(event) => setGrade(event.target.value)}
          options={CLEANING_GRADE_OPTIONS}
          placeholder="Choose a grade"
          required
        />
        <label className="checkbox-field">
          <input type="checkbox" checked={cleaningRequired} onChange={(event) => setCleaningRequired(event.target.checked)} />
          Cleaning required
        </label>
        <label className="checkbox-field">
          <input type="checkbox" checked={urgent} onChange={(event) => setUrgent(event.target.checked)} />
          Urgent
        </label>
        <label className="form-field">
          <span>Notes</span>
          <textarea className="form-field__input answer-textarea" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>

        <div className="dialog__actions">
          <button type="button" className="button button--secondary" onClick={handleClose} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" className="button" disabled={submitting || loadingAreas}>
            {submitting ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
