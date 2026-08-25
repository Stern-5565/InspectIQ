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
 * Dashboard + Properties/Units + Inspection Templates + Inspections exist as real pages so far
 * - this file grows one nested <Route> block per module as each module's frontend gets built
 * (same incremental order as the backend), the same shape PropertyManager's App.jsx used across
 * its own modules. Dashboard needs no `allowedRoles` (constants/roles.js - GET /api/dashboard
 * has no role gate at all), so it's the one route NOT wrapped in a second, role-narrowing
 * ProtectedRoute. Properties' VIEW routes are the same way (no CAN_VIEW_PROPERTIES exists - any
 * company member can view); only the create/edit routes are nested under a second
 * ProtectedRoute with `allowedRoles={CAN_MANAGE_PROPERTIES}`. Units have no routes of their own
 * - they're managed entirely from within PropertyDetailPage (see that file's own header comment
 * for why). Inspection Templates are read-only end to end (no mutation exists in the backend
 * yet - app/api/inspection_templates.py's own module docstring), so neither of its two routes
 * is nested under a role-narrowing ProtectedRoute at all.
 *
 * Inspections: viewing (list/get/sections/questions/review) has no role restriction either -
 * only `/inspections/new` (starting one) is gated to `CAN_CONDUCT_INSPECTIONS`. The Sections,
 * Question, and Review screens are all nested under `InspectionWizardLayout` (a layout route,
 * same pattern as `MainLayout` one level up) so all three share one fetch of the inspection
 * instead of each re-fetching it - see that file's own header comment. Whether a given user can
 * actually EDIT the one inspection they're looking at (not just any inspection) is a per-record
 * check (`ensure_can_edit` on the backend) that `allowedRoles` can't express, so
 * `InspectionWizardLayout` computes `canEdit` itself and the question/sections/review pages read
 * it from `useOutletContext()` rather than a route-level gate.
 *
 * Maintenance: view (list/detail) has no role restriction, the same shape as every module above.
 * Only `/maintenance-issues/:id/edit` (general field edits) is route-gated to
 * `CAN_MANAGE_MAINTENANCE` - assign/status/notes/photos are all per-record checks
 * (`ensure_can_edit`-shaped, mirroring the same reasoning as Inspections' `canEdit`) that
 * `MaintenanceIssueDetailPage` computes itself, the same pattern as `InspectionWizardLayout`. No
 * `/maintenance-issues/new` route exists - scope §17 frames issue creation entirely as the
 * wizard's job (Sub-phase C's quick-create), not a standalone flow this module adds.
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
import { InspectionsListPage } from "./pages/inspections/InspectionsListPage";
import { StartInspectionPage } from "./pages/inspections/StartInspectionPage";
import { InspectionWizardLayout } from "./pages/inspections/InspectionWizardLayout";
import { InspectionSectionsPage } from "./pages/inspections/InspectionSectionsPage";
import { InspectionQuestionPage } from "./pages/inspections/InspectionQuestionPage";
import { InspectionReviewPage } from "./pages/inspections/InspectionReviewPage";
import { MaintenanceIssuesListPage } from "./pages/maintenance/MaintenanceIssuesListPage";
import { MaintenanceIssueDetailPage } from "./pages/maintenance/MaintenanceIssueDetailPage";
import { MaintenanceIssueFormPage } from "./pages/maintenance/MaintenanceIssueFormPage";
import { CAN_MANAGE_PROPERTIES, CAN_CONDUCT_INSPECTIONS, CAN_MANAGE_MAINTENANCE } from "./constants/roles";

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

                <Route path="/inspections" element={<InspectionsListPage />} />

                <Route element={<ProtectedRoute allowedRoles={CAN_CONDUCT_INSPECTIONS} />}>
                  <Route path="/inspections/new" element={<StartInspectionPage />} />
                </Route>

                <Route path="/inspections/:id" element={<InspectionWizardLayout />}>
                  <Route index element={<InspectionSectionsPage />} />
                  <Route path="sections/:sectionIndex/questions/:questionIndex" element={<InspectionQuestionPage />} />
                  <Route path="review" element={<InspectionReviewPage />} />
                </Route>

                <Route path="/maintenance-issues" element={<MaintenanceIssuesListPage />} />
                <Route path="/maintenance-issues/:id" element={<MaintenanceIssueDetailPage />} />

                <Route element={<ProtectedRoute allowedRoles={CAN_MANAGE_MAINTENANCE} />}>
                  <Route path="/maintenance-issues/:id/edit" element={<MaintenanceIssueFormPage />} />
                </Route>
              </Route>
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
