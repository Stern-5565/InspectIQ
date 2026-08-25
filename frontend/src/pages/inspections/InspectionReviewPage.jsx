/**
 * Sub-phase F (the final sub-phase of the wizard, Prompt 17): Inspection Review and Submit.
 * Genuinely useful only because of the `PATCH /api/inspections/{id}` endpoint added during
 * Sub-phase A's own planning - GeneralNotes/OverallCondition/OverallRiskRating existed on
 * InspectionDetailResponse since Phase 8 but had no way to ever be set before that.
 *
 * OverallRiskRating's SelectField is populated from the company's own configured risk matrix
 * (GET /api/risk-matrix-levels' LevelNames - "Low"/"Medium"/"High"/"Critical" for the seeded
 * global default) rather than a hardcoded list - matching app/schemas/inspection.py's own
 * documented reasoning for leaving the field a plain string in the first place.
 *
 * Deliberately does NOT try to compute "which mandatory questions are still unanswered" client-
 * side - InspectionResponseSchema's frozen snapshot doesn't carry the live IsMandatory flag
 * (same fact MediaAttachments.jsx's header comment already established for AllowsPhoto/
 * RequiresPhoto), so any client-side reconstruction would risk disagreeing with the backend's
 * own check. `submit_inspection` already computes the exact count and a preview of which
 * questions - this page just surfaces that message verbatim via getErrorMessage() on a 422,
 * rather than duplicating (and risking drifting from) that logic.
 *
 * "Inspection Report" (PDF) is explicitly OUT of scope for this page - PROJECT_PLAN.md §11's
 * phase table makes it Phase 17, which doesn't exist yet.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";
import { ErrorMessage } from "../../components/ErrorMessage";
import { PageHeader } from "../../components/PageHeader";
import { SelectField } from "../../components/SelectField";
import { StatusBadge } from "../../components/StatusBadge";
import { Toast } from "../../components/Toast";
import { submitInspection, updateInspectionSummary } from "../../services/inspectionService";
import { getRiskMatrix } from "../../services/riskService";
import { OVERALL_CONDITION_OPTIONS } from "../../constants/overallConditionOptions";
import { getErrorMessage } from "../../utilities/apiError";
import { isAnswered } from "../../utilities/inspectionAnswers";
import { useDebouncedCallback } from "../../utilities/useDebouncedCallback";

export function InspectionReviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { inspection, canEdit, applyInspectionUpdate } = useOutletContext();

  const [riskLevels, setRiskLevels] = useState([]);
  const [loadingLevels, setLoadingLevels] = useState(true);

  const [notesValue, setNotesValue] = useState(inspection.GeneralNotes ?? "");
  const [saveError, setSaveError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState(null);

  const [debouncedSaveNotes, flushSaveNotes] = useDebouncedCallback((value) => saveField({ GeneralNotes: value }));

  useEffect(() => {
    setNotesValue(inspection.GeneralNotes ?? "");
  }, [inspection.InspectionId]);

  useEffect(() => {
    getRiskMatrix()
      .then(setRiskLevels)
      .catch((err) => setSaveError(getErrorMessage(err)))
      .finally(() => setLoadingLevels(false));
  }, []);

  const editable = canEdit && inspection.Status !== "Submitted";
  const totalResponses = inspection.Sections.reduce((sum, s) => sum + s.Responses.length, 0);
  const totalAnswered = inspection.Sections.reduce(
    (sum, s) => sum + s.Responses.filter(isAnswered).length,
    0,
  );

  function saveField(payload) {
    setSaveError(null);
    updateInspectionSummary(id, payload).then(applyInspectionUpdate).catch((err) => setSaveError(getErrorMessage(err)));
  }

  function handleSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    submitInspection(id)
      .then((updated) => {
        applyInspectionUpdate(updated);
        setToast("Inspection submitted.");
      })
      .catch((err) => setSubmitError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  return (
    <div>
      <PageHeader title="Inspection Review" description="Confirm the overall summary before submitting." />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="detail-card">
        <StatusBadge status={inspection.Status} />
        <div className="inspection-progress">
          <div className="inspection-progress__bar">
            <div className="inspection-progress__fill" style={{ width: `${inspection.CompletionPercentage}%` }} />
          </div>
          <span className="inspection-progress__label">
            {inspection.CompletionPercentage}% complete ({totalAnswered}/{totalResponses} questions)
          </span>
        </div>

        {inspection.Status === "Submitted" && (
          <p className="empty-state">Submitted {new Date(inspection.SubmittedAt).toLocaleString()}.</p>
        )}
        {!canEdit && inspection.Status !== "Submitted" && (
          <p className="empty-state">
            You can view this inspection, but only its assigned inspector (or an Administrator/Manager) can edit its
            summary or submit it.
          </p>
        )}

        {saveError && <ErrorMessage message={saveError} />}

        <SelectField
          label="Overall condition"
          name="overallCondition"
          value={inspection.OverallCondition ?? ""}
          onChange={(event) => saveField({ OverallCondition: event.target.value })}
          options={OVERALL_CONDITION_OPTIONS}
          placeholder="Not set"
          disabled={!editable}
        />

        <SelectField
          label="Overall risk rating"
          name="overallRiskRating"
          value={inspection.OverallRiskRating ?? ""}
          onChange={(event) => saveField({ OverallRiskRating: event.target.value })}
          options={riskLevels.map((level) => ({ value: level.LevelName, label: level.LevelName }))}
          placeholder={loadingLevels ? "Loading…" : "Not set"}
          disabled={!editable || loadingLevels}
        />

        <label className="form-field">
          <span>General notes</span>
          <textarea
            className="form-field__input answer-textarea"
            value={notesValue}
            disabled={!editable}
            onChange={(event) => {
              setNotesValue(event.target.value);
              debouncedSaveNotes(event.target.value);
            }}
            onBlur={() => {
              if (notesValue !== (inspection.GeneralNotes ?? "")) {
                flushSaveNotes(notesValue);
              }
            }}
          />
        </label>

        {submitError && <ErrorMessage message={submitError} />}

        {editable && (
          <button type="button" className="button" disabled={submitting} onClick={handleSubmit}>
            {submitting ? "Submitting…" : "Submit Inspection"}
          </button>
        )}
      </div>

      <p>
        <Link to={`/inspections/${id}`}>← Back to sections</Link>
      </p>
    </div>
  );
}
