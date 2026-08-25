/**
 * The MeterReading answer type's own flow (scope §11, Sub-phase D): photo -> mock OCR -> the
 * inspector confirms or corrects. Wired to /api/meter-readings, NOT the generic
 * PATCH .../responses/{id} endpoint InspectionQuestionPage.jsx uses for every other answer type
 * - a meter reading is its own record (AIDetectedReading/ConfirmedReading/PhotoMediaFileId),
 * not free text on the response.
 *
 * Two DIFFERENT authorization tiers in one control, confirmed by reading
 * meter_reading_service.py before wiring either half (the same lesson Sub-phase C's
 * CreateMaintenanceIssueModal/CreateRiskAssessmentModal header comments document):
 *   - `canCreate` (CAN_CONDUCT_INSPECTIONS, i.e. `canRaiseIssues` from InspectionWizardLayout) -
 *     create_meter_reading has no ensure_can_edit-style check at all, so any Administrator/
 *     Manager/Inspector at the company can take and upload the photo.
 *   - `canConfirm` (`editable` from InspectionWizardLayout) - update_meter_reading calls
 *     ensure_can_edit_reading, which for an Inspection-linked reading is exactly the
 *     assigned-inspector-or-Admin/Manager rule every other answer control uses.
 * The photo/AI value themselves are always visible regardless of either flag (view has no role
 * restriction, matching every other module).
 *
 * On confirm, `onConfirmed` lets the parent question page sync the generic InspectionResponse
 * (AnswerNumber -> the backend auto-derives AnswerText = str(AnswerNumber), same as the Number
 * answer type) - otherwise this question would never count towards CompletionPercentage. This
 * deliberately happens only at CONFIRM, not at photo-upload: scope's own flow treats an
 * unconfirmed AI reading as not yet answered (Phase 14 was explicit the AI value must never
 * silently become the confirmed one; the same principle extends to "answered" here).
 */
import { useEffect, useRef, useState } from "react";
import { ErrorMessage } from "./ErrorMessage";
import { FormField } from "./FormField";
import { SelectField } from "./SelectField";
import { downloadMediaBlob } from "../services/mediaService";
import { createMeterReading, listMeterReadings, updateMeterReading } from "../services/meterReadingService";
import { METER_TYPE_OPTIONS, guessMeterTypeFromSectionName } from "../constants/meterReadingOptions";
import { getErrorMessage } from "../utilities/apiError";

export function MeterReadingControl({ inspectionResponseId, propertyId, sectionName, canCreate, canConfirm, onConfirmed }) {
  const [loading, setLoading] = useState(true);
  const [reading, setReading] = useState(null);
  const [photoUrl, setPhotoUrl] = useState(null);
  const [error, setError] = useState(null);

  const [meterType, setMeterType] = useState("");
  const [createSerial, setCreateSerial] = useState("");
  const [creating, setCreating] = useState(false);
  const fileInputRef = useRef(null);

  const [editingConfirmation, setEditingConfirmation] = useState(false);
  const [confirmedReading, setConfirmedReading] = useState("");
  const [confirmSerial, setConfirmSerial] = useState("");
  const [inspectorNotes, setInspectorNotes] = useState("");
  const [confirming, setConfirming] = useState(false);

  const photoUrlRef = useRef(null);
  photoUrlRef.current = photoUrl;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setMeterType(guessMeterTypeFromSectionName(sectionName));

    listMeterReadings({ inspectionResponseId, pageSize: 1 })
      .then(async (page) => {
        if (cancelled) return;
        const existing = page.items[0] ?? null;
        setReading(existing);
        if (existing?.PhotoMediaFileId) {
          const blob = await downloadMediaBlob(existing.PhotoMediaFileId);
          if (!cancelled) setPhotoUrl(URL.createObjectURL(blob));
        }
      })
      .catch((err) => !cancelled && setError(getErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
      if (photoUrlRef.current) {
        URL.revokeObjectURL(photoUrlRef.current);
      }
    };
  }, [inspectionResponseId, sectionName]);

  function handleFileChosen(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !meterType) return;

    setCreating(true);
    setError(null);
    createMeterReading({
      propertyId,
      meterType,
      inspectionResponseId,
      meterSerialNumber: createSerial.trim() || undefined,
      file,
    })
      .then(async (created) => {
        setReading(created);
        if (created.PhotoMediaFileId) {
          const blob = await downloadMediaBlob(created.PhotoMediaFileId);
          setPhotoUrl(URL.createObjectURL(blob));
        }
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setCreating(false));
  }

  function startConfirming() {
    setConfirmedReading(String(reading.ConfirmedReading ?? reading.AIDetectedReading ?? ""));
    setConfirmSerial(reading.MeterSerialNumber ?? "");
    setInspectorNotes(reading.InspectorNotes ?? "");
    setError(null);
    setEditingConfirmation(true);
  }

  function handleConfirmSubmit(event) {
    event.preventDefault();
    if (!confirmedReading.trim()) {
      setError("Enter the meter reading.");
      return;
    }
    setConfirming(true);
    setError(null);
    updateMeterReading(reading.MeterReadingId, {
      confirmedReading: Number(confirmedReading),
      meterSerialNumber: confirmSerial.trim() || undefined,
      inspectorNotes: inspectorNotes.trim() || undefined,
    })
      .then((updated) => {
        setReading(updated);
        setEditingConfirmation(false);
        onConfirmed(updated.ConfirmedReading);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setConfirming(false));
  }

  if (loading) {
    return <p className="empty-state">Loading meter reading…</p>;
  }

  return (
    <div className="meter-reading">
      {error && <ErrorMessage message={error} />}

      {!reading && (
        <div className="meter-reading__create">
          {canCreate ? (
            <>
              <SelectField
                label="Meter type"
                name="meterType"
                value={meterType}
                onChange={(event) => setMeterType(event.target.value)}
                options={METER_TYPE_OPTIONS}
                placeholder="Choose a meter type"
                required
              />
              <FormField
                label="Meter serial number (optional)"
                name="meterSerialNumber"
                value={createSerial}
                onChange={(event) => setCreateSerial(event.target.value)}
              />
              <button
                type="button"
                className="button button--secondary"
                disabled={creating || !meterType}
                onClick={() => fileInputRef.current?.click()}
              >
                {creating ? "Uploading…" : "Take / Upload Meter Photo"}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="visually-hidden"
                onChange={handleFileChosen}
              />
            </>
          ) : (
            <p className="empty-state">No meter reading recorded yet.</p>
          )}
        </div>
      )}

      {reading && (
        <div className="meter-reading__record">
          {photoUrl && <img src={photoUrl} alt="Meter photo" className="meter-reading__photo" />}

          <div className="detail-grid">
            <div className="detail-grid__item">
              <span className="detail-grid__label">AI-detected reading</span>
              <span>
                {reading.AIDetectedReading ?? "—"}
                {reading.AIConfidence != null && ` (${Math.round(reading.AIConfidence * 100)}% confidence)`}
              </span>
            </div>
            <div className="detail-grid__item">
              <span className="detail-grid__label">Confirmed reading</span>
              <span>{reading.ConfirmedReading ?? "Not yet confirmed"}</span>
            </div>
          </div>

          {!editingConfirmation && canConfirm && (
            <button type="button" className="button button--secondary button--small" onClick={startConfirming}>
              {reading.ConfirmedReading != null ? "Correct this reading" : "Confirm reading"}
            </button>
          )}

          {!editingConfirmation && !canConfirm && reading.ConfirmedReading == null && (
            <p className="empty-state">Awaiting confirmation by the assigned inspector.</p>
          )}

          {editingConfirmation && (
            <form className="meter-reading__confirm-form" onSubmit={handleConfirmSubmit}>
              <FormField
                label="Confirmed reading"
                name="confirmedReading"
                type="number"
                value={confirmedReading}
                onChange={(event) => setConfirmedReading(event.target.value)}
                required
              />
              <FormField
                label="Meter serial number (optional)"
                name="confirmSerial"
                value={confirmSerial}
                onChange={(event) => setConfirmSerial(event.target.value)}
              />
              <label className="form-field">
                <span>Inspector notes</span>
                <textarea
                  className="form-field__input answer-textarea"
                  value={inspectorNotes}
                  onChange={(event) => setInspectorNotes(event.target.value)}
                />
              </label>
              <div className="dialog__actions">
                <button
                  type="button"
                  className="button button--secondary"
                  disabled={confirming}
                  onClick={() => setEditingConfirmation(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="button" disabled={confirming}>
                  {confirming ? "Saving…" : "Save"}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
