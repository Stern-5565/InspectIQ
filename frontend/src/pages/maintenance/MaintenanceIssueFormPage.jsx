/**
 * PATCH /api/maintenance-issues/{id} - general field edits only (Title/Description/Location/
 * Category/Priority/DueDate/Notes), Administrator/Manager only per
 * maintenance_service.py's own module docstring. Edit-only, no create mode - unlike
 * PropertyFormPage.jsx's dual-mode shape, this page has no `/maintenance-issues/new` counterpart:
 * scope §17 frames issue creation entirely as the wizard's job ("from any inspection question"),
 * not a standalone flow, so this page is reached only via the Detail page's "Edit" link.
 * Status/AssignedUserId are deliberately excluded here too, matching the backend's own
 * MaintenanceIssueUpdate schema exactly - both have their own dedicated controls on the Detail
 * page.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SelectField } from "../../components/SelectField";
import { DateField } from "../../components/DateField";
import { MAINTENANCE_CATEGORY_OPTIONS, MAINTENANCE_PRIORITY_OPTIONS } from "../../constants/maintenanceOptions";
import { getMaintenanceIssue, updateMaintenanceIssue } from "../../services/maintenanceService";
import { getErrorMessage } from "../../utilities/apiError";

export function MaintenanceIssueFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [form, setForm] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  useEffect(() => {
    getMaintenanceIssue(id)
      .then((issue) =>
        setForm({
          Title: issue.Title,
          Description: issue.Description ?? "",
          Location: issue.Location ?? "",
          Category: issue.Category,
          Priority: issue.Priority,
          DueDate: issue.DueDate ?? "",
          Notes: issue.Notes ?? "",
        }),
      )
      .catch((err) => setLoadError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!form.Title.trim()) {
      setSubmitError("Title is required.");
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    updateMaintenanceIssue(id, {
      Title: form.Title.trim(),
      Description: form.Description.trim() || null,
      Location: form.Location.trim() || null,
      Category: form.Category,
      Priority: form.Priority,
      DueDate: form.DueDate || null,
      Notes: form.Notes.trim() || null,
    })
      .then(() => navigate(`/maintenance-issues/${id}`, { state: { toast: "Maintenance issue updated." } }))
      .catch((err) => {
        setSubmitError(getErrorMessage(err));
        setSubmitting(false);
      });
  }

  if (loading) {
    return <LoadingSpinner label="Loading maintenance issue…" />;
  }

  if (loadError) {
    return <ErrorMessage message={loadError} />;
  }

  return (
    <div>
      <PageHeader title="Edit Maintenance Issue" />

      <div className="form-card">
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <FormField
              label="Title"
              name="Title"
              value={form.Title}
              onChange={(event) => updateField("Title", event.target.value)}
              required
            />
            <SelectField
              label="Category"
              name="Category"
              value={form.Category}
              onChange={(event) => updateField("Category", event.target.value)}
              options={MAINTENANCE_CATEGORY_OPTIONS}
              required
            />
            <SelectField
              label="Priority"
              name="Priority"
              value={form.Priority}
              onChange={(event) => updateField("Priority", event.target.value)}
              options={MAINTENANCE_PRIORITY_OPTIONS}
              required
            />
            <DateField
              label="Due date"
              name="DueDate"
              value={form.DueDate}
              onChange={(event) => updateField("DueDate", event.target.value)}
            />
            <FormField
              label="Location"
              name="Location"
              value={form.Location}
              onChange={(event) => updateField("Location", event.target.value)}
            />
          </div>

          <label className="form-field">
            <span>Description</span>
            <textarea
              className="form-field__input answer-textarea"
              value={form.Description}
              onChange={(event) => updateField("Description", event.target.value)}
            />
          </label>

          <label className="form-field">
            <span>Notes</span>
            <textarea
              className="form-field__input answer-textarea"
              value={form.Notes}
              onChange={(event) => updateField("Notes", event.target.value)}
            />
          </label>

          {submitError && <ErrorMessage message={submitError} />}

          <div className="form-card__actions">
            <button type="submit" className="button" disabled={submitting}>
              {submitting ? "Saving…" : "Save"}
            </button>
            <Link to={`/maintenance-issues/${id}`} className="button button--secondary">
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
