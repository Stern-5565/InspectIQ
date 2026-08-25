/**
 * GET /api/cleaning-inspections/{id} (the new standalone-module endpoint, PropertyId/AreaName
 * already embedded) plus a fetch of the parent Inspection (GET /api/inspections/{id}, already
 * exists) to compute `canEdit` - there's no shortcut around this second fetch: `ensure_can_edit`
 * needs the parent Inspection's own InspectorUserId/Status, confirmed by reading
 * cleaning_service.py's update_cleaning_inspection before assuming otherwise.
 *
 * ONE tier for mutation (Grade/Status/CleaningRequired/Urgent/AssignedUserId/DueDate/Notes, one
 * combined PATCH, no separate assign/status endpoints), computed exactly like
 * InspectionWizardLayout's own `canEdit`: the parent Inspection's assigned inspector, or
 * Administrator/Manager, AND the Inspection isn't Submitted. Photos use the SAME tier here -
 * confirmed by reading media_service.py: CleaningInspection's mutate check calls
 * inspection_service.ensure_can_edit, unlike RiskAssessment's unconditional "any company member"
 * shape - a genuinely different rule from the Risk Register module, not copied wholesale.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { SelectField } from "../../components/SelectField";
import { DateField } from "../../components/DateField";
import { MediaAttachments } from "../../components/MediaAttachments";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { ADMINISTRATOR, MANAGER } from "../../constants/roles";
import { CLEANING_GRADE_OPTIONS, CLEANING_INSPECTION_STATUS_OPTIONS } from "../../constants/cleaningOptions";
import { getCleaningInspectionDetail, updateCleaningInspection } from "../../services/cleaningService";
import { getInspection } from "../../services/inspectionService";
import { getProperty } from "../../services/propertyService";
import { listUsers } from "../../services/userService";
import { getErrorMessage } from "../../utilities/apiError";

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

export function CleaningInspectionDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [cleaningInspection, setCleaningInspection] = useState(null);
  const [inspection, setInspection] = useState(null);
  const [propertyName, setPropertyName] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  const [userOptions, setUserOptions] = useState([]);
  const [userNamesById, setUserNamesById] = useState({});

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
    getCleaningInspectionDetail(id)
      .then((data) => {
        setCleaningInspection(data);
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

  useEffect(() => {
    listUsers()
      .then((users) => {
        setUserOptions(users.map((u) => ({ value: String(u.UserId), label: `${u.FirstName} ${u.LastName}` })));
        setUserNamesById(Object.fromEntries(users.map((u) => [u.UserId, `${u.FirstName} ${u.LastName}`])));
      })
      .catch(() => {});
  }, []);

  if (loading) {
    return <LoadingSpinner label="Loading cleaning grade…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={load} />;
  }

  const canEdit =
    (hasAnyRole(user, [ADMINISTRATOR, MANAGER]) || user.UserId === inspection.InspectorUserId) &&
    inspection.Status !== "Submitted";

  function startEdit() {
    setForm({
      Grade: cleaningInspection.Grade,
      Status: cleaningInspection.Status,
      CleaningRequired: cleaningInspection.CleaningRequired,
      Urgent: cleaningInspection.Urgent,
      AssignedUserId: cleaningInspection.AssignedUserId ? String(cleaningInspection.AssignedUserId) : "",
      DueDate: cleaningInspection.DueDate ?? "",
      Notes: cleaningInspection.Notes ?? "",
    });
    setSaveError(null);
    setEditing(true);
  }

  function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    setSaveError(null);
    updateCleaningInspection(id, {
      Grade: form.Grade,
      Status: form.Status,
      CleaningRequired: form.CleaningRequired,
      Urgent: form.Urgent,
      AssignedUserId: form.AssignedUserId ? Number(form.AssignedUserId) : null,
      DueDate: form.DueDate || null,
      Notes: form.Notes.trim() || null,
    })
      .then((updated) => {
        setCleaningInspection((prev) => ({ ...prev, ...updated }));
        setEditing(false);
        setToast("Cleaning grade updated.");
      })
      .catch((err) => setSaveError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  return (
    <div>
      <PageHeader
        title={cleaningInspection.AreaName}
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
        <StatusBadge status={cleaningInspection.Grade} />
        <StatusBadge status={cleaningInspection.Status} />

        {!editing ? (
          <div className="detail-grid">
            <Field
              label="Property"
              value={propertyName ? <Link to={`/properties/${cleaningInspection.PropertyId}`}>{propertyName}</Link> : null}
            />
            <Field label="Linked inspection" value={<Link to={`/inspections/${cleaningInspection.InspectionId}`}>View inspection</Link>} />
            <Field label="Cleaning required" value={cleaningInspection.CleaningRequired ? "Yes" : "No"} />
            <Field label="Urgent" value={cleaningInspection.Urgent ? "Yes" : "No"} />
            <Field
              label="Assigned to"
              value={cleaningInspection.AssignedUserId ? (userNamesById[cleaningInspection.AssignedUserId] ?? "—") : "Unassigned"}
            />
            <Field label="Due date" value={cleaningInspection.DueDate} />
            <Field label="Notes" value={cleaningInspection.Notes} />
          </div>
        ) : (
          <form onSubmit={handleSave}>
            <div className="form-grid">
              <SelectField
                label="Grade"
                name="Grade"
                value={form.Grade}
                onChange={(event) => setForm((prev) => ({ ...prev, Grade: event.target.value }))}
                options={CLEANING_GRADE_OPTIONS}
                required
              />
              <SelectField
                label="Status"
                name="Status"
                value={form.Status}
                onChange={(event) => setForm((prev) => ({ ...prev, Status: event.target.value }))}
                options={CLEANING_INSPECTION_STATUS_OPTIONS}
              />
              <SelectField
                label="Assigned to"
                name="AssignedUserId"
                value={form.AssignedUserId}
                onChange={(event) => setForm((prev) => ({ ...prev, AssignedUserId: event.target.value }))}
                placeholder="Unassigned"
                options={userOptions}
              />
              <DateField
                label="Due date"
                name="DueDate"
                value={form.DueDate}
                onChange={(event) => setForm((prev) => ({ ...prev, DueDate: event.target.value }))}
              />
            </div>
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={form.CleaningRequired}
                onChange={(event) => setForm((prev) => ({ ...prev, CleaningRequired: event.target.checked }))}
              />
              Cleaning required
            </label>
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={form.Urgent}
                onChange={(event) => setForm((prev) => ({ ...prev, Urgent: event.target.checked }))}
              />
              Urgent
            </label>
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
        <MediaAttachments
          entityType="CleaningInspection"
          entityId={cleaningInspection.CleaningInspectionId}
          editable={canEdit}
        />
      </div>

      <p>
        <Link to="/cleaning-inspections">← Back to cleaning</Link>
      </p>
    </div>
  );
}
