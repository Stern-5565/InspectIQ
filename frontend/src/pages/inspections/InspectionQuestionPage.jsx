/**
 * "Inside each question: question text, answer controls, notes, ... Previous/Next" (Prompt
 * 17). Photo/Video is wired (Sub-phase B, via components/MediaAttachments.jsx against
 * EntityType=InspectionResponse). Create Maintenance/Create Risk are wired too (Sub-phase C),
 * gated on `canRaiseIssues` from InspectionWizardLayout - deliberately NOT `editable`, since
 * the backend's create_issue/create_risk_assessment only require CAN_CONDUCT_INSPECTIONS
 * company membership, not being this inspection's assigned inspector (see
 * InspectionWizardLayout.jsx's own comment on the distinction).
 *
 * Answer types YesNo/PassFail/Condition render as tap buttons (instant save, no separate save
 * step - "as few taps as possible"). Text/Number/Notes debounce-save WHILE typing (700ms after
 * the last keystroke) with an immediate flush on blur, not blur-only - found while verifying
 * this page live that blur alone isn't a reliable enough save trigger for a field an inspector
 * is typing into on a phone (see utilities/useDebouncedCallback.js's own comment). Date saves
 * on change (a single discrete pick, no typing to debounce). Condition uses a curated
 * Good/Fair/Poor preset (owner's explicit choice, 2026-08-25) even though the backend leaves
 * the field genuinely freeform - still just plain text once saved. MeterReading gets an honest
 * placeholder, not a fake text input - its real flow (photo -> mock OCR -> confirm) is
 * sub-phase D, wired to a completely different endpoint (/api/meter-readings), not this one.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { ErrorMessage } from "../../components/ErrorMessage";
import { CreateMaintenanceIssueModal } from "../../components/CreateMaintenanceIssueModal";
import { CreateRiskAssessmentModal } from "../../components/CreateRiskAssessmentModal";
import { MediaAttachments } from "../../components/MediaAttachments";
import { StatusBadge } from "../../components/StatusBadge";
import { Toast } from "../../components/Toast";
import { updateResponse } from "../../services/inspectionService";
import { getErrorMessage } from "../../utilities/apiError";
import { isAnswered, isFailed } from "../../utilities/inspectionAnswers";
import { useDebouncedCallback } from "../../utilities/useDebouncedCallback";

const CONDITION_OPTIONS = ["Good", "Fair", "Poor"];

function flattenPositions(sections) {
  const positions = [];
  sections.forEach((section, sectionIndex) => {
    section.Responses.forEach((_, questionIndex) => {
      positions.push({ sectionIndex, questionIndex });
    });
  });
  return positions;
}

function AnswerControl({ response, editable, onSave, saving }) {
  const [textValue, setTextValue] = useState(response.AnswerText ?? "");
  const [numberValue, setNumberValue] = useState(response.AnswerNumber ?? "");
  const [dateValue, setDateValue] = useState(response.AnswerDate ?? "");

  const [debouncedSaveText, flushSaveText] = useDebouncedCallback((value) => onSave({ AnswerText: value }));
  const [debouncedSaveNumber, flushSaveNumber] = useDebouncedCallback((value) => onSave({ AnswerNumber: value }));

  useEffect(() => {
    setTextValue(response.AnswerText ?? "");
    setNumberValue(response.AnswerNumber ?? "");
    setDateValue(response.AnswerDate ?? "");
  }, [response.InspectionResponseId]);

  const disabled = !editable || saving;

  switch (response.AnswerTypeSnapshot) {
    case "YesNo":
      return (
        <div className="answer-buttons">
          {["Yes", "No"].map((value) => (
            <button
              key={value}
              type="button"
              className={`answer-button${response.AnswerText === value ? " answer-button--selected" : ""}`}
              disabled={disabled}
              onClick={() => onSave({ AnswerText: value })}
            >
              {value}
            </button>
          ))}
        </div>
      );

    case "PassFail":
      return (
        <div className="answer-buttons">
          {["Pass", "Fail"].map((value) => (
            <button
              key={value}
              type="button"
              className={`answer-button${response.AnswerText === value ? " answer-button--selected" : ""}${
                value === "Fail" ? " answer-button--danger" : ""
              }`}
              disabled={disabled}
              onClick={() => onSave({ AnswerText: value })}
            >
              {value}
            </button>
          ))}
        </div>
      );

    case "Condition":
      return (
        <div className="answer-buttons">
          {CONDITION_OPTIONS.map((value) => (
            <button
              key={value}
              type="button"
              className={`answer-button${response.AnswerText === value ? " answer-button--selected" : ""}`}
              disabled={disabled}
              onClick={() => onSave({ AnswerText: value })}
            >
              {value}
            </button>
          ))}
        </div>
      );

    case "Text":
      return (
        <textarea
          className="form-field__input answer-textarea"
          value={textValue}
          disabled={disabled}
          onChange={(event) => {
            setTextValue(event.target.value);
            debouncedSaveText(event.target.value);
          }}
          onBlur={() => {
            if (textValue !== (response.AnswerText ?? "")) {
              flushSaveText(textValue);
            }
          }}
        />
      );

    case "Number":
      return (
        <input
          type="number"
          className="form-field__input"
          value={numberValue}
          disabled={disabled}
          onChange={(event) => {
            setNumberValue(event.target.value);
            if (event.target.value !== "") {
              debouncedSaveNumber(event.target.value);
            }
          }}
          onBlur={() => {
            if (String(numberValue) !== String(response.AnswerNumber ?? "") && numberValue !== "") {
              flushSaveNumber(numberValue);
            }
          }}
        />
      );

    case "Date":
      return (
        <input
          type="date"
          className="form-field__input"
          value={dateValue}
          disabled={disabled}
          onChange={(event) => {
            setDateValue(event.target.value);
            if (event.target.value) {
              onSave({ AnswerDate: event.target.value });
            }
          }}
        />
      );

    default:
      // MeterReading (or any future answer type) - the real photo/OCR/confirm flow is a
      // separate, later piece of work (sub-phase D), wired to /api/meter-readings, not this
      // generic response-update endpoint.
      return (
        <p className="empty-state">
          This question uses the Meter Reading flow - full support is coming in a later update.
          You can still add notes or mark it Not Applicable below.
        </p>
      );
  }
}

export function InspectionQuestionPage() {
  const { id, sectionIndex, questionIndex } = useParams();
  const navigate = useNavigate();
  const { inspection, canEdit, canRaiseIssues, applyResponseUpdate } = useOutletContext();

  const sectionIdx = Number(sectionIndex);
  const questionIdx = Number(questionIndex);
  const section = inspection.Sections[sectionIdx];
  const response = section?.Responses[questionIdx];

  const [notesValue, setNotesValue] = useState(response?.Notes ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [debouncedSaveNotes, flushSaveNotes] = useDebouncedCallback((value) => save({ Notes: value }));
  const [showMaintenanceModal, setShowMaintenanceModal] = useState(false);
  const [showRiskModal, setShowRiskModal] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    setNotesValue(response?.Notes ?? "");
    setError(null);
  }, [response?.InspectionResponseId]);

  if (!section || !response) {
    return <ErrorMessage message="That question doesn't exist in this inspection." />;
  }

  const editable = canEdit && inspection.Status !== "Submitted";
  const positions = flattenPositions(inspection.Sections);
  const currentFlatIndex = positions.findIndex(
    (p) => p.sectionIndex === sectionIdx && p.questionIndex === questionIdx,
  );
  const previousPosition = currentFlatIndex > 0 ? positions[currentFlatIndex - 1] : null;
  const nextPosition = currentFlatIndex < positions.length - 1 ? positions[currentFlatIndex + 1] : null;

  function goTo(position) {
    navigate(`/inspections/${id}/sections/${position.sectionIndex}/questions/${position.questionIndex}`);
  }

  function save(payload) {
    setSaving(true);
    setError(null);
    updateResponse(id, response.InspectionResponseId, payload)
      .then(applyResponseUpdate)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  return (
    <div>
      <PageHeader
        title={section.SectionName}
        description={`Question ${questionIdx + 1} of ${section.Responses.length}`}
      />

      <div className="question-card">
        <div className="question-card__badges">
          {response.IsNotApplicable ? (
            <StatusBadge status="Not Applicable" tone="neutral" />
          ) : isAnswered(response) ? (
            <StatusBadge status="Answered" tone="success" />
          ) : (
            <StatusBadge status="Unanswered" tone="neutral" />
          )}
          {/* Not Applicable and Failed are mutually exclusive in this display, even though the
              backend permits both flags being true at once (marking N/A doesn't clear a prior
              AnswerText) - N/A means "ignore whatever was answered before," so it takes
              precedence over showing a stale Failed badge. */}
          {!response.IsNotApplicable && isFailed(response) && <StatusBadge status="Failed" tone="danger" />}
        </div>

        <p className="question-card__text">{response.QuestionTextSnapshot}</p>

        {error && <ErrorMessage message={error} />}

        {response.IsNotApplicable ? (
          <p className="empty-state">Marked as Not Applicable.</p>
        ) : (
          <AnswerControl response={response} editable={editable} onSave={save} saving={saving} />
        )}

        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={response.IsNotApplicable}
            disabled={!editable || saving}
            onChange={(event) => save({ IsNotApplicable: event.target.checked })}
          />
          Not Applicable
        </label>

        <label className="form-field">
          <span>Notes</span>
          <textarea
            className="form-field__input answer-textarea"
            value={notesValue}
            disabled={!editable || saving}
            onChange={(event) => {
              setNotesValue(event.target.value);
              debouncedSaveNotes(event.target.value);
            }}
            onBlur={() => {
              if (notesValue !== (response.Notes ?? "")) {
                flushSaveNotes(notesValue);
              }
            }}
          />
        </label>

        <MediaAttachments
          entityType="InspectionResponse"
          entityId={response.InspectionResponseId}
          editable={editable}
        />

        {canRaiseIssues && (
          <div className="question-card__quick-actions">
            <button type="button" className="button button--secondary button--small" onClick={() => setShowMaintenanceModal(true)}>
              + Create Maintenance Issue
            </button>
            <button type="button" className="button button--secondary button--small" onClick={() => setShowRiskModal(true)}>
              + Create Risk Assessment
            </button>
          </div>
        )}
      </div>

      <CreateMaintenanceIssueModal
        open={showMaintenanceModal}
        inspectionResponseId={response.InspectionResponseId}
        defaultTitle={response.QuestionTextSnapshot}
        onClose={() => setShowMaintenanceModal(false)}
        onCreated={(issue) => {
          setShowMaintenanceModal(false);
          setToast(`Maintenance issue "${issue.Title}" created.`);
        }}
      />

      <CreateRiskAssessmentModal
        open={showRiskModal}
        inspectionResponseId={response.InspectionResponseId}
        defaultHazard={response.QuestionTextSnapshot}
        onClose={() => setShowRiskModal(false)}
        onCreated={(risk) => {
          setShowRiskModal(false);
          setToast(`Risk assessment created (Risk Level: ${risk.RiskLevel}).`);
        }}
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="question-nav">
        <button type="button" className="button button--secondary" disabled={!previousPosition} onClick={() => previousPosition && goTo(previousPosition)}>
          ← Previous
        </button>
        {nextPosition ? (
          <button type="button" className="button" onClick={() => goTo(nextPosition)}>
            Next →
          </button>
        ) : (
          <Link to={`/inspections/${id}`} className="button">
            Finish section review
          </Link>
        )}
      </div>

      <p>
        <Link to={`/inspections/${id}`}>← Back to sections</Link>
      </p>
    </div>
  );
}
