/**
 * Shared create/edit form - POST/PATCH /api/risk-assessments, same dual-mode shape as
 * PropertyFormPage.jsx (`isEdit = id !== undefined`). The two modes genuinely differ in fields,
 * not just which request fires: Property is only asked at create time (RiskAssessmentCreate
 * requires it when not linked to an inspection; RiskAssessmentUpdate has no PropertyId field at
 * all - a risk can't be reassigned to a different property after creation), while Status only
 * exists to edit (a new risk always starts "Open" server-side, RiskAssessmentCreate has no
 * Status field either).
 *
 * Create is CAN_CONDUCT_INSPECTIONS-gated at the route level (App.jsx); edit is CAN_MANAGE_RISK.
 * Neither is enforced again here - ProtectedRoute already keeps an unauthorized user off this
 * page entirely.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SelectField } from "../../components/SelectField";
import { DateField } from "../../components/DateField";
import { LIKELIHOOD_OPTIONS, SEVERITY_OPTIONS, RISK_ASSESSMENT_STATUS_OPTIONS } from "../../constants/riskOptions";
import { createRiskAssessment, getRiskAssessment, updateRiskAssessment } from "../../services/riskService";
import { listProperties } from "../../services/propertyService";
import { listUsers } from "../../services/userService";
import { getErrorMessage } from "../../utilities/apiError";

const BLANK_FORM = {
  PropertyId: "",
  Location: "",
  Hazard: "",
  WhoMayBeAffected: "",
  ExistingControls: "",
  Likelihood: "",
  Severity: "",
  AdditionalActionRequired: "",
  ResponsiblePersonUserId: "",
  TargetCompletionDate: "",
  Status: "Open",
  Notes: "",
};

function validate(form, isEdit) {
  const errors = {};
  if (!isEdit && !form.PropertyId) errors.PropertyId = "Choose a property.";
  if (!form.Hazard.trim()) errors.Hazard = "Hazard is required.";
  if (!form.Likelihood) errors.Likelihood = "Choose a likelihood.";
  if (!form.Severity) errors.Severity = "Choose a severity.";
  return errors;
}

export function RiskAssessmentFormPage() {
  const { id } = useParams();
  const isEdit = id !== undefined;
  const navigate = useNavigate();

  const [form, setForm] = useState(BLANK_FORM);
  const [loading, setLoading] = useState(isEdit);
  const [loadError, setLoadError] = useState(null);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [propertyOptions, setPropertyOptions] = useState([]);
  const [userOptions, setUserOptions] = useState([]);

  useEffect(() => {
    if (!isEdit) {
      listProperties({ pageSize: 100 })
        .then((data) => setPropertyOptions(data.items.map((p) => ({ value: String(p.PropertyId), label: p.PropertyName }))))
        .catch(() => setPropertyOptions([]));
    }
    listUsers()
      .then((users) => setUserOptions(users.map((u) => ({ value: String(u.UserId), label: `${u.FirstName} ${u.LastName}` }))))
      .catch(() => setUserOptions([]));
  }, [isEdit]);

  useEffect(() => {
    if (!isEdit) {
      return;
    }
    getRiskAssessment(id)
      .then((risk) =>
        setForm({
          PropertyId: "",
          Location: risk.Location ?? "",
          Hazard: risk.Hazard,
          WhoMayBeAffected: risk.WhoMayBeAffected ?? "",
          ExistingControls: risk.ExistingControls ?? "",
          Likelihood: String(risk.Likelihood),
          Severity: String(risk.Severity),
          AdditionalActionRequired: risk.AdditionalActionRequired ?? "",
          ResponsiblePersonUserId: risk.ResponsiblePersonUserId ? String(risk.ResponsiblePersonUserId) : "",
          TargetCompletionDate: risk.TargetCompletionDate ?? "",
          Status: risk.Status,
          Notes: risk.Notes ?? "",
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
    const validationErrors = validate(form, isEdit);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    const shared = {
      location: form.Location.trim() || null,
      hazard: form.Hazard.trim(),
      whoMayBeAffected: form.WhoMayBeAffected.trim() || null,
      existingControls: form.ExistingControls.trim() || null,
      likelihood: Number(form.Likelihood),
      severity: Number(form.Severity),
      additionalActionRequired: form.AdditionalActionRequired.trim() || null,
      responsiblePersonUserId: form.ResponsiblePersonUserId ? Number(form.ResponsiblePersonUserId) : null,
      targetCompletionDate: form.TargetCompletionDate || null,
      notes: form.Notes.trim() || null,
    };

    const request = isEdit
      ? updateRiskAssessment(id, {
          Location: shared.location,
          Hazard: shared.hazard,
          WhoMayBeAffected: shared.whoMayBeAffected,
          ExistingControls: shared.existingControls,
          Likelihood: shared.likelihood,
          Severity: shared.severity,
          AdditionalActionRequired: shared.additionalActionRequired,
          ResponsiblePersonUserId: shared.responsiblePersonUserId,
          TargetCompletionDate: shared.targetCompletionDate,
          Status: form.Status,
          Notes: shared.notes,
        })
      : createRiskAssessment({ propertyId: Number(form.PropertyId), ...shared });

    request
      .then((risk) => {
        navigate(`/risk-assessments/${risk.RiskAssessmentId}`, {
          state: { toast: isEdit ? "Risk assessment updated." : "Risk assessment created." },
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
      <PageHeader title={isEdit ? "Edit Risk Assessment" : "New Risk Assessment"} />

      {submitError && <ErrorMessage message={submitError} />}

      <form className="form-card" onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          {!isEdit && (
            <SelectField
              label="Property"
              name="PropertyId"
              value={form.PropertyId}
              onChange={updateField("PropertyId")}
              placeholder="Choose a property"
              options={propertyOptions}
              required
              error={errors.PropertyId}
            />
          )}
          <div className="form-field--full">
            <FormField
              label="Hazard"
              name="Hazard"
              value={form.Hazard}
              onChange={updateField("Hazard")}
              required
              error={errors.Hazard}
            />
          </div>
          <FormField label="Location" name="Location" value={form.Location} onChange={updateField("Location")} />
          <SelectField
            label="Likelihood"
            name="Likelihood"
            value={form.Likelihood}
            onChange={updateField("Likelihood")}
            placeholder="Choose likelihood"
            options={LIKELIHOOD_OPTIONS}
            required
            error={errors.Likelihood}
          />
          <SelectField
            label="Severity"
            name="Severity"
            value={form.Severity}
            onChange={updateField("Severity")}
            placeholder="Choose severity"
            options={SEVERITY_OPTIONS}
            required
            error={errors.Severity}
          />
          {isEdit && (
            <SelectField
              label="Status"
              name="Status"
              value={form.Status}
              onChange={updateField("Status")}
              options={RISK_ASSESSMENT_STATUS_OPTIONS}
            />
          )}
          <SelectField
            label="Responsible person"
            name="ResponsiblePersonUserId"
            value={form.ResponsiblePersonUserId}
            onChange={updateField("ResponsiblePersonUserId")}
            placeholder="Unassigned"
            options={userOptions}
          />
          <DateField
            label="Target completion date"
            name="TargetCompletionDate"
            value={form.TargetCompletionDate}
            onChange={updateField("TargetCompletionDate")}
          />
          <div className="form-field--full">
            <FormField
              label="Who may be affected"
              name="WhoMayBeAffected"
              value={form.WhoMayBeAffected}
              onChange={updateField("WhoMayBeAffected")}
            />
          </div>
          <div className="form-field--full">
            <FormField
              label="Existing controls"
              name="ExistingControls"
              value={form.ExistingControls}
              onChange={updateField("ExistingControls")}
            />
          </div>
          <div className="form-field--full">
            <FormField
              label="Additional action required"
              name="AdditionalActionRequired"
              value={form.AdditionalActionRequired}
              onChange={updateField("AdditionalActionRequired")}
            />
          </div>
          <div className="form-field--full">
            <FormField label="Notes" name="Notes" value={form.Notes} onChange={updateField("Notes")} />
          </div>
        </div>

        <div className="form-card__actions">
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create risk assessment"}
          </button>
          <button type="button" className="button button--secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
