/**
 * GET /api/properties/{id} plus its Units (GET /api/properties/{id}/units) - Units have no
 * standalone list/detail/form pages of their own (scope's own page list names only
 * "Properties, Property Details," not a separate Units module), so unit management lives here
 * as a nested section instead, matching the backend's own nested route shape
 * (/api/properties/{id}/units, /api/units/{id}).
 *
 * Status vs. active/inactive are two separate concerns, same as PropertyManager's own
 * PropertyDetailPage: "Deactivate" (IsActive) is the one-way, confirmed action - there is no
 * "Reactivate," because the backend has no endpoint for it (soft-delete-only design,
 * docs/DATABASE.md). PropertyStatus itself (Active/UnderRefurbishment/...) is freely editable
 * through the regular Edit form instead - unlike PropertyManager's Properties, this module has
 * no dedicated PATCH /status endpoint, so there's no separate quick-change control for it here.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { SelectField } from "../../components/SelectField";
import { FormField } from "../../components/FormField";
import { ConfirmationDialog } from "../../components/ConfirmationDialog";
import { Toast } from "../../components/Toast";
import { EmptyState } from "../../components/EmptyState";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_PROPERTIES } from "../../constants/roles";
import { OCCUPANCY_STATUS_OPTIONS } from "../../constants/unitOptions";
import { getProperty, deactivateProperty } from "../../services/propertyService";
import { listUnits, createUnit, updateUnit, updateUnitOccupancy } from "../../services/unitService";
import { getErrorMessage } from "../../utilities/apiError";

function Field({ label, value }) {
  return (
    <div className="detail-grid__item">
      <span className="detail-grid__label">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}

function UnitRow({ unit, canManage, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [occupancy, setOccupancy] = useState(unit.OccupancyStatus);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  function startEdit() {
    setForm({
      UnitNumber: unit.UnitNumber,
      Floor: unit.Floor ?? "",
      TenantOccupierName: unit.TenantOccupierName ?? "",
      Notes: unit.Notes ?? "",
    });
    setEditing(true);
    setError(null);
  }

  function handleSave() {
    setSaving(true);
    setError(null);
    updateUnit(unit.UnitId, {
      UnitNumber: form.UnitNumber.trim(),
      Floor: form.Floor.trim() === "" ? null : form.Floor.trim(),
      TenantOccupierName: form.TenantOccupierName.trim() === "" ? null : form.TenantOccupierName.trim(),
      Notes: form.Notes.trim() === "" ? null : form.Notes.trim(),
    })
      .then((updated) => {
        onSaved(updated);
        setEditing(false);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  function handleOccupancyUpdate() {
    setSaving(true);
    setError(null);
    updateUnitOccupancy(unit.UnitId, occupancy)
      .then(onSaved)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  if (editing) {
    return (
      <tr>
        <td colSpan={5}>
          <div className="unit-edit-row">
            <FormField
              label="Unit number"
              name="UnitNumber"
              value={form.UnitNumber}
              onChange={(e) => setForm((prev) => ({ ...prev, UnitNumber: e.target.value }))}
              required
            />
            <FormField
              label="Floor"
              name="Floor"
              value={form.Floor}
              onChange={(e) => setForm((prev) => ({ ...prev, Floor: e.target.value }))}
            />
            <FormField
              label="Tenant / occupier name"
              name="TenantOccupierName"
              value={form.TenantOccupierName}
              onChange={(e) => setForm((prev) => ({ ...prev, TenantOccupierName: e.target.value }))}
            />
            <FormField
              label="Notes"
              name="Notes"
              value={form.Notes}
              onChange={(e) => setForm((prev) => ({ ...prev, Notes: e.target.value }))}
            />
            {error && <ErrorMessage message={error} />}
            <div className="unit-edit-row__actions">
              <button type="button" className="button" onClick={handleSave} disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </button>
              <button type="button" className="button button--secondary" onClick={() => setEditing(false)}>
                Cancel
              </button>
            </div>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td>{unit.UnitNumber}</td>
      <td>{unit.Floor ?? "—"}</td>
      <td>
        {canManage ? (
          <div className="unit-occupancy-control">
            <SelectField
              label=""
              name={`occupancy-${unit.UnitId}`}
              value={occupancy}
              onChange={(e) => setOccupancy(e.target.value)}
              options={OCCUPANCY_STATUS_OPTIONS}
            />
            <button
              type="button"
              className="button button--secondary button--small"
              onClick={handleOccupancyUpdate}
              disabled={saving || occupancy === unit.OccupancyStatus}
            >
              {saving ? "…" : "Update"}
            </button>
          </div>
        ) : (
          <StatusBadge status={unit.OccupancyStatus} />
        )}
      </td>
      <td>{unit.TenantOccupierName ?? "—"}</td>
      <td>
        {canManage && (
          <button type="button" className="button button--secondary button--small" onClick={startEdit}>
            Edit
          </button>
        )}
        {error && <ErrorMessage message={error} />}
      </td>
    </tr>
  );
}

function AddUnitForm({ propertyId, onCreated, onCancel }) {
  const [unitNumber, setUnitNumber] = useState("");
  const [floor, setFloor] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function handleSubmit(event) {
    event.preventDefault();
    if (!unitNumber.trim()) {
      setError("Unit number is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    createUnit(propertyId, {
      UnitNumber: unitNumber.trim(),
      Floor: floor.trim() === "" ? null : floor.trim(),
    })
      .then((unit) => {
        onCreated(unit);
        setUnitNumber("");
        setFloor("");
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  return (
    <form className="unit-add-form" onSubmit={handleSubmit}>
      <FormField label="Unit number" name="unitNumber" value={unitNumber} onChange={(e) => setUnitNumber(e.target.value)} required />
      <FormField label="Floor" name="floor" value={floor} onChange={(e) => setFloor(e.target.value)} />
      {error && <ErrorMessage message={error} />}
      <div className="unit-add-form__actions">
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Adding…" : "Add unit"}
        </button>
        <button type="button" className="button button--secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export function PropertyDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_PROPERTIES);
  const navigate = useNavigate();
  const location = useLocation();

  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deactivateSubmitting, setDeactivateSubmitting] = useState(false);
  const [deactivateError, setDeactivateError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);
  const [showAlarmCode, setShowAlarmCode] = useState(false);

  const [units, setUnits] = useState([]);
  const [unitsLoading, setUnitsLoading] = useState(true);
  const [unitsError, setUnitsError] = useState(null);
  const [addingUnit, setAddingUnit] = useState(false);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadProperty = useCallback(() => {
    setLoading(true);
    setError(null);
    getProperty(id)
      .then(setProperty)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  const loadUnits = useCallback(() => {
    setUnitsLoading(true);
    setUnitsError(null);
    listUnits(id, { pageSize: 100 })
      .then((data) => setUnits(data.items))
      .catch((err) => setUnitsError(getErrorMessage(err)))
      .finally(() => setUnitsLoading(false));
  }, [id]);

  useEffect(() => {
    loadProperty();
    loadUnits();
  }, [loadProperty, loadUnits]);

  function handleConfirmDeactivate() {
    setDeactivateSubmitting(true);
    setDeactivateError(null);
    deactivateProperty(id)
      .then((updated) => {
        setProperty(updated);
        setToast("Property deactivated.");
      })
      .catch((err) => setDeactivateError(getErrorMessage(err)))
      .finally(() => {
        setDialogOpen(false);
        setDeactivateSubmitting(false);
      });
  }

  function replaceUnit(updated) {
    setUnits((prev) => prev.map((u) => (u.UnitId === updated.UnitId ? updated : u)));
  }

  if (loading) {
    return <LoadingSpinner label="Loading property…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadProperty} />;
  }

  return (
    <div>
      <PageHeader
        title={property.PropertyName}
        actions={
          canManage &&
          property.IsActive && (
            <Link to={`/properties/${id}/edit`} className="button button--secondary">
              Edit
            </Link>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="detail-card">
        <StatusBadge status={property.PropertyStatus} />
        {!property.IsActive && <StatusBadge status="Inactive" />}

        <div className="detail-grid">
          <Field
            label="Address"
            value={[property.AddressLine1, property.AddressLine2, property.City, property.Postcode]
              .filter(Boolean)
              .join(", ")}
          />
          <Field label="Type" value={property.PropertyType} />
          <Field label="Number of units (declared)" value={property.NumberOfUnits} />
          <Field label="Inspection frequency" value={property.InspectionFrequency} />
          <Field label="Last inspection date" value={property.LastInspectionDate} />
          <Field label="Next inspection due" value={property.NextInspectionDue} />
          <Field label="Main contact" value={property.MainContactName} />
          <Field label="Contact phone" value={property.MainContactPhone} />
          <Field label="Contact email" value={property.MainContactEmail} />
          <Field label="Key location" value={property.KeyLocation} />
          <Field
            label="Alarm / access code"
            value={
              property.AlarmAccessCode ? (
                <span className="masked-value">
                  {showAlarmCode ? property.AlarmAccessCode : "••••••"}{" "}
                  <button
                    type="button"
                    className="button button--secondary button--small"
                    onClick={() => setShowAlarmCode((prev) => !prev)}
                  >
                    {showAlarmCode ? "Hide" : "Show"}
                  </button>
                </span>
              ) : null
            }
          />
          <Field label="Access instructions" value={property.AccessInstructions} />
          <Field label="Notes" value={property.GeneralNotes} />
        </div>

        {canManage && property.IsActive && (
          <>
            <div className="detail-card__actions">
              <button type="button" className="button button--danger" onClick={() => setDialogOpen(true)}>
                Deactivate
              </button>
            </div>
            {deactivateError && <ErrorMessage message={deactivateError} />}
          </>
        )}
      </div>

      <div className="detail-card">
        <div className="detail-card__header">
          <h2>Units</h2>
          {canManage && !addingUnit && (
            <button type="button" className="button button--secondary" onClick={() => setAddingUnit(true)}>
              + Add unit
            </button>
          )}
        </div>

        {addingUnit && (
          <AddUnitForm
            propertyId={id}
            onCreated={(unit) => {
              setUnits((prev) => [...prev, unit]);
              setAddingUnit(false);
            }}
            onCancel={() => setAddingUnit(false)}
          />
        )}

        {unitsLoading ? (
          <LoadingSpinner label="Loading units…" />
        ) : unitsError ? (
          <ErrorMessage message={unitsError} onRetry={loadUnits} />
        ) : units.length === 0 ? (
          <EmptyState message="No units recorded for this property yet." />
        ) : (
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Unit</th>
                  <th scope="col">Floor</th>
                  <th scope="col">Occupancy</th>
                  <th scope="col">Tenant / occupier</th>
                  <th scope="col"></th>
                </tr>
              </thead>
              <tbody>
                {units.map((unit) => (
                  <UnitRow key={unit.UnitId} unit={unit} canManage={canManage} onSaved={replaceUnit} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ConfirmationDialog
        open={dialogOpen}
        title="Deactivate this property?"
        message="This hides it from the default property list. It cannot currently be undone from the app."
        confirmLabel="Deactivate"
        danger
        confirmDisabled={deactivateSubmitting}
        onCancel={() => setDialogOpen(false)}
        onConfirm={handleConfirmDeactivate}
      />

      <p>
        <Link to="/properties">← Back to properties</Link>
      </p>
    </div>
  );
}
