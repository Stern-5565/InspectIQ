/**
 * GET /api/inspections - view has no role restriction (any company member), matching every
 * other module's read side. The property filter's options come from a one-off
 * listProperties({pageSize:100}) fetched once on mount, same pattern PropertyManager used for
 * its own list-page filter dropdowns.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { Pagination } from "../../components/Pagination";
import { FilterPanel } from "../../components/FilterPanel";
import { SelectField } from "../../components/SelectField";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_CONDUCT_INSPECTIONS } from "../../constants/roles";
import { listInspections } from "../../services/inspectionService";
import { listProperties } from "../../services/propertyService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

const STATUS_OPTIONS = [
  { value: "InProgress", label: "In Progress" },
  { value: "Submitted", label: "Submitted" },
  { value: "Scheduled", label: "Scheduled" },
  { value: "Completed", label: "Completed" },
  { value: "Cancelled", label: "Cancelled" },
];

export function InspectionsListPage() {
  const { user } = useAuth();
  const canConduct = hasAnyRole(user, CAN_CONDUCT_INSPECTIONS);

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [propertyId, setPropertyId] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [propertyOptions, setPropertyOptions] = useState([]);
  const [propertyNamesById, setPropertyNamesById] = useState({});

  useEffect(() => {
    listProperties({ pageSize: 100 })
      .then((data) => {
        setPropertyOptions(data.items.map((p) => ({ value: String(p.PropertyId), label: p.PropertyName })));
        setPropertyNamesById(Object.fromEntries(data.items.map((p) => [p.PropertyId, p.PropertyName])));
      })
      .catch(() => setPropertyOptions([])); // filter dropdown just stays empty - not worth its own error UI
  }, []);

  const loadInspections = useCallback(() => {
    setLoading(true);
    setError(null);
    listInspections({ page, pageSize: PAGE_SIZE, propertyId: propertyId || undefined, status: status || undefined })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, propertyId, status]);

  useEffect(() => {
    loadInspections();
  }, [loadInspections]);

  function handleClearFilters() {
    setPropertyId("");
    setStatus("");
    setPage(1);
  }

  return (
    <div>
      <PageHeader
        title="Inspections"
        description="Property inspections across your company."
        actions={
          canConduct && (
            <Link to="/inspections/new" className="button">
              + Start Inspection
            </Link>
          )
        }
      />

      <FilterPanel title="Filters" onClear={handleClearFilters}>
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
          label="Status"
          name="status"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
          placeholder="Any status"
          options={STATUS_OPTIONS}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadInspections}
        emptyMessage="No inspections match your filters."
        rows={items}
        getRowKey={(row) => row.InspectionId}
        columns={[
          {
            key: "PropertyId",
            header: "Property",
            render: (row) => (
              <Link to={`/inspections/${row.InspectionId}`}>
                {propertyNamesById[row.PropertyId] ?? `Property #${row.PropertyId}`}
              </Link>
            ),
          },
          { key: "InspectionDate", header: "Date" },
          { key: "InspectionType", header: "Type", render: (row) => row.InspectionType ?? "—" },
          { key: "Status", header: "Status", render: (row) => <StatusBadge status={row.Status} /> },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} onPageChange={setPage} />
      )}
    </div>
  );
}
