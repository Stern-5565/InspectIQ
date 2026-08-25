/**
 * GET /api/maintenance-issues - view has no role restriction (any company member), matching
 * every other module's read side. Property/Assigned-to filter options and the Assigned-to
 * column's display name both come from one-off fetches on mount (listProperties/listUsers),
 * the same pattern InspectionsListPage.jsx already established for property names.
 *
 * No "+ New Issue" action here - creating a maintenance issue is the wizard's job (Sub-phase C's
 * quick-create, scope §17's own framing: "from any inspection question"), not a standalone flow
 * this page adds. This is the module's missing OTHER half: browsing/managing what the wizard
 * already created, which had nowhere to be viewed or acted on until now.
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
import {
  MAINTENANCE_CATEGORY_OPTIONS,
  MAINTENANCE_PRIORITY_OPTIONS,
  MAINTENANCE_STATUS_OPTIONS,
} from "../../constants/maintenanceOptions";
import { listMaintenanceIssues } from "../../services/maintenanceService";
import { listProperties } from "../../services/propertyService";
import { listUsers } from "../../services/userService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function MaintenanceIssuesListPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState("");
  const [propertyId, setPropertyId] = useState("");
  const [assignedUserId, setAssignedUserId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  const [propertyOptions, setPropertyOptions] = useState([]);
  const [propertyNamesById, setPropertyNamesById] = useState({});
  const [userOptions, setUserOptions] = useState([]);
  const [userNamesById, setUserNamesById] = useState({});

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
        setUserOptions(users.map((u) => ({ value: String(u.UserId), label: `${u.FirstName} ${u.LastName}` })));
        setUserNamesById(Object.fromEntries(users.map((u) => [u.UserId, `${u.FirstName} ${u.LastName}`])));
      })
      .catch(() => setUserOptions([]));
  }, []);

  const loadIssues = useCallback(() => {
    setLoading(true);
    setError(null);
    listMaintenanceIssues({
      page,
      pageSize: PAGE_SIZE,
      status: status || undefined,
      category: category || undefined,
      priority: priority || undefined,
      propertyId: propertyId || undefined,
      assignedUserId: assignedUserId || undefined,
    })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, status, category, priority, propertyId, assignedUserId]);

  useEffect(() => {
    loadIssues();
  }, [loadIssues]);

  function handleClearFilters() {
    setStatus("");
    setCategory("");
    setPriority("");
    setPropertyId("");
    setAssignedUserId("");
    setPage(1);
  }

  return (
    <div>
      <PageHeader title="Maintenance" description="Maintenance issues raised across your company." />

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
          options={MAINTENANCE_STATUS_OPTIONS}
        />
        <SelectField
          label="Category"
          name="category"
          value={category}
          onChange={(event) => {
            setCategory(event.target.value);
            setPage(1);
          }}
          placeholder="Any category"
          options={MAINTENANCE_CATEGORY_OPTIONS}
        />
        <SelectField
          label="Priority"
          name="priority"
          value={priority}
          onChange={(event) => {
            setPriority(event.target.value);
            setPage(1);
          }}
          placeholder="Any priority"
          options={MAINTENANCE_PRIORITY_OPTIONS}
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
        <SelectField
          label="Assigned to"
          name="assignedUserId"
          value={assignedUserId}
          onChange={(event) => {
            setAssignedUserId(event.target.value);
            setPage(1);
          }}
          placeholder="Anyone"
          options={userOptions}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadIssues}
        emptyMessage="No maintenance issues match your filters."
        rows={items}
        getRowKey={(row) => row.MaintenanceIssueId}
        columns={[
          {
            key: "Title",
            header: "Title",
            render: (row) => <Link to={`/maintenance-issues/${row.MaintenanceIssueId}`}>{row.Title}</Link>,
          },
          {
            key: "PropertyId",
            header: "Property",
            render: (row) => propertyNamesById[row.PropertyId] ?? `Property #${row.PropertyId}`,
          },
          { key: "Category", header: "Category" },
          { key: "Priority", header: "Priority", render: (row) => <StatusBadge status={row.Priority} /> },
          { key: "Status", header: "Status", render: (row) => <StatusBadge status={row.Status} /> },
          {
            key: "AssignedUserId",
            header: "Assigned to",
            render: (row) => (row.AssignedUserId ? (userNamesById[row.AssignedUserId] ?? "—") : "Unassigned"),
          },
          { key: "DueDate", header: "Due date", render: (row) => row.DueDate ?? "—" },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} onPageChange={setPage} />
      )}
    </div>
  );
}
