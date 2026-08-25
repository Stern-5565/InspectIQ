/**
 * GET /api/maintenance-issues/{id} - Updates (the full timeline) come embedded in the same
 * response (MaintenanceIssueDetailResponse.from_issue), so no separate GET .../timeline call is
 * needed here.
 *
 * Three authorization tiers rendered as three separately-gated sections, matching
 * maintenance_service.py's own module docstring exactly rather than one blanket "can edit" flag:
 * - `canManage` (Administrator/Manager only, CAN_MANAGE_MAINTENANCE): the "Edit" link (general
 *   fields, a separate page - MaintenanceIssueFormPage.jsx) and the Assign control.
 * - `canWork` (the issue's own AssignedUserId, OR canManage - mirrors
 *   maintenance_service.ensure_can_edit exactly): status changes, notes, and photo uploads.
 *   Computed here per-record, the same reason InspectionWizardLayout.jsx computes `canEdit`
 *   itself rather than relying on a static role list.
 * - View (everything else on this page): any company member, no gating at all.
 *
 * Property/Unit/every user referenced (ReportedByUserId, AssignedUserId, each timeline entry's
 * UserId) are resolved to display names via one-off fetches on mount - the summary/detail/
 * timeline responses only ever carry bare IDs, the same "frontend resolves the name" convention
 * every other module in this app already uses.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { SelectField } from "../../components/SelectField";
import { MediaAttachments } from "../../components/MediaAttachments";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_MAINTENANCE } from "../../constants/roles";
import { MAINTENANCE_STATUS_OPTIONS } from "../../constants/maintenanceOptions";
import {
  addMaintenanceNote,
  assignMaintenanceIssue,
  getMaintenanceIssue,
  updateMaintenanceStatus,
  uploadMaintenancePhoto,
} from "../../services/maintenanceService";
import { getProperty } from "../../services/propertyService";
import { getUnit } from "../../services/unitService";
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

function describeUpdate(update, userNamesById) {
  const who = userNamesById[update.UserId] ?? `User #${update.UserId}`;
  if (update.UpdateType === "StatusChange") {
    return update.OldStatus
      ? `${who} changed status from ${update.OldStatus} to ${update.NewStatus}.`
      : `${who} set status to ${update.NewStatus}.`;
  }
  if (update.UpdateType === "PhotoUploaded") {
    return `${who} uploaded a photo.`;
  }
  return `${who} added a note.`;
}

export function MaintenanceIssueDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_MAINTENANCE);
  const navigate = useNavigate();
  const location = useLocation();

  const [issue, setIssue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [propertyName, setPropertyName] = useState(null);
  const [unitNumber, setUnitNumber] = useState(null);
  const [userOptions, setUserOptions] = useState([]);
  const [userNamesById, setUserNamesById] = useState({});

  const [assigneeId, setAssigneeId] = useState("");
  const [assignSaving, setAssignSaving] = useState(false);
  const [assignError, setAssignError] = useState(null);

  const [newStatus, setNewStatus] = useState("");
  const [statusComment, setStatusComment] = useState("");
  const [statusSaving, setStatusSaving] = useState(false);
  const [statusError, setStatusError] = useState(null);

  const [noteText, setNoteText] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);
  const [noteError, setNoteError] = useState(null);

  const loadIssue = useCallback(() => {
    setLoading(true);
    setError(null);
    getMaintenanceIssue(id)
      .then((data) => {
        setIssue(data);
        setAssigneeId(data.AssignedUserId ? String(data.AssignedUserId) : "");
        return getProperty(data.PropertyId).then((p) => setPropertyName(p.PropertyName));
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  // A quiet re-fetch (no loading-spinner gate) for when only `Updates` needs to catch up -
  // unlike loadIssue(), this must NOT flip `loading`, which would unmount the whole detail page
  // (MediaAttachments included) mid-upload.
  function refreshTimeline() {
    getMaintenanceIssue(id).then(setIssue);
  }

  useEffect(() => {
    loadIssue();
  }, [loadIssue]);

  useEffect(() => {
    if (issue?.UnitId) {
      getUnit(issue.UnitId)
        .then((u) => setUnitNumber(u.UnitNumber))
        .catch(() => setUnitNumber(null));
    } else {
      setUnitNumber(null);
    }
  }, [issue?.UnitId]);

  useEffect(() => {
    listUsers()
      .then((users) => {
        setUserOptions(users.map((u) => ({ value: String(u.UserId), label: `${u.FirstName} ${u.LastName}` })));
        setUserNamesById(Object.fromEntries(users.map((u) => [u.UserId, `${u.FirstName} ${u.LastName}`])));
      })
      .catch(() => setUserOptions([]));
  }, []);

  if (loading) {
    return <LoadingSpinner label="Loading maintenance issue…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadIssue} />;
  }

  const canWork = canManage || user.UserId === issue.AssignedUserId;
  const statusOptionsExcludingCurrent = MAINTENANCE_STATUS_OPTIONS.filter((o) => o.value !== issue.Status);

  function handleAssign() {
    if (!assigneeId) return;
    setAssignSaving(true);
    setAssignError(null);
    assignMaintenanceIssue(id, Number(assigneeId))
      .then((updated) => {
        setIssue(updated);
        setToast("Issue assigned.");
      })
      .catch((err) => setAssignError(getErrorMessage(err)))
      .finally(() => setAssignSaving(false));
  }

  function handleStatusUpdate(event) {
    event.preventDefault();
    if (!newStatus) return;
    setStatusSaving(true);
    setStatusError(null);
    updateMaintenanceStatus(id, newStatus, statusComment.trim() || undefined)
      .then((updated) => {
        setIssue(updated);
        setNewStatus("");
        setStatusComment("");
        setToast(`Status updated to ${updated.Status}.`);
      })
      .catch((err) => setStatusError(getErrorMessage(err)))
      .finally(() => setStatusSaving(false));
  }

  function handleAddNote(event) {
    event.preventDefault();
    if (!noteText.trim()) return;
    setNoteSaving(true);
    setNoteError(null);
    addMaintenanceNote(id, noteText.trim())
      .then((update) => {
        setIssue((prev) => ({ ...prev, Updates: [...prev.Updates, update] }));
        setNoteText("");
      })
      .catch((err) => setNoteError(getErrorMessage(err)))
      .finally(() => setNoteSaving(false));
  }

  return (
    <div>
      <PageHeader
        title={issue.Title}
        actions={
          canManage && (
            <Link to={`/maintenance-issues/${id}/edit`} className="button button--secondary">
              Edit
            </Link>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="detail-card">
        <StatusBadge status={issue.Status} />
        <StatusBadge status={issue.Priority} />

        <div className="detail-grid">
          <Field
            label="Property"
            value={propertyName ? <Link to={`/properties/${issue.PropertyId}`}>{propertyName}</Link> : `Property #${issue.PropertyId}`}
          />
          {issue.UnitId && <Field label="Unit" value={unitNumber ?? `Unit #${issue.UnitId}`} />}
          <Field label="Category" value={issue.Category} />
          <Field label="Location" value={issue.Location} />
          <Field label="Reported by" value={userNamesById[issue.ReportedByUserId] ?? `User #${issue.ReportedByUserId}`} />
          <Field label="Reported date" value={issue.ReportedDate} />
          <Field label="Due date" value={issue.DueDate} />
          {issue.CompletedDate && <Field label="Completed date" value={issue.CompletedDate} />}
          <Field label="Description" value={issue.Description} />
          <Field label="Notes" value={issue.Notes} />
        </div>
      </div>

      <div className="detail-card">
        <h2>Assignment</h2>
        <Field label="Currently assigned to" value={issue.AssignedUserId ? (userNamesById[issue.AssignedUserId] ?? "—") : "Unassigned"} />
        {canManage && (
          <>
            <SelectField
              label="Assign to"
              name="assigneeId"
              value={assigneeId}
              onChange={(event) => setAssigneeId(event.target.value)}
              placeholder="Choose a person"
              options={userOptions}
            />
            {assignError && <ErrorMessage message={assignError} />}
            <button
              type="button"
              className="button"
              disabled={assignSaving || !assigneeId || Number(assigneeId) === issue.AssignedUserId}
              onClick={handleAssign}
            >
              {assignSaving ? "Assigning…" : "Assign"}
            </button>
          </>
        )}
      </div>

      {canWork && (
        <div className="detail-card">
          <h2>Update Status</h2>
          <form onSubmit={handleStatusUpdate}>
            <SelectField
              label="New status"
              name="newStatus"
              value={newStatus}
              onChange={(event) => setNewStatus(event.target.value)}
              placeholder="Choose a status"
              options={statusOptionsExcludingCurrent}
              required
            />
            <label className="form-field">
              <span>Comment (optional)</span>
              <textarea
                className="form-field__input answer-textarea"
                value={statusComment}
                onChange={(event) => setStatusComment(event.target.value)}
              />
            </label>
            {statusError && <ErrorMessage message={statusError} />}
            <button type="submit" className="button" disabled={statusSaving || !newStatus}>
              {statusSaving ? "Updating…" : "Update Status"}
            </button>
          </form>
        </div>
      )}

      <div className="detail-card">
        <h2>Timeline</h2>
        {issue.Updates.length === 0 ? (
          <p className="empty-state">No activity yet.</p>
        ) : (
          <ul className="activity-list">
            {issue.Updates.map((update) => (
              <li key={update.MaintenanceUpdateId}>
                <div>{describeUpdate(update, userNamesById)}</div>
                {update.Comment && <div>"{update.Comment}"</div>}
                <span className="detail-grid__label">{new Date(update.CreatedAt).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}

        {canWork && (
          <form onSubmit={handleAddNote}>
            <label className="form-field">
              <span>Add a note</span>
              <textarea
                className="form-field__input answer-textarea"
                value={noteText}
                onChange={(event) => setNoteText(event.target.value)}
              />
            </label>
            {noteError && <ErrorMessage message={noteError} />}
            <button type="submit" className="button button--secondary" disabled={noteSaving || !noteText.trim()}>
              {noteSaving ? "Adding…" : "Add Note"}
            </button>
          </form>
        )}
      </div>

      <div className="detail-card">
        <MediaAttachments
          entityType="MaintenanceIssue"
          entityId={issue.MaintenanceIssueId}
          editable={canWork}
          onUpload={(file) =>
            // uploadMaintenancePhoto also writes a PhotoUploaded timeline entry server-side
            // (maintenance_service.upload_photo) - loadIssue() refreshes `issue.Updates` so the
            // Timeline section shows it immediately, not only after a manual reload. Fire-and-
            // forget: the media object itself is returned unchanged for MediaAttachments' own
            // thumbnail state, independent of whether the issue refetch has resolved yet.
            uploadMaintenancePhoto(issue.MaintenanceIssueId, file).then((media) => {
              refreshTimeline();
              return media;
            })
          }
        />
      </div>

      <p>
        <Link to="/maintenance-issues">← Back to maintenance</Link>
      </p>
    </div>
  );
}
