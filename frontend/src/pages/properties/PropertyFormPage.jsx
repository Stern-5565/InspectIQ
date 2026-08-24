/**
 * Shared create/edit form - POST/PATCH /api/properties (propertyService.js). Client-side
 * validation covers only what the schema itself requires (app/schemas/property.py); anything
 * server-specific (duplicate handling, etc.) is left to the server's own error message.
 *
 * AlarmAccessCode uses type="password" with a show/hide toggle, and the detail page masks it
 * by default - the backend stores it as plaintext (docs/DATABASE.md §10.4, a documented, not
 * yet mitigated risk), so this doesn't fix that, but there's no reason for the frontend to
 * additionally leave it sitting in plain view on screen when it doesn't have to.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SelectField } from "../../components/SelectField";
import { DateField } from "../../components/DateField";
import {
  PROPERTY_TYPE_OPTIONS,
  PROPERTY_STATUS_OPTIONS,
  INSPECTION_FREQUENCY_OPTIONS,
} from "../../constants/propertyOptions";
import { getProperty, createProperty, updateProperty } from "../../services/propertyService";
import { getErrorMessage } from "../../utilities/apiError";

const BLANK_FORM = {
  PropertyName: "",
  AddressLine1: "",
  AddressLine2: "",
  City: "",
  Postcode: "",
  PropertyType: "",
  PropertyStatus: "Active",
  NumberOfUnits: "",
  MainContactName: "",
  MainContactPhone: "",
  MainContactEmail: "",
  AccessInstructions: "",
  KeyLocation: "",
  AlarmAccessCode: "",
  GeneralNotes: "",
  InspectionFrequency: "",
  LastInspectionDate: "",
  NextInspectionDue: "",
};

function validate(form) {
  const errors = {};
  if (!form.PropertyName.trim()) errors.PropertyName = "Property name is required.";
  if (!form.AddressLine1.trim()) errors.AddressLine1 = "Address line 1 is required.";
  if (!form.Postcode.trim()) errors.Postcode = "Postcode is required.";
  if (!form.PropertyType) errors.PropertyType = "Choose a property type.";
  if (!form.InspectionFrequency) errors.InspectionFrequency = "Choose an inspection frequency.";
  if (form.NumberOfUnits !== "" && (Number(form.NumberOfUnits) < 0 || !Number.isInteger(Number(form.NumberOfUnits)))) {
    errors.NumberOfUnits = "Enter a whole number of 0 or more.";
  }
  return errors;
}

function toPayload(form) {
  const emptyToNull = (value) => (value.trim() === "" ? null : value.trim());
  return {
    PropertyName: form.PropertyName.trim(),
    AddressLine1: form.AddressLine1.trim(),
    AddressLine2: emptyToNull(form.AddressLine2),
    City: emptyToNull(form.City),
    Postcode: form.Postcode.trim(),
    PropertyType: form.PropertyType,
    PropertyStatus: form.PropertyStatus,
    NumberOfUnits: form.NumberOfUnits === "" ? null : Number(form.NumberOfUnits),
    MainContactName: emptyToNull(form.MainContactName),
    MainContactPhone: emptyToNull(form.MainContactPhone),
    MainContactEmail: emptyToNull(form.MainContactEmail),
    AccessInstructions: emptyToNull(form.AccessInstructions),
    KeyLocation: emptyToNull(form.KeyLocation),
    AlarmAccessCode: emptyToNull(form.AlarmAccessCode),
    GeneralNotes: emptyToNull(form.GeneralNotes),
    InspectionFrequency: form.InspectionFrequency,
    LastInspectionDate: emptyToNull(form.LastInspectionDate),
    NextInspectionDue: emptyToNull(form.NextInspectionDue),
  };
}

export function PropertyFormPage() {
  const { id } = useParams();
  const isEdit = id !== undefined;
  const navigate = useNavigate();

  const [form, setForm] = useState(BLANK_FORM);
  const [loading, setLoading] = useState(isEdit);
  const [loadError, setLoadError] = useState(null);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showAlarmCode, setShowAlarmCode] = useState(false);

  useEffect(() => {
    if (!isEdit) {
      return;
    }
    getProperty(id)
      .then((property) =>
        setForm({
          PropertyName: property.PropertyName,
          AddressLine1: property.AddressLine1,
          AddressLine2: property.AddressLine2 ?? "",
          City: property.City ?? "",
          Postcode: property.Postcode,
          PropertyType: property.PropertyType,
          PropertyStatus: property.PropertyStatus,
          NumberOfUnits: property.NumberOfUnits === null ? "" : String(property.NumberOfUnits),
          MainContactName: property.MainContactName ?? "",
          MainContactPhone: property.MainContactPhone ?? "",
          MainContactEmail: property.MainContactEmail ?? "",
          AccessInstructions: property.AccessInstructions ?? "",
          KeyLocation: property.KeyLocation ?? "",
          AlarmAccessCode: property.AlarmAccessCode ?? "",
          GeneralNotes: property.GeneralNotes ?? "",
          InspectionFrequency: property.InspectionFrequency,
          LastInspectionDate: property.LastInspectionDate ?? "",
          NextInspectionDue: property.NextInspectionDue ?? "",
        }),
      )
      .catch((err) => setLoadError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id, isEdit]);

  function updateField(field) {
    return (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    const validationErrors = validate(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    const payload = toPayload(form);
    const request = isEdit ? updateProperty(id, payload) : createProperty(payload);
    request
      .then((property) => {
        navigate(`/properties/${property.PropertyId}`, {
          state: { toast: isEdit ? "Property updated." : "Property created." },
        });
      })
      .catch((err) => setSubmitError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  if (loading) {
    return <LoadingSpinner label="Loading…" />;
  }

  if (loadError) {
    return <ErrorMessage message={loadError} />;
  }

  return (
    <div>
      <PageHeader title={isEdit ? "Edit property" : "New property"} />

      {submitError && <ErrorMessage message={submitError} />}

      <form className="form-card" onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          <div className="form-field--full">
            <FormField
              label="Property name"
              name="PropertyName"
              value={form.PropertyName}
              onChange={updateField("PropertyName")}
              required
              error={errors.PropertyName}
            />
          </div>
          <SelectField
            label="Property type"
            name="PropertyType"
            value={form.PropertyType}
            onChange={updateField("PropertyType")}
            placeholder="Choose a type"
            options={PROPERTY_TYPE_OPTIONS}
            required
            error={errors.PropertyType}
          />
          <SelectField
            label="Status"
            name="PropertyStatus"
            value={form.PropertyStatus}
            onChange={updateField("PropertyStatus")}
            options={PROPERTY_STATUS_OPTIONS}
          />
          <div className="form-field--full">
            <FormField
              label="Address line 1"
              name="AddressLine1"
              value={form.AddressLine1}
              onChange={updateField("AddressLine1")}
              required
              error={errors.AddressLine1}
            />
          </div>
          <div className="form-field--full">
            <FormField
              label="Address line 2"
              name="AddressLine2"
              value={form.AddressLine2}
              onChange={updateField("AddressLine2")}
            />
          </div>
          <FormField label="City" name="City" value={form.City} onChange={updateField("City")} />
          <FormField
            label="Postcode"
            name="Postcode"
            value={form.Postcode}
            onChange={updateField("Postcode")}
            required
            error={errors.Postcode}
          />
          <FormField
            label="Number of units (declared)"
            name="NumberOfUnits"
            type="number"
            value={form.NumberOfUnits}
            onChange={updateField("NumberOfUnits")}
            error={errors.NumberOfUnits}
          />
          <SelectField
            label="Inspection frequency"
            name="InspectionFrequency"
            value={form.InspectionFrequency}
            onChange={updateField("InspectionFrequency")}
            placeholder="Choose a frequency"
            options={INSPECTION_FREQUENCY_OPTIONS}
            required
            error={errors.InspectionFrequency}
          />
          <DateField
            label="Last inspection date"
            name="LastInspectionDate"
            value={form.LastInspectionDate}
            onChange={updateField("LastInspectionDate")}
          />
          <DateField
            label="Next inspection due"
            name="NextInspectionDue"
            value={form.NextInspectionDue}
            onChange={updateField("NextInspectionDue")}
          />

          <div className="form-field--full">
            <h3>Contact & access</h3>
          </div>
          <FormField
            label="Main contact name"
            name="MainContactName"
            value={form.MainContactName}
            onChange={updateField("MainContactName")}
          />
          <FormField
            label="Main contact phone"
            name="MainContactPhone"
            value={form.MainContactPhone}
            onChange={updateField("MainContactPhone")}
          />
          <FormField
            label="Main contact email"
            name="MainContactEmail"
            type="email"
            value={form.MainContactEmail}
            onChange={updateField("MainContactEmail")}
          />
          <FormField
            label="Key location"
            name="KeyLocation"
            value={form.KeyLocation}
            onChange={updateField("KeyLocation")}
          />
          <div className="form-field--full">
            <FormField
              label="Access instructions"
              name="AccessInstructions"
              value={form.AccessInstructions}
              onChange={updateField("AccessInstructions")}
            />
          </div>
          <div className="form-field--full form-field--with-toggle">
            <FormField
              label="Alarm / access code"
              name="AlarmAccessCode"
              type={showAlarmCode ? "text" : "password"}
              value={form.AlarmAccessCode}
              onChange={updateField("AlarmAccessCode")}
            />
            <button
              type="button"
              className="button button--secondary button--small"
              onClick={() => setShowAlarmCode((prev) => !prev)}
            >
              {showAlarmCode ? "Hide" : "Show"}
            </button>
          </div>
          <div className="form-field--full">
            <FormField
              label="General notes"
              name="GeneralNotes"
              value={form.GeneralNotes}
              onChange={updateField("GeneralNotes")}
            />
          </div>
        </div>

        <div className="form-card__actions">
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create property"}
          </button>
          <button type="button" className="button button--secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
