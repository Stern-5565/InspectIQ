/** GET /api/properties - search, filters, and pagination drive one fetch effect. */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { Pagination } from "../../components/Pagination";
import { SearchInput } from "../../components/SearchInput";
import { FilterPanel } from "../../components/FilterPanel";
import { SelectField } from "../../components/SelectField";
import { StatusBadge } from "../../components/StatusBadge";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_PROPERTIES } from "../../constants/roles";
import { PROPERTY_TYPE_OPTIONS, PROPERTY_STATUS_OPTIONS } from "../../constants/propertyOptions";
import { listProperties } from "../../services/propertyService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function PropertiesListPage() {
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_PROPERTIES);
  const location = useLocation();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [search, setSearch] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [propertyStatus, setPropertyStatus] = useState("");
  const [includeInactive, setIncludeInactive] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadProperties = useCallback(() => {
    setLoading(true);
    setError(null);
    listProperties({
      page,
      pageSize: PAGE_SIZE,
      search,
      propertyType: propertyType || undefined,
      propertyStatus: propertyStatus || undefined,
      includeInactive: includeInactive === "true",
    })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, search, propertyType, propertyStatus, includeInactive]);

  useEffect(() => {
    loadProperties();
  }, [loadProperties]);

  function handleClearFilters() {
    setPropertyType("");
    setPropertyStatus("");
    setIncludeInactive("");
    setPage(1);
  }

  return (
    <div>
      <PageHeader
        title="Properties"
        description="Every property in your company's portfolio."
        actions={
          canManage && (
            <Link to="/properties/new" className="button">
              + New Property
            </Link>
          )
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="list-page__toolbar">
        <SearchInput
          value={search}
          onSearch={(value) => {
            setSearch(value);
            setPage(1);
          }}
          placeholder="Search name, address, postcode…"
        />
      </div>

      <FilterPanel title="Filters" onClear={handleClearFilters}>
        <SelectField
          label="Property type"
          name="propertyType"
          value={propertyType}
          onChange={(event) => {
            setPropertyType(event.target.value);
            setPage(1);
          }}
          placeholder="Any type"
          options={PROPERTY_TYPE_OPTIONS}
        />
        <SelectField
          label="Status"
          name="propertyStatus"
          value={propertyStatus}
          onChange={(event) => {
            setPropertyStatus(event.target.value);
            setPage(1);
          }}
          placeholder="Any status"
          options={PROPERTY_STATUS_OPTIONS}
        />
        <SelectField
          label="Include deactivated"
          name="includeInactive"
          value={includeInactive}
          onChange={(event) => {
            setIncludeInactive(event.target.value);
            setPage(1);
          }}
          placeholder="No"
          options={[{ value: "true", label: "Yes" }]}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadProperties}
        emptyMessage="No properties match your search/filters."
        rows={items}
        getRowKey={(row) => row.PropertyId}
        columns={[
          {
            key: "PropertyName",
            header: "Name",
            render: (row) => <Link to={`/properties/${row.PropertyId}`}>{row.PropertyName}</Link>,
          },
          { key: "AddressLine1", header: "Address" },
          { key: "City", header: "City" },
          { key: "PropertyType", header: "Type" },
          {
            key: "PropertyStatus",
            header: "Status",
            render: (row) => <StatusBadge status={row.PropertyStatus} />,
          },
          {
            key: "NextInspectionDue",
            header: "Next inspection due",
            render: (row) => row.NextInspectionDue ?? "—",
          },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} onPageChange={setPage} />
      )}
    </div>
  );
}
