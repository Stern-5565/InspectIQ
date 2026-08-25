/**
 * GET /api/properties/{id} plus its Units (GET /api/properties/{id}/units) and CleaningAreas
 * (GET /api/properties/{id}/cleaning-areas) - neither has standalone list/detail/form pages of
 * its own (scope's own page list names only "Properties, Property Details," not separate Units
 * or Cleaning-Areas-config modules), so both live here as nested sections instead, matching the
 * backend's own nested route shapes. CleaningAreas mirrors the Units section's exact shape
 * (inline edit row + an add form + `canManage`-gated mutation) - added alongside the standalone
 * Cleaning module's list/detail pages (grading history), which needed somewhere for the AREAS
 * themselves to be configured, since properties only ever got the 3 auto-seeded ones with no UI
 * to add the rest of scope §16's own list (Staircase, Landing, Communal Kitchen, ...) before now.
 *
 * Status vs. active/inactive are two separate concerns, same as PropertyManager's own
 * PropertyDetailPage: "Deactivate" (IsActive) is the one-way, confirmed action - there is no
 * "Reactivate," because the backend has no endpoint for it (soft-delete-only design,
 * docs/DATABASE.md). PropertyStatus itself (Active/UnderRefurbishment/...) is freely editable
 * through the regular Edit form instead - unlike PropertyManager's Properties, this module has
 * no dedicated PATCH /status endpoint, so there's no separate quick-change control for it here.
 * CleaningAreas' own IsActive is genuinely two-way (CleaningAreaUpdate allows setting it either
 * direction) - no such one-way restriction, so its toggle can reactivate too.
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
import { CAN_MANAGE_PROPERTIES, CAN_CONDUCT_INSPECTIONS } from "../../constants/roles";
import { OCCUPANCY_STATUS_OPTIONS } from "../../constants/unitOptions";
import { CLEANING_AREA_TYPE_OPTIONS } from "../../constants/cleaningOptions";
import { getProperty, deactivateProperty } from "../../services/propertyService";
import { listUnits, createUnit, updateUnit, updateUnitOccupancy } from "../../services/unitService";
import { listCleaningAreas, createCleaningArea, updateCleaningArea } from "../../services/cleaningService";
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

function CleaningAreaRow({ area, canManage, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  function startEdit() {
    setForm({ AreaName: area.AreaName, AreaType: area.AreaType });
    setEditing(true);
    setError(null);
  }

  function handleSave() {
    setSaving(true);
    setError(null);
    updateCleaningArea(area.CleaningAreaId, { AreaName: form.AreaName.trim(), AreaType: form.AreaType })
      .then((updated) => {
        onSaved(updated);
        setEditing(false);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  function handleToggleActive() {
    setSaving(true);
    setError(null);
    updateCleaningArea(area.CleaningAreaId, { IsActive: !area.IsActive })
      .then(onSaved)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  if (editing) {
    return (
      <tr>
        <td colSpan={4}>
          <div className="unit-edit-row">
            <FormField
              label="Area name"
              name="AreaName"
              value={form.AreaName}
              onChange={(e) => setForm((prev) => ({ ...prev, AreaName: e.target.value }))}
              required
            />
            <SelectField
              label="Area type"
              name="AreaType"
              value={form.AreaType}
              onChange={(e) => setForm((prev) => ({ ...prev, AreaType: e.target.value }))}
              options={CLEANING_AREA_TYPE_OPTIONS}
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
      <td>{area.AreaName}</td>
      <td>{area.AreaType}</td>
      <td>
        {canManage ? (
          <button type="button" className="button button--secondary button--small" onClick={handleToggleActive} disabled={saving}>
            {saving ? "…" : area.IsActive ? "Deactivate" : "Reactivate"}
          </button>
        ) : (
          <StatusBadge status={area.IsActive ? "Active" : "Inactive"} />
        )}
      </td>
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

function AddCleaningAreaForm({ propertyId, onCreated, onCancel }) {
  const [areaName, setAreaName] = useState("");
  const [areaType, setAreaType] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function handleSubmit(event) {
    event.preventDefault();
    if (!areaName.trim() || !areaType) {
      setError("Area name and type are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    createCleaningArea(propertyId, { areaName: areaName.trim(), areaType })
      .then((area) => {
        onCreated(area);
        setAreaName("");
        setAreaType("");
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  return (
    <form className="unit-add-form" onSubmit={handleSubmit}>
      <FormField label="Area name" name="areaName" value={areaName} onChange={(e) => setAreaName(e.target.value)} required />
      <SelectField
        label="Area type"
        name="areaType"
        value={areaType}
        onChange={(e) => setAreaType(e.target.value)}
        placeholder="Choose a type"
        options={CLEANING_AREA_TYPE_OPTIONS}
        required
      />
      {error && <ErrorMessage message={error} />}
      <div className="unit-add-form__actions">
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Adding…" : "Add area"}
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
  const canConductInspections = hasAnyRole(user, CAN_CONDUCT_INSPECTIONS);
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

  const [areas, setAreas] = useState([]);
  const [areasLoading, setAreasLoading] = useState(true);
  const [areasError, setAreasError] = useState(null);
  const [addingArea, setAddingArea] = useState(false);
  const [includeInactiveAreas, setIncludeInactiveAreas] = useState(false);

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

  const loadAreas = useCallback(() => {
    setAreasLoading(true);
    setAreasError(null);
    listCleaningAreas(id, { includeInactive: includeInactiveAreas })
      .then(setAreas)
      .catch((err) => setAreasError(getErrorMessage(err)))
      .finally(() => setAreasLoading(false));
  }, [id, includeInactiveAreas]);

  useEffect(() => {
    loadProperty();
    loadUnits();
  }, [loadProperty, loadUnits]);

  useEffect(() => {
    loadAreas();
  }, [loadAreas]);

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

  function replaceArea(updated) {
    setAreas((prev) => {
      const next = prev.map((a) => (a.CleaningAreaId === updated.CleaningAreaId ? updated : a));
      // A just-deactivated area should disappear immediately when "include deactivated" is off,
      // the same way Properties' own list hides a deactivated one without a manual refresh.
      return includeInactiveAreas ? next : next.filter((a) => a.IsActive);
    });
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
          property.IsActive && (
            <>
              {canConductInspections && (
                <Link to={`/inspections/new?propertyId=${id}`} className="button">
                  Start Inspection
                </Link>
              )}
              {canManage && (
                <Link to={`/properties/${id}/edit`} className="button button--secondary">
                  Edit
                </Link>
              )}
            </>
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

      <div className="detail-card">
        <div className="detail-card__header">
          <h2>Cleaning Areas</h2>
          {canManage && !addingArea && (
            <button type="button" className="button button--secondary" onClick={() => setAddingArea(true)}>
              + Add area
            </button>
          )}
        </div>

        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={includeInactiveAreas}
            onChange={(event) => setIncludeInactiveAreas(event.target.checked)}
          />
          Include deactivated
        </label>

        {addingArea && (
          <AddCleaningAreaForm
            propertyId={id}
            onCreated={(area) => {
              setAreas((prev) => [...prev, area]);
              setAddingArea(false);
            }}
            onCancel={() => setAddingArea(false)}
          />
        )}

        {areasLoading ? (
          <LoadingSpinner label="Loading cleaning areas…" />
        ) : areasError ? (
          <ErrorMessage message={areasError} onRetry={loadAreas} />
        ) : areas.length === 0 ? (
          <EmptyState message="No cleaning areas configured for this property yet." />
        ) : (
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Area</th>
                  <th scope="col">Type</th>
                  <th scope="col">Status</th>
                  <th scope="col"></th>
                </tr>
              </thead>
              <tbody>
                {areas.map((area) => (
                  <CleaningAreaRow key={area.CleaningAreaId} area={area} canManage={canManage} onSaved={replaceArea} />
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
