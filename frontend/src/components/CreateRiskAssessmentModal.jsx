/**
 * Minimal quick-create modal for "raise a risk from this question" (scope §19). Only
 * InspectionResponseId is sent as linkage - app/services/risk_service.py derives Property/
 * Inspection itself from the response, and RiskScore/RiskLevel are computed server-side
 * (RiskScore is a real PERSISTED computed column, Phase 13 - structurally impossible to supply
 * from here even if this form tried to). Likelihood/Severity options use scope §19's own exact
 * scale text (constants/riskOptions.js), not an invented one.
 *
 * Gating is the caller's job, deliberately NOT `editable` - same reasoning as
 * CreateMaintenanceIssueModal (see its own header comment): create_risk_assessment only
 * requires CAN_CONDUCT_INSPECTIONS company membership, not being this inspection's assigned
 * inspector.
 */
import { useEffect, useState } from "react";
import { ErrorMessage } from "./ErrorMessage";
import { FormField } from "./FormField";
import { Modal } from "./Modal";
import { SelectField } from "./SelectField";
import { LIKELIHOOD_OPTIONS, SEVERITY_OPTIONS } from "../constants/riskOptions";
import { createRiskAssessment } from "../services/riskService";
import { getErrorMessage } from "../utilities/apiError";

export function CreateRiskAssessmentModal({ open, inspectionResponseId, defaultHazard, onClose, onCreated }) {
  const [hazard, setHazard] = useState("");
  const [likelihood, setLikelihood] = useState("");
  const [severity, setSeverity] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      setHazard(defaultHazard ?? "");
      setLikelihood("");
      setSeverity("");
      setNotes("");
      setError(null);
    }
  }, [open, defaultHazard]);

  function handleClose() {
    if (!submitting) {
      onClose();
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!hazard.trim() || !likelihood || !severity) {
      setError("Hazard, likelihood, and severity are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    createRiskAssessment({
      inspectionResponseId,
      hazard: hazard.trim(),
      likelihood: Number(likelihood),
      severity: Number(severity),
      notes: notes.trim() || undefined,
    })
      .then(onCreated)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  return (
    <Modal open={open} title="Create Risk Assessment" onClose={handleClose}>
      <form onSubmit={handleSubmit}>
        {error && <ErrorMessage message={error} />}
        <FormField label="Hazard" name="hazard" value={hazard} onChange={(event) => setHazard(event.target.value)} required />
        <SelectField
          label="Likelihood"
          name="likelihood"
          value={likelihood}
          onChange={(event) => setLikelihood(event.target.value)}
          options={LIKELIHOOD_OPTIONS}
          placeholder="Choose likelihood"
          required
        />
        <SelectField
          label="Severity"
          name="severity"
          value={severity}
          onChange={(event) => setSeverity(event.target.value)}
          options={SEVERITY_OPTIONS}
          placeholder="Choose severity"
          required
        />
        <label className="form-field">
          <span>Notes</span>
          <textarea
            className="form-field__input answer-textarea"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
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
