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
