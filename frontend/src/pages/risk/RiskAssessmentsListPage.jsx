/**
 * GET /api/risk-assessments - view has no role restriction (any company member), matching every
 * other module's read side. Sorted by RiskScore descending server-side (risk_repository.
 * list_risk_assessments' own ORDER BY) - highest risk first, no client-side re-sort needed.
 * Property/Responsible-person names resolved via one-off fetches, the same pattern
 * MaintenanceIssuesListPage.jsx already established.
 *
 * "+ New Risk Assessment" links to the standalone create form - a deliberate difference from
 * Maintenance, which has no such button. Scope §19 doesn't frame risk creation as
 * inspection-only the way §17 explicitly does for Maintenance ("from any inspection question"),
 * and the backend's own RiskAssessmentCreate already supports a PropertyId-only, non-inspection-
 * linked entry - a genuine standalone Risk Register use case (e.g. a manager logging a hazard
 * noticed outside any inspection), not scope creep.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { Pagination } from "../../components/Pagination";
import { FilterPanel } from "../../components/FilterPanel";
import { SelectField } from "../../components/SelectField";
import { StatusBadge } from "../../components/StatusBadge";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_CONDUCT_INSPECTIONS } from "../../constants/roles";
import { RISK_ASSESSMENT_STATUS_OPTIONS } from "../../constants/riskOptions";
import { listRiskAssessments, getRiskMatrix } from "../../services/riskService";
import { listProperties } from "../../services/propertyService";
import { listUsers } from "../../services/userService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function RiskAssessmentsListPage() {
  const { user } = useAuth();
  const canCreate = hasAnyRole(user, CAN_CONDUCT_INSPECTIONS);
  const location = useLocation();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [status, setStatus] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [propertyId, setPropertyId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  const [propertyOptions, setPropertyOptions] = useState([]);
  const [propertyNamesById, setPropertyNamesById] = useState({});
  const [userNamesById, setUserNamesById] = useState({});
  const [riskLevelOptions, setRiskLevelOptions] = useState([]);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    listProperties({ pageSize: 100 })
      .then((data) => {
        setPropertyOptions(data.items.map((p) => ({ value: String(p.PropertyId), label: p.PropertyName })));
        setPropertyNamesById(Object.fromEntries(data.items.map((p) => [p.PropertyId, p.PropertyName])));
      })
      .catch(() => setPropertyOptions([]));

    listUsers()
      .then((users) => {
        setUserNamesById(Object.fromEntries(users.map((u) => [u.UserId, `${u.FirstName} ${u.LastName}`])));
      })
      .catch(() => {});

    getRiskMatrix()
      .then((levels) => setRiskLevelOptions(levels.map((l) => ({ value: l.LevelName, label: l.LevelName }))))
      .catch(() => setRiskLevelOptions([]));
  }, []);

  const loadRiskAssessments = useCallback(() => {
    setLoading(true);
    setError(null);
    listRiskAssessments({
      page,
      pageSize: PAGE_SIZE,
      status: status || undefined,
      riskLevel: riskLevel || undefined,
      propertyId: propertyId || undefined,
    })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, status, riskLevel, propertyId]);

  useEffect(() => {
    loadRiskAssessments();
  }, [loadRiskAssessments]);

  function handleClearFilters() {
    setStatus("");
    setRiskLevel("");
    setPropertyId("");
    setPage(1);
  }

  return (
    <div>
      <PageHeader
        title="Risk Register"
        description="Risk assessments across your company's properties."
        actions={
          <>
            <Link to="/risk-matrix" className="button button--secondary">
              Configure Risk Matrix
            </Link>
            {canCreate && (
              <Link to="/risk-assessments/new" className="button">
                + New Risk Assessment
              </Link>
            )}
          </>
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <FilterPanel title="Filters" onClear={handleClearFilters}>
        <SelectField
          label="Status"
          name="status"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
          placeholder="Any status"
          options={RISK_ASSESSMENT_STATUS_OPTIONS}
        />
        <SelectField
          label="Risk level"
          name="riskLevel"
          value={riskLevel}
          onChange={(event) => {
            setRiskLevel(event.target.value);
            setPage(1);
          }}
          placeholder="Any risk level"
          options={riskLevelOptions}
        />
        <SelectField
          label="Property"
          name="propertyId"
          value={propertyId}
          onChange={(event) => {
            setPropertyId(event.target.value);
            setPage(1);
          }}
          placeholder="Any property"
          options={propertyOptions}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadRiskAssessments}
        emptyMessage="No risk assessments match your filters."
        rows={items}
        getRowKey={(row) => row.RiskAssessmentId}
        columns={[
          {
            key: "Hazard",
            header: "Hazard",
            render: (row) => <Link to={`/risk-assessments/${row.RiskAssessmentId}`}>{row.Hazard}</Link>,
          },
          {
            key: "PropertyId",
            header: "Property",
            render: (row) => propertyNamesById[row.PropertyId] ?? `Property #${row.PropertyId}`,
          },
          { key: "RiskScore", header: "Score" },
          { key: "RiskLevel", header: "Level", render: (row) => <StatusBadge status={row.RiskLevel} /> },
          { key: "Status", header: "Status", render: (row) => <StatusBadge status={row.Status} /> },
          {
            key: "ResponsiblePersonUserId",
            header: "Responsible person",
            render: (row) => (row.ResponsiblePersonUserId ? (userNamesById[row.ResponsiblePersonUserId] ?? "—") : "—"),
          },
          { key: "TargetCompletionDate", header: "Target date", render: (row) => row.TargetCompletionDate ?? "—" },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} onPageChange={setPage} />
      )}
    </div>
  );
}
