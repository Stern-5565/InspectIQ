/**
 * GET /api/meter-readings - this list was already company-wide since Phase 14 (unlike Cleaning/
 * VacantUnits, MeterReadings was never nested under one Inspection), so this module needed no
 * new backend ROUTE - just PropertyName/InspectionId added onto the existing response
 * (MeterReadingSummaryResponse, app/schemas/meter_reading.py). View has no role restriction,
 * matching every other module's read side.
 *
 * No "+ New Reading" action here, mirroring Cleaning/Maintenance's own reasoning: scope §11's
 * capture flow (photo -> mock OCR) only ever happens from within an Inspection question (the
 * MeterReading answer type, Sub-phase D) or a standalone create the wizard doesn't expose on
 * this page either - taking a meter photo needs a live camera/file picker moment, not a form.
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
import { METER_TYPE_OPTIONS } from "../../constants/meterReadingOptions";
import { listMeterReadings } from "../../services/meterReadingService";
import { listProperties } from "../../services/propertyService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function MeterReadingsListPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [propertyId, setPropertyId] = useState("");
  const [meterType, setMeterType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  const [propertyOptions, setPropertyOptions] = useState([]);

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
      })
      .catch(() => setPropertyOptions([]));
  }, []);

  const loadMeterReadings = useCallback(() => {
    setLoading(true);
    setError(null);
    listMeterReadings({ page, pageSize: PAGE_SIZE, propertyId: propertyId || undefined, meterType: meterType || undefined })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, propertyId, meterType]);

  useEffect(() => {
    loadMeterReadings();
  }, [loadMeterReadings]);

  function handleClearFilters() {
    setPropertyId("");
    setMeterType("");
    setPage(1);
  }

  return (
    <div>
      <PageHeader title="Meter Readings" description="Meter readings recorded across your company." />

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
          label="Meter type"
          name="meterType"
          value={meterType}
          onChange={(event) => {
            setMeterType(event.target.value);
            setPage(1);
          }}
          placeholder="Any type"
          options={METER_TYPE_OPTIONS}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadMeterReadings}
        emptyMessage="No meter readings match your filters."
        rows={items}
        getRowKey={(row) => row.MeterReadingId}
        columns={[
          {
            key: "MeterType",
            header: "Meter",
            render: (row) => <Link to={`/meter-readings/${row.MeterReadingId}`}>{row.MeterType}</Link>,
          },
          {
            key: "PropertyName",
            header: "Property",
            render: (row) => <Link to={`/properties/${row.PropertyId}`}>{row.PropertyName}</Link>,
          },
          { key: "ReadingDateTime", header: "Date", render: (row) => new Date(row.ReadingDateTime).toLocaleDateString() },
          { key: "AIDetectedReading", header: "AI reading", render: (row) => row.AIDetectedReading ?? "—" },
          { key: "ConfirmedReading", header: "Confirmed reading", render: (row) => row.ConfirmedReading ?? "—" },
          {
            key: "status",
            header: "Status",
            render: (row) => <StatusBadge status={row.ConfirmedReading != null ? "Confirmed" : "Unconfirmed"} />,
          },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} onPageChange={setPage} />
      )}
    </div>
  );
}
