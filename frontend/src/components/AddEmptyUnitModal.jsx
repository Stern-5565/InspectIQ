/**
 * The "Add Empty Unit" gateway quick-action (scope §7), available throughout the inspection -
 * not tied to one question, since the seeded template's "Vacant Units" section only asks the
 * inspector to CONFIRM this was recorded elsewhere (database/seed/12_SeedInspectionTemplate.sql's
 * own file header, the discovery that shaped this whole sub-phase plan). Fields match scope §7's
 * list exactly (Unit, Date identified vacant, Condition, 11 Yes/No checks, Notes) - Photos/
 * Videos and the "creatable maintenance issue from any of these questions" link are real scope
 * items but deliberately NOT here, the same "don't show it until it's real" call Sub-phase A
 * made for this page's other buttons; both are natural follow-on refinements once this action
 * itself is proven, not something this sub-phase's own plan (docs/AI_HANDOFF.md) asked for.
 *
 * Gated by the caller on `editable`, NOT `canRaiseIssues` - confirmed by reading
 * vacant_unit_service.create_vacant_unit_inspection first: it calls
 * inspection_service.ensure_can_edit, the same assigned-inspector-or-Admin/Manager rule
 * answering questions uses, unlike Sub-phase C/D's create actions (which have no such check).
 * Every "gateway" create action needed this same independent check - it happened to land on
 * `editable` both times here, not by assumption.
 */
import { useEffect, useState } from "react";
import { ErrorMessage } from "./ErrorMessage";
import { FormField } from "./FormField";
import { DateField } from "./DateField";
import { Modal } from "./Modal";
import { SelectField } from "./SelectField";
import { listUnits } from "../services/unitService";
import { createVacantUnitInspection } from "../services/vacantUnitService";
import { getErrorMessage } from "../utilities/apiError";

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

const INITIAL_CHECKS = Object.fromEntries(CHECKS.map(([field]) => [field, null]));

export function AddEmptyUnitModal({ open, inspectionId, propertyId, onClose, onCreated }) {
  const [units, setUnits] = useState([]);
  const [loadingUnits, setLoadingUnits] = useState(true);
  const [unitId, setUnitId] = useState("");
  const [dateIdentifiedVacant, setDateIdentifiedVacant] = useState("");
  const [condition, setCondition] = useState("");
  const [checks, setChecks] = useState(INITIAL_CHECKS);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setUnitId("");
    setDateIdentifiedVacant("");
    setCondition("");
    setChecks(INITIAL_CHECKS);
    setNotes("");
    setError(null);
    setLoadingUnits(true);
    listUnits(propertyId, { pageSize: 100 })
      .then((page) => setUnits(page.items))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoadingUnits(false));
  }, [open, propertyId]);

  function handleClose() {
    if (!submitting) {
      onClose();
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!unitId) {
      setError("Choose a unit.");
      return;
    }
    setSubmitting(true);
    setError(null);
    createVacantUnitInspection(inspectionId, {
      UnitId: Number(unitId),
      DateIdentifiedVacant: dateIdentifiedVacant || undefined,
      Condition: condition.trim() || undefined,
      Notes: notes.trim() || undefined,
      ...checks,
    })
      .then(onCreated)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  return (
    <Modal open={open} title="Add Empty Unit" onClose={handleClose}>
      <form onSubmit={handleSubmit}>
        {error && <ErrorMessage message={error} />}

        <SelectField
          label="Unit"
          name="unitId"
          value={unitId}
          onChange={(event) => setUnitId(event.target.value)}
          options={units.map((u) => ({
            value: String(u.UnitId),
            label: `${u.UnitNumber} (${u.OccupancyStatus})`,
          }))}
          placeholder={loadingUnits ? "Loading units…" : "Choose a unit"}
          required
        />
        <DateField
          label="Date identified vacant"
          name="dateIdentifiedVacant"
          value={dateIdentifiedVacant}
          onChange={(event) => setDateIdentifiedVacant(event.target.value)}
        />
        <FormField label="Condition" name="condition" value={condition} onChange={(event) => setCondition(event.target.value)} />

        {CHECKS.map(([field, label]) => (
          <TriStateRow
            key={field}
            label={label}
            value={checks[field]}
            onChange={(value) => setChecks((prev) => ({ ...prev, [field]: value }))}
          />
        ))}

        <label className="form-field">
          <span>Notes</span>
          <textarea className="form-field__input answer-textarea" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>

        <div className="dialog__actions">
          <button type="button" className="button button--secondary" onClick={handleClose} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" className="button" disabled={submitting || loadingUnits}>
            {submitting ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
