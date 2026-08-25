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
 * Dashboard + Properties/Units + Inspection Templates exist as real pages so far - this file
 * grows one nested <Route> block per module as each module's frontend gets built (same
 * incremental order as the backend), the same shape PropertyManager's App.jsx used across its
 * own modules. Dashboard needs no `allowedRoles` (constants/roles.js - GET /api/dashboard has
 * no role gate at all), so it's the one route NOT wrapped in a second, role-narrowing
 * ProtectedRoute. Properties' VIEW routes are the same way (no CAN_VIEW_PROPERTIES exists - any
 * company member can view); only the create/edit routes are nested under a second
 * ProtectedRoute with `allowedRoles={CAN_MANAGE_PROPERTIES}`. Units have no routes of their own
 * - they're managed entirely from within PropertyDetailPage (see that file's own header comment
 * for why). Inspection Templates are read-only end to end (no mutation exists in the backend
 * yet - app/api/inspection_templates.py's own module docstring), so neither of its two routes
 * is nested under a role-narrowing ProtectedRoute at all.
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
import { PropertiesListPage } from "./pages/properties/PropertiesListPage";
import { PropertyDetailPage } from "./pages/properties/PropertyDetailPage";
import { PropertyFormPage } from "./pages/properties/PropertyFormPage";
import { InspectionTemplatesListPage } from "./pages/inspection-templates/InspectionTemplatesListPage";
import { InspectionTemplateDetailPage } from "./pages/inspection-templates/InspectionTemplateDetailPage";
import { CAN_MANAGE_PROPERTIES } from "./constants/roles";

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

                <Route path="/properties" element={<PropertiesListPage />} />
                <Route path="/properties/:id" element={<PropertyDetailPage />} />

                <Route element={<ProtectedRoute allowedRoles={CAN_MANAGE_PROPERTIES} />}>
                  <Route path="/properties/new" element={<PropertyFormPage />} />
                  <Route path="/properties/:id/edit" element={<PropertyFormPage />} />
                </Route>

                <Route path="/inspection-templates" element={<InspectionTemplatesListPage />} />
                <Route path="/inspection-templates/:id" element={<InspectionTemplateDetailPage />} />
              </Route>
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
