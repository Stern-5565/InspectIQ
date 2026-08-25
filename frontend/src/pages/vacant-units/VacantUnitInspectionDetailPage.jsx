/**
 * GET /api/vacant-unit-inspections/{id} (the new standalone-module endpoint, PropertyId/
 * UnitNumber already embedded) plus a fetch of the parent Inspection (GET /api/inspections/{id},
 * already exists) to compute `canEdit` - same two-fetch shape as CleaningInspectionDetailPage,
 * confirmed by reading vacant_unit_service.py's update_vacant_unit_inspection: ensure_can_edit
 * needs the parent Inspection's own InspectorUserId/Status.
 *
 * ONE tier for mutation (every field in one combined PATCH, no separate assign/status endpoints
 * - the record has no Status/AssignedUserId at all, app/models/vacant_unit_inspection.py),
 * computed exactly like CleaningInspectionDetailPage's own `canEdit`: the parent Inspection's
 * assigned inspector, or Administrator/Manager, AND the Inspection isn't Submitted. Photos use
 * the SAME tier - confirmed by reading media_service.py: VacantUnitInspection's mutate check
 * also calls inspection_service.ensure_can_edit, the same as CleaningInspection.
 *
 * The 11 tri-state Yes/No/Not-checked checks reuse the same three-button pattern as
 * components/AddEmptyUnitModal.jsx's own TriStateRow (kept local here, not extracted - the two
 * usages differ enough in surrounding layout that a shared component would need its own prop
 * surface anyway).
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { DateField } from "../../components/DateField";
import { FormField } from "../../components/FormField";
import { MediaAttachments } from "../../components/MediaAttachments";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { ADMINISTRATOR, MANAGER } from "../../constants/roles";
import { getVacantUnitInspectionDetail, updateVacantUnitInspection } from "../../services/vacantUnitService";
import { getInspection } from "../../services/inspectionService";
import { getProperty } from "../../services/propertyService";
import { getErrorMessage } from "../../utilities/apiError";

const CHECKS = [
  ["ElectricityOn", "Electricity on?"],
  ["WaterOn", "Water on?"],
  ["HeatingWorking", "Heating working?"],
  ["WindowsSecure", "Windows secure?"],
  ["DoorsSecure", "Doors secure?"],
  ["SignsOfLeaks", "Signs of leaks?"],
  ["SignsOfDamp", "Signs of damp?"],
  ["SignsOfPests", "Signs of pests?"],
  ["CleaningRequired", "Cleaning required?"],
  ["WasteItemsLeftBehind", "Waste / items left behind?"],
  ["MaintenanceRequired", "Maintenance required?"],
];

function triStateLabel(value) {
  if (value === true) return "Yes";
  if (value === false) return "No";
  return "Not checked";
}

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

function TriStateRow({ label, value, onChange }) {
  return (
    <div className="form-field">
      <span>{label}</span>
      <div className="answer-buttons">
        {[
          ["Yes", true],
          ["No", false],
          ["Not checked", null],
        ].map(([text, optionValue]) => (
          <button
            key={text}
            type="button"
            className={`answer-button${value === optionValue ? " answer-button--selected" : ""}`}
            onClick={() => onChange(optionValue)}
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

export function VacantUnitInspectionDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [record, setRecord] = useState(null);
  const [inspection, setInspection] = useState(null);
  const [propertyName, setPropertyName] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getVacantUnitInspectionDetail(id)
      .then((data) => {
        setRecord(data);
        return Promise.all([getInspection(data.InspectionId), getProperty(data.PropertyId)]);
      })
      .then(([insp, property]) => {
        setInspection(insp);
        setPropertyName(property.PropertyName);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <LoadingSpinner label="Loading vacant-unit finding…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={load} />;
  }

  const canEdit =
    (hasAnyRole(user, [ADMINISTRATOR, MANAGER]) || user.UserId === inspection.InspectorUserId) &&
    inspection.Status !== "Submitted";

  function startEdit() {
    setForm({
      DateIdentifiedVacant: record.DateIdentifiedVacant ?? "",
      Condition: record.Condition ?? "",
      Notes: record.Notes ?? "",
      ...Object.fromEntries(CHECKS.map(([field]) => [field, record[field]])),
    });
    setSaveError(null);
    setEditing(true);
  }

  function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    setSaveError(null);
    updateVacantUnitInspection(id, {
      DateIdentifiedVacant: form.DateIdentifiedVacant || null,
      Condition: form.Condition.trim() || null,
      Notes: form.Notes.trim() || null,
      ...Object.fromEntries(CHECKS.map(([field]) => [field, form[field]])),
    })
      .then((updated) => {
        setRecord((prev) => ({ ...prev, ...updated }));
        setEditing(false);
        setToast("Vacant-unit finding updated.");
      })
      .catch((err) => setSaveError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  return (
    <div>
      <PageHeader
        title={`Unit ${record.UnitNumber}`}
        actions={
          canEdit &&
          !editing && (
            <button type="button" className="button button--secondary" onClick={startEdit}>
              Edit
            </button>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="detail-card">
        {!editing ? (
          <div className="detail-grid">
            <Field
              label="Property"
              value={propertyName ? <Link to={`/properties/${record.PropertyId}`}>{propertyName}</Link> : null}
            />
            <Field label="Linked inspection" value={<Link to={`/inspections/${record.InspectionId}`}>View inspection</Link>} />
            <Field label="Date identified vacant" value={record.DateIdentifiedVacant} />
            <Field label="Condition" value={record.Condition} />
            {CHECKS.map(([field, label]) => (
              <Field key={field} label={label} value={triStateLabel(record[field])} />
            ))}
            <Field label="Notes" value={record.Notes} />
          </div>
        ) : (
          <form onSubmit={handleSave}>
            <div className="form-grid">
              <DateField
                label="Date identified vacant"
                name="DateIdentifiedVacant"
                value={form.DateIdentifiedVacant}
                onChange={(event) => setForm((prev) => ({ ...prev, DateIdentifiedVacant: event.target.value }))}
              />
              <FormField
                label="Condition"
                name="Condition"
                value={form.Condition}
                onChange={(event) => setForm((prev) => ({ ...prev, Condition: event.target.value }))}
              />
            </div>

            {CHECKS.map(([field, label]) => (
              <TriStateRow
                key={field}
                label={label}
                value={form[field]}
                onChange={(value) => setForm((prev) => ({ ...prev, [field]: value }))}
              />
            ))}

            <label className="form-field">
              <span>Notes</span>
              <textarea
                className="form-field__input answer-textarea"
                value={form.Notes}
                onChange={(event) => setForm((prev) => ({ ...prev, Notes: event.target.value }))}
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

      <div className="detail-card">
        <MediaAttachments entityType="VacantUnitInspection" entityId={record.VacantUnitInspectionId} editable={canEdit} />
      </div>

      <p>
        <Link to="/vacant-unit-inspections">← Back to vacant units</Link>
      </p>
    </div>
  );
}
