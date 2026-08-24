/**
 * Routing flow, explained:
 * - "/login" and "/unauthorized" are public.
 * - Everything else is nested under <ProtectedRoute />, which blocks rendering until
 *   AuthContext confirms whether the user is logged in (see routes/ProtectedRoute.jsx) and
 *   redirects to /login if not.
 * - Authenticated routes are further nested under <MainLayout />, which renders the sidebar/
 *   header shell once, around whichever page is active (see layouts/MainLayout.jsx).
 * - "*" catches any URL that doesn't match one of the routes above.
 *
 * Only Dashboard exists as a real page so far - this file grows one nested <Route> block per
 * module as each module's frontend gets built (same incremental order as the backend), the
 * same shape PropertyManager's App.jsx used across its own modules. Dashboard needs no
 * `allowedRoles` (constants/roles.js - GET /api/dashboard has no role gate at all), so it's the
 * one route so far NOT wrapped in a second, role-narrowing ProtectedRoute.
 */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { MainLayout } from "./layouts/MainLayout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { UnauthorizedPage } from "./pages/UnauthorizedPage";
import { NotFoundPage } from "./pages/NotFoundPage";

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/unauthorized" element={<UnauthorizedPage />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<MainLayout />}>
                <Route path="/" element={<DashboardPage />} />
              </Route>
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
