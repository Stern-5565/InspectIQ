/**
 * GET /api/risk-assessments/{id}. No timeline table exists for RiskAssessments (unlike
 * Maintenance) - scope §19 names no audit-trail requirement, so there's nothing here to log
 * chronologically; edits just overwrite the record via the one combined PATCH.
 *
 * Two authorization surfaces, confirmed independently by reading the backend rather than
 * assumed from Maintenance's shape:
 * - `canManage` (Administrator/Manager, CAN_MANAGE_RISK) gates the Edit link - the only mutate
 *   action this record has (risk_service.update_risk_assessment, one combined PATCH covering
 *   every field including Status/ResponsiblePersonUserId). No per-record carve-out exists -
 *   being the ResponsiblePersonUserId does NOT grant edit rights, unlike Maintenance's
 *   AssignedUserId tier.
 * - Photos are NOT gated on `canManage` at all - confirmed by reading media_service.py:
 *   RiskAssessment's media mutate check is the SAME function as its view check (any company
 *   member), matching Property/Unit's "uploading evidence is broader than editing the record"
 *   shape. `MediaAttachments` gets `editable={true}` unconditionally here - not a bug, a
 *   verified backend behavior (an Inspector who gets a real 403 on Edit can still legitimately
 *   attach a photo).
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { MediaAttachments } from "../../components/MediaAttachments";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_RISK } from "../../constants/roles";
import { getRiskAssessment } from "../../services/riskService";
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

export function RiskAssessmentDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_RISK);
  const navigate = useNavigate();
  const location = useLocation();

  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);
  const [propertyName, setPropertyName] = useState(null);
  const [userNamesById, setUserNamesById] = useState({});

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadRisk = useCallback(() => {
    setLoading(true);
    setError(null);
    getRiskAssessment(id)
      .then((data) => {
        setRisk(data);
        return getProperty(data.PropertyId).then((p) => setPropertyName(p.PropertyName));
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadRisk();
  }, [loadRisk]);

  useEffect(() => {
    listUsers()
      .then((users) => setUserNamesById(Object.fromEntries(users.map((u) => [u.UserId, `${u.FirstName} ${u.LastName}`]))))
      .catch(() => {});
  }, []);

  if (loading) {
    return <LoadingSpinner label="Loading risk assessment…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadRisk} />;
  }

  return (
    <div>
      <PageHeader
        title={risk.Hazard}
        actions={
          canManage && (
            <Link to={`/risk-assessments/${id}/edit`} className="button button--secondary">
              Edit
            </Link>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="detail-card">
        <StatusBadge status={risk.RiskLevel} />
        <StatusBadge status={risk.Status} />

        <div className="detail-grid">
          <Field
            label="Property"
            value={propertyName ? <Link to={`/properties/${risk.PropertyId}`}>{propertyName}</Link> : `Property #${risk.PropertyId}`}
          />
          <Field label="Location" value={risk.Location} />
          <Field label="Likelihood x Severity" value={`${risk.Likelihood} x ${risk.Severity} = ${risk.RiskScore}`} />
          <Field label="Who may be affected" value={risk.WhoMayBeAffected} />
          <Field label="Existing controls" value={risk.ExistingControls} />
          <Field label="Additional action required" value={risk.AdditionalActionRequired} />
          <Field
            label="Responsible person"
            value={risk.ResponsiblePersonUserId ? (userNamesById[risk.ResponsiblePersonUserId] ?? "—") : "—"}
          />
          <Field label="Target completion date" value={risk.TargetCompletionDate} />
          {risk.InspectionId && (
            <Field label="Linked inspection" value={<Link to={`/inspections/${risk.InspectionId}`}>View inspection</Link>} />
          )}
          {risk.MaintenanceIssueId && (
            <Field
              label="Linked maintenance issue"
              value={<Link to={`/maintenance-issues/${risk.MaintenanceIssueId}`}>View issue</Link>}
            />
          )}
          <Field label="Notes" value={risk.Notes} />
        </div>
      </div>

      <div className="detail-card">
        <MediaAttachments entityType="RiskAssessment" entityId={risk.RiskAssessmentId} editable />
      </div>

      <p>
        <Link to="/risk-assessments">← Back to risk register</Link>
      </p>
    </div>
  );
}
