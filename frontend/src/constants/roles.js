/**
 * Mirrors backend/app/security/roles.py exactly - role name constants plus, per module, which
 * roles can view vs. manage it. Built incrementally as each module's frontend gets built (same
 * order as the backend), not all at once, so this file only has what's actually used so far.
 */
export const ADMINISTRATOR = "Administrator";
export const MANAGER = "Manager";
export const INSPECTOR = "Inspector";
export const MAINTENANCE = "Maintenance";
export const VIEWER = "Viewer";

export const ALL_ROLES = [ADMINISTRATOR, MANAGER, INSPECTOR, MAINTENANCE, VIEWER];

// Dashboard: GET /api/dashboard has no role restriction at all (app/api/dashboard.py) - a
// dashboard has no natural "mutate" action, so every module's read side lands here the same
// way. No CAN_VIEW_DASHBOARD constant is needed as a result; ProtectedRoute for "/" is used
// without an `allowedRoles` prop.

// Properties + Units: view = any authenticated company member (app/api/properties.py's own
// module docstring - the schema has no per-property assignment table, so "Inspectors can view
// properties they have permission to inspect" is interpreted as company membership), mutate =
// Administrator/Manager only. No CAN_VIEW_PROPERTIES constant, same reasoning as Dashboard -
// every role needs it, so ProtectedRoute is used without `allowedRoles` for the view routes.
// Units share the exact same shape (app/api/units.py's own docstring says so explicitly), so
// one constant covers both - no separate CAN_MANAGE_UNITS.
export const CAN_MANAGE_PROPERTIES = [ADMINISTRATOR, MANAGER];

// Inspections: viewing (list/get) has no role restriction, same as every module above -
// Maintenance/Viewer can still see an inspection's results. Starting/answering/submitting is
// narrower (Administrator/Manager/Inspector - app/api/inspections.py's _conduct_inspections),
// but that role check alone is NOT sufficient to decide whether to show editing controls for
// one SPECIFIC inspection - the backend's own ensure_can_edit additionally requires being that
// inspection's own assigned inspector (or Admin/Manager). That per-record check can't be
// expressed as a static role list the way ProtectedRoute's `allowedRoles` works, so pages that
// need it compute `canEditThisInspection` at runtime (CAN_MANAGE_PROPERTIES-equivalent roles,
// OR `user.UserId === inspection.InspectorUserId`) instead of relying on this constant alone -
// see pages/inspections/InspectionWizardLayout.jsx.
export const CAN_CONDUCT_INSPECTIONS = [ADMINISTRATOR, MANAGER, INSPECTOR];

// Maintenance: viewing (list/get/timeline) has no role restriction, same as every module above.
// General field edits (Title/Description/Category/Priority/DueDate/Notes) and assignment are
// Administrator/Manager only, route-gated - app/services/maintenance_service.py's own module
// docstring. Status changes/notes/photos are narrower still (the issue's own AssignedUserId, or
// Admin/Manager) but that's a PER-RECORD check the same way Inspections' `canEdit` is - not a
// static role list this constant could express, so pages needing it compute it at runtime from
// `user.UserId === issue.AssignedUserId` OR CAN_MANAGE_MAINTENANCE, the same pattern
// InspectionWizardLayout.jsx already established for `canEdit`.
export const CAN_MANAGE_MAINTENANCE = [ADMINISTRATOR, MANAGER];

// Risk Register: viewing (list/get, RiskMatrixLevels included) has no role restriction. Create
// is CAN_CONDUCT_INSPECTIONS (identifying a hazard is the same "raise a problem" tier
// Maintenance's create uses - app/services/risk_service.py's own module docstring), so no
// separate constant is needed for it - reuse CAN_CONDUCT_INSPECTIONS directly. Update (EVERY
// field, including Status/ResponsiblePersonUserId, in one combined PATCH - there's no
// Maintenance-style three-tier split here, since RiskAssessment.InspectionId is nullable and
// scope §19 names no audit-trail requirement) is Administrator/Manager only, a static role gate
// with no per-record carve-out - unlike Maintenance's `canWork`, nobody else can edit a risk
// assessment just by being its ResponsiblePersonUserId.
export const CAN_MANAGE_RISK = [ADMINISTRATOR, MANAGER];
