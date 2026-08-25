/**
 * GET /api/cleaning-inspections - a company-wide grading history list that didn't exist before
 * this module's own frontend needed it (see app/api/cleaning.py's module docstring - every
 * prior CleaningInspection query was scoped to one already-authorized Inspection). View has no
 * role restriction, matching every other module's read side. PropertyId/AreaName come embedded
 * in the response itself (CleaningInspectionSummaryResponse), not resolved via a separate
 * fetch - the backend already joins them server-side for this exact reason.
 *
 * No "+ New Grade" action here - scope §16's grading always happens as part of conducting an
 * Inspection (structurally enforced too: CleaningInspection.InspectionId is NOT NULL), the same
 * "wizard-only creation" reasoning Maintenance follows, unlike Risk Register's standalone
 * create form.
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
import { CLEANING_GRADE_OPTIONS, CLEANING_INSPECTION_STATUS_OPTIONS } from "../../constants/cleaningOptions";
import { listAllCleaningInspections } from "../../services/cleaningService";
import { listProperties } from "../../services/propertyService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function CleaningInspectionsListPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [propertyId, setPropertyId] = useState("");
  const [grade, setGrade] = useState("");
  const [status, setStatus] = useState("");
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

  const loadCleaningInspections = useCallback(() => {
    setLoading(true);
    setError(null);
    listAllCleaningInspections({
      page,
      pageSize: PAGE_SIZE,
      propertyId: propertyId || undefined,
      grade: grade || undefined,
      status: status || undefined,
    })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, propertyId, grade, status]);

  useEffect(() => {
    loadCleaningInspections();
  }, [loadCleaningInspections]);

  function handleClearFilters() {
    setPropertyId("");
    setGrade("");
    setStatus("");
    setPage(1);
  }

  return (
    <div>
      <PageHeader title="Cleaning" description="Communal area grading history across your company." />

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
        <SelectField
          label="Grade"
          name="grade"
          value={grade}
          onChange={(event) => {
            setGrade(event.target.value);
            setPage(1);
          }}
          placeholder="Any grade"
          options={CLEANING_GRADE_OPTIONS.map((o) => ({ value: o.value, label: o.value }))}
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
          options={CLEANING_INSPECTION_STATUS_OPTIONS}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadCleaningInspections}
        emptyMessage="No cleaning grades match your filters."
        rows={items}
        getRowKey={(row) => row.CleaningInspectionId}
        columns={[
          {
            key: "AreaName",
            header: "Area",
            render: (row) => <Link to={`/cleaning-inspections/${row.CleaningInspectionId}`}>{row.AreaName}</Link>,
          },
          {
            key: "PropertyId",
            header: "Property",
            render: (row) => (
              <Link to={`/properties/${row.PropertyId}`}>{propertyNamesById[row.PropertyId] ?? `Property #${row.PropertyId}`}</Link>
            ),
          },
          { key: "Grade", header: "Grade", render: (row) => <StatusBadge status={row.Grade} /> },
          { key: "Status", header: "Status", render: (row) => <StatusBadge status={row.Status} /> },
          { key: "CleaningRequired", header: "Cleaning req.", render: (row) => (row.CleaningRequired ? "Yes" : "—") },
          { key: "Urgent", header: "Urgent", render: (row) => (row.Urgent ? "Yes" : "—") },
          { key: "DueDate", header: "Due date", render: (row) => row.DueDate ?? "—" },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} onPageChange={setPage} />
      )}
    </div>
  );
}
