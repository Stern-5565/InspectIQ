/**
 * GET /api/meter-readings/{id} (PropertyName/InspectionId already embedded,
 * MeterReadingSummaryResponse) plus, when InspectionId is present, a fetch of the parent
 * Inspection (GET /api/inspections/{id}, already exists) to compute `canConfirm` - the SAME
 * genuinely hybrid tier `MeterReadingControl.jsx` already established for the wizard's Question
 * screen, re-derived here rather than assumed, since this page has no InspectionWizardLayout to
 * hand it a ready-made `editable` flag:
 *   - InspectionId present -> the parent Inspection's assigned inspector, or Administrator/
 *     Manager (mirrors `inspection_service.ensure_can_edit`, the same rule
 *     Cleaning/VacantUnitInspectionDetailPage compute).
 *   - InspectionId absent (a standalone reading) -> Administrator/Manager only.
 * Confirmed by reading `meter_reading_service.py`'s `ensure_can_edit_reading`/
 * `update_meter_reading` before writing this: unlike Cleaning/VacantUnit, there is NO
 * `Inspection.Status == "Submitted"` lock on confirming a reading, so `canConfirm` deliberately
 * does not gate on submission the way those two pages' `canEdit` does.
 *
 * The photo is fetched as an authenticated blob and rendered via `URL.createObjectURL`, the same
 * pattern `MeterReadingControl.jsx` already uses (`PhotoMediaFileId` is a direct 1:1 FK, not the
 * generic `MediaAttachments` polymorphic list every other module's detail page uses).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { FormField } from "../../components/FormField";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { ADMINISTRATOR, MANAGER } from "../../constants/roles";
import { getMeterReading, updateMeterReading } from "../../services/meterReadingService";
import { getInspection } from "../../services/inspectionService";
import { downloadMediaBlob } from "../../services/mediaService";
import { getErrorMessage } from "../../utilities/apiError";

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

export function MeterReadingDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [reading, setReading] = useState(null);
  const [inspection, setInspection] = useState(null);
  const [photoUrl, setPhotoUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const photoUrlRef = useRef(null);
  photoUrlRef.current = photoUrl;

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    setInspection(null);
    if (photoUrlRef.current) {
      URL.revokeObjectURL(photoUrlRef.current);
      setPhotoUrl(null);
    }
    getMeterReading(id)
      .then((data) => {
        setReading(data);
        return Promise.all([
          data.InspectionId ? getInspection(data.InspectionId) : Promise.resolve(null),
          data.PhotoMediaFileId ? downloadMediaBlob(data.PhotoMediaFileId) : Promise.resolve(null),
        ]);
      })
      .then(([insp, blob]) => {
        setInspection(insp);
        if (blob) setPhotoUrl(URL.createObjectURL(blob));
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    load();
    return () => {
      if (photoUrlRef.current) {
        URL.revokeObjectURL(photoUrlRef.current);
      }
    };
  }, [load]);

  if (loading) {
    return <LoadingSpinner label="Loading meter reading…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={load} />;
  }

  const canConfirm = reading.InspectionId
    ? hasAnyRole(user, [ADMINISTRATOR, MANAGER]) || user.UserId === inspection?.InspectorUserId
    : hasAnyRole(user, [ADMINISTRATOR, MANAGER]);

  function startEdit() {
    setForm({
      ConfirmedReading: String(reading.ConfirmedReading ?? reading.AIDetectedReading ?? ""),
      MeterSerialNumber: reading.MeterSerialNumber ?? "",
      InspectorNotes: reading.InspectorNotes ?? "",
    });
    setSaveError(null);
    setEditing(true);
  }

  function handleSave(event) {
    event.preventDefault();
    if (!form.ConfirmedReading.trim()) {
      setSaveError("Enter the meter reading.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    updateMeterReading(id, {
      confirmedReading: Number(form.ConfirmedReading),
      meterSerialNumber: form.MeterSerialNumber.trim() || undefined,
      inspectorNotes: form.InspectorNotes.trim() || undefined,
    })
      .then((updated) => {
        setReading((prev) => ({ ...prev, ...updated }));
        setEditing(false);
        setToast("Meter reading updated.");
      })
      .catch((err) => setSaveError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  return (
    <div>
      <PageHeader
        title={`${reading.MeterType} Meter`}
        actions={
          canConfirm &&
          !editing && (
            <button type="button" className="button button--secondary" onClick={startEdit}>
              {reading.ConfirmedReading != null ? "Correct reading" : "Confirm reading"}
            </button>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="detail-card">
        <StatusBadge status={reading.ConfirmedReading != null ? "Confirmed" : "Unconfirmed"} />

        {photoUrl && <img src={photoUrl} alt="Meter photo" className="meter-reading__photo" />}

        {!editing ? (
          <div className="detail-grid">
            <Field label="Property" value={<Link to={`/properties/${reading.PropertyId}`}>{reading.PropertyName}</Link>} />
            {reading.InspectionId && (
              <Field label="Linked inspection" value={<Link to={`/inspections/${reading.InspectionId}`}>View inspection</Link>} />
            )}
            <Field label="Reading date" value={new Date(reading.ReadingDateTime).toLocaleString()} />
            <Field
              label="AI-detected reading"
              value={
                reading.AIDetectedReading != null
                  ? `${reading.AIDetectedReading}${reading.AIConfidence != null ? ` (${Math.round(reading.AIConfidence * 100)}% confidence)` : ""}`
                  : null
              }
            />
            <Field label="Confirmed reading" value={reading.ConfirmedReading} />
            <Field label="Meter serial number" value={reading.MeterSerialNumber} />
            <Field label="Inspector notes" value={reading.InspectorNotes} />
          </div>
        ) : (
          <form onSubmit={handleSave}>
            <div className="form-grid">
              <FormField
                label="Confirmed reading"
                name="ConfirmedReading"
                type="number"
                value={form.ConfirmedReading}
                onChange={(event) => setForm((prev) => ({ ...prev, ConfirmedReading: event.target.value }))}
                required
              />
              <FormField
                label="Meter serial number"
                name="MeterSerialNumber"
                value={form.MeterSerialNumber}
                onChange={(event) => setForm((prev) => ({ ...prev, MeterSerialNumber: event.target.value }))}
              />
            </div>
            <label className="form-field">
              <span>Inspector notes</span>
              <textarea
                className="form-field__input answer-textarea"
                value={form.InspectorNotes}
                onChange={(event) => setForm((prev) => ({ ...prev, InspectorNotes: event.target.value }))}
              />
            </label>

            {saveError && <ErrorMessage message={saveError} />}

            <div className="form-card__actions">
              <button type="submit" className="button" disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </button>
              <button type="button" className="button button--secondary" onClick={() => setEditing(false)} disabled={saving}>
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

      <p>
        <Link to="/meter-readings">← Back to meter readings</Link>
      </p>
    </div>
  );
}
