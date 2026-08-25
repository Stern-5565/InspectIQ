/** Mirrors app/schemas/enums.py's MaintenanceCategory exactly. */
export const MAINTENANCE_CATEGORY_OPTIONS = [
  { value: "Electrical", label: "Electrical" },
  { value: "Plumbing", label: "Plumbing" },
  { value: "Heating", label: "Heating" },
  { value: "FireSafety", label: "Fire Safety" },
  { value: "EmergencyLighting", label: "Emergency Lighting" },
  { value: "Cleaning", label: "Cleaning" },
  { value: "Garden", label: "Garden" },
  { value: "Structural", label: "Structural" },
  { value: "DoorsWindows", label: "Doors / Windows" },
  { value: "PestControl", label: "Pest Control" },
  { value: "Decoration", label: "Decoration" },
  { value: "Appliance", label: "Appliance" },
  { value: "Security", label: "Security" },
  { value: "Other", label: "Other" },
];

/** Mirrors app/schemas/enums.py's MaintenancePriority exactly. */
export const MAINTENANCE_PRIORITY_OPTIONS = [
  { value: "Low", label: "Low" },
  { value: "Medium", label: "Medium" },
  { value: "High", label: "High" },
  { value: "Urgent", label: "Urgent" },
  { value: "Emergency", label: "Emergency" },
];

/** Mirrors app/schemas/enums.py's MaintenanceIssueStatus exactly. Order matches the workflow's
 * natural progression, not alphabetical - used both for the status SELECT and for the filter. */
export const MAINTENANCE_STATUS_OPTIONS = [
  { value: "Open", label: "Open" },
  { value: "Assigned", label: "Assigned" },
  { value: "InProgress", label: "In Progress" },
  { value: "Waiting", label: "Waiting" },
  { value: "Completed", label: "Completed" },
  { value: "Closed", label: "Closed" },
];
