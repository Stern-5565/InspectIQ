/**
 * GET /api/vacant-unit-inspections - a company-wide vacant-unit finding history that didn't
 * exist before this module's own frontend needed it (see app/api/vacant_units.py's module
 * docstring - every prior VacantUnitInspection query was scoped to one already-authorized
 * Inspection). View has no role restriction, matching every other module's read side.
 * PropertyId/UnitNumber come embedded in the response itself
 * (VacantUnitInspectionSummaryResponse), not resolved via a separate fetch.
 *
 * No "+ New Finding" action here, mirroring Cleaning/Maintenance's own reasoning: scope §7's
 * flow always happens as part of conducting an Inspection (Sub-phase E's "Add Empty Unit"
 * gateway action), so there's no standalone create route either.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { Pagination } from "../../components/Pagination";
import { FilterPanel } from "../../components/FilterPanel";
import { SelectField } from "../../components/SelectField";
import { Toast } from "../../components/Toast";
import { listAllVacantUnitInspections } from "../../services/vacantUnitService";
import { listProperties } from "../../services/propertyService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function VacantUnitInspectionsListPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [propertyId, setPropertyId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  const [propertyOptions, setPropertyOptions] = useState([]);
  const [propertyNamesById, setPropertyNamesById] = useState({});

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
  }, []);

  const loadVacantUnitInspections = useCallback(() => {
    setLoading(true);
    setError(null);
    listAllVacantUnitInspections({ page, pageSize: PAGE_SIZE, propertyId: propertyId || undefined })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, propertyId]);

  useEffect(() => {
    loadVacantUnitInspections();
  }, [loadVacantUnitInspections]);

  function handleClearFilters() {
    setPropertyId("");
    setPage(1);
  }

  return (
    <div>
      <PageHeader title="Vacant Units" description="Vacant-unit inspection findings across your company." />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

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
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadVacantUnitInspections}
        emptyMessage="No vacant-unit findings match your filters."
        rows={items}
        getRowKey={(row) => row.VacantUnitInspectionId}
        columns={[
          {
            key: "UnitNumber",
            header: "Unit",
            render: (row) => <Link to={`/vacant-unit-inspections/${row.VacantUnitInspectionId}`}>{row.UnitNumber}</Link>,
          },
          {
            key: "PropertyId",
            header: "Property",
            render: (row) => (
              <Link to={`/properties/${row.PropertyId}`}>{propertyNamesById[row.PropertyId] ?? `Property #${row.PropertyId}`}</Link>
            ),
          },
          { key: "DateIdentifiedVacant", header: "Date identified", render: (row) => row.DateIdentifiedVacant },
          { key: "Condition", header: "Condition", render: (row) => row.Condition ?? "—" },
          { key: "MaintenanceRequired", header: "Maintenance req.", render: (row) => (row.MaintenanceRequired ? "Yes" : "—") },
          { key: "CleaningRequired", header: "Cleaning req.", render: (row) => (row.CleaningRequired ? "Yes" : "—") },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} onPageChange={setPage} />
      )}
    </div>
  );
}
