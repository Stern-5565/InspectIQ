import { Link } from "react-router-dom";
import { getDefaultLandingPath } from "../utilities/permissions";

/**
 * Unused by any route yet - no module built so far restricts by role (Dashboard is open to
 * every authenticated user). Kept ready for the first module that does, same as
 * ProtectedRoute's `allowedRoles` prop.
 */
export function UnauthorizedPage() {
  return (
    <div className="status-page">
      <h1>403 - Not permitted</h1>
      <p>Your account doesn't have access to this page.</p>
      <Link to={getDefaultLandingPath()} className="button">
        Back to dashboard
      </Link>
    </div>
  );
}
