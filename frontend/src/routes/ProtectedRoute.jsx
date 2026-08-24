/**
 * Route guard used as a layout route: <Route element={<ProtectedRoute />}> wraps every child
 * route that requires a logged-in user, rendering them via <Outlet /> only once auth is
 * confirmed.
 *
 * `allowedRoles` is optional - no route passes it yet, since the only gated route so far
 * (Dashboard) has no role restriction (constants/roles.js). Built and demonstrated here anyway
 * so each future module can opt in just by passing the roles it needs, without touching this
 * file again - same pattern validated on PropertyManager's frontend.
 */
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { hasAnyRole } from "../utilities/permissions";

export function ProtectedRoute({ allowedRoles }) {
  const { isAuthenticated, initializing, user } = useAuth();
  const location = useLocation();

  if (initializing) {
    return <LoadingSpinner fullPage label="Checking your session…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (allowedRoles && !hasAnyRole(user, allowedRoles)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
}
