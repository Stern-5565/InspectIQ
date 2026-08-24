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
};

export function StatusBadge({ status, tone }) {
  const resolvedTone = tone ?? TONE_BY_STATUS[status?.toLowerCase()] ?? "neutral";
  return <span className={`status-badge status-badge--${resolvedTone}`}>{status}</span>;
}
