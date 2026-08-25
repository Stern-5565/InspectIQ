/**
 * Renders any of the backend's status strings (PropertyStatus, OccupancyStatus, and future
 * modules' Status/Priority/RiskLevel/Grade fields) as a small colored pill, inferring a tone
 * automatically from the value so most call sites don't need to think about color at all:
 * <StatusBadge status={property.PropertyStatus} />.
 *
 * The map only needs to be "good enough" - anything not covered falls back to neutral grey
 * rather than guessing wrong; any call site can override with the `tone` prop. Grown
 * incrementally as each module's frontend adds its own status values, not written all at once
 * for enums that don't have a UI yet.
 */
const TONE_BY_STATUS = {
  // Property/Unit (this module)
  active: "success",
  occupied: "success",
  "for sale": "info",
  "under refurbishment": "warning",
  "not in use": "neutral",
  vacant: "danger",
  unavailable: "danger",
  unknown: "neutral",
  inactive: "danger",
  other: "neutral",
  // Maintenance status/priority
  open: "warning",
  assigned: "info",
  inprogress: "info",
  waiting: "warning",
  completed: "success",
  closed: "neutral",
  emergency: "danger",
  urgent: "danger",
  high: "warning",
  medium: "info",
  low: "neutral",
  // Risk Register (RiskLevel names come from each company's own configurable matrix, but the
  // seeded global default and every demo company use these four - falls back to neutral for
  // any company-specific name that doesn't match)
  critical: "danger",
  actionplanned: "warning",
  // Cleaning (CleaningInspectionStatus; Grade is a single letter A-E, scope §16's own
  // Excellent/Good/Needs-Attention/Poor/Critical meanings)
  pending: "warning",
  a: "success",
  b: "success",
  c: "warning",
  d: "warning",
  e: "danger",
  // Meter Readings (a derived "Confirmed"/"Unconfirmed" label, not a real DB enum column -
  // ConfirmedReading is just null-or-not on the record)
  confirmed: "success",
  unconfirmed: "warning",
};

export function StatusBadge({ status, tone }) {
  const resolvedTone = tone ?? TONE_BY_STATUS[status?.toLowerCase()] ?? "neutral";
  return <span className={`status-badge status-badge--${resolvedTone}`}>{status}</span>;
}
