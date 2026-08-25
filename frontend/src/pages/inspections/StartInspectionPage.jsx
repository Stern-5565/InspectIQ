/**
 * POST /api/inspections - self-assigns the inspector server-side, so there's no "assign to"
 * field here (app/schemas/inspection.py's own comment on InspectionCreate). `?propertyId=` in
 * the URL pre-selects the property - PropertyDetailPage's "Start Inspection" button links here
 * that way, so an inspector already looking at a property doesn't have to find it again in a
 * dropdown.
 */
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { SelectField } from "../../components/SelectField";
import { DateField } from "../../components/DateField";
import { FormField } from "../../components/FormField";
import { listProperties } from "../../services/propertyService";
import { listTemplates } from "../../services/inspectionTemplateService";
import { startInspection } from "../../services/inspectionService";
import { getErrorMessage } from "../../utilities/apiError";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function StartInspectionPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [propertyOptions, setPropertyOptions] = useState([]);
  const [templateOptions, setTemplateOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [propertyId, setPropertyId] = useState(searchParams.get("propertyId") ?? "");
  const [templateId, setTemplateId] = useState("");
  const [inspectionType, setInspectionType] = useState("");
  const [inspectionDate, setInspectionDate] = useState(todayIso());
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([listProperties({ pageSize: 100 }), listTemplates()])
      .then(([properties, templates]) => {
        setPropertyOptions(properties.items.map((p) => ({ value: String(p.PropertyId), label: p.PropertyName })));
        setTemplateOptions(templates.map((t) => ({ value: String(t.InspectionTemplateId), label: t.TemplateName })));
        if (templates.length === 1) {
          setTemplateId(String(templates[0].InspectionTemplateId));
        }
      })
      .catch((err) => setLoadError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  function handleSubmit(event) {
    event.preventDefault();
    const validationErrors = {};
    if (!propertyId) validationErrors.propertyId = "Choose a property.";
    if (!templateId) validationErrors.templateId = "Choose a template.";
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    startInspection({
      propertyId: Number(propertyId),
      inspectionTemplateId: Number(templateId),
      inspectionType: inspectionType.trim() || undefined,
      inspectionDate,
    })
      .then((inspection) => navigate(`/inspections/${inspection.InspectionId}`))
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
      <PageHeader title="Start Inspection" />

      {submitError && <ErrorMessage message={submitError} />}

      <form className="form-card" onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          <SelectField
            label="Property"
            name="propertyId"
            value={propertyId}
            onChange={(event) => setPropertyId(event.target.value)}
            placeholder="Choose a property"
            options={propertyOptions}
            required
            error={errors.propertyId}
          />
          <SelectField
            label="Inspection template"
            name="templateId"
            value={templateId}
            onChange={(event) => setTemplateId(event.target.value)}
            placeholder="Choose a template"
            options={templateOptions}
            required
            error={errors.templateId}
          />
          <FormField
            label="Inspection type (optional)"
            name="inspectionType"
            value={inspectionType}
            onChange={(event) => setInspectionType(event.target.value)}
            placeholder="e.g. Monthly, Ad-hoc"
          />
          <DateField
            label="Inspection date"
            name="inspectionDate"
            value={inspectionDate}
            onChange={(event) => setInspectionDate(event.target.value)}
          />
        </div>

        <div className="form-card__actions">
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Starting…" : "Start inspection"}
          </button>
          <button type="button" className="button button--secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
