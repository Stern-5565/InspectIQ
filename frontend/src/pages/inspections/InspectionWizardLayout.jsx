/**
 * Wraps every inspection-detail route (Sections, Question) as a layout route - fetches the
 * inspection (and its property, for the header) ONCE, then shares it via React Router's
 * `<Outlet context={...}>` mechanism so navigating between questions doesn't re-fetch the
 * whole inspection on every tap (the "few taps as possible" requirement extends to network
 * latency, not just UI taps). Children read it with `useOutletContext()` and call
 * `applyResponseUpdate`/`applyInspectionUpdate` to splice a PATCH's response back into local
 * state instead of triggering a full reload.
 *
 * `canEdit` is computed here once, not per-page - the assigned inspector or an Administrator/
 * Manager (mirrors app/services/inspection_service.py's ensure_can_edit exactly; a plain
 * CAN_CONDUCT_INSPECTIONS role check alone is NOT enough, since a different Inspector at the
 * same company must NOT get edit controls for someone else's inspection - see
 * constants/roles.js's own comment on this).
 *
 * `canRaiseIssues` is a DIFFERENT, wider check, also computed once here - Sub-phase C's Create
 * Maintenance Issue/Create Risk quick-creates deliberately do NOT use `canEdit`.
 * maintenance_service.create_issue/risk_service.create_risk_assessment resolve the inspection
 * via inspection_service.get_inspection (a VIEW-level lookup), never ensure_can_edit - so any
 * Administrator/Manager/Inspector at the company can raise an issue against any response, not
 * just the inspector assigned to that specific inspection. Confirmed by reading both service
 * functions before building the frontend gate, not assumed from the answering/photos precedent.
 */
import { useCallback, useEffect, useState } from "react";
import { Outlet, useParams } from "react-router-dom";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { ADMINISTRATOR, MANAGER, CAN_CONDUCT_INSPECTIONS } from "../../constants/roles";
import { getInspection } from "../../services/inspectionService";
import { getProperty } from "../../services/propertyService";
import { getErrorMessage } from "../../utilities/apiError";

export function InspectionWizardLayout() {
  const { id } = useParams();
  const { user } = useAuth();

  const [inspection, setInspection] = useState(null);
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getInspection(id)
      .then((data) => {
        setInspection(data);
        return getProperty(data.PropertyId);
      })
      .then(setProperty)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // Splices one updated InspectionResponseSchema back into local state - avoids re-fetching
  // the whole inspection after every answer/notes/N-A save.
  function applyResponseUpdate(updatedResponse) {
    setInspection((prev) => ({
      ...prev,
      Sections: prev.Sections.map((section) => ({
        ...section,
        Responses: section.Responses.map((r) =>
          r.InspectionResponseId === updatedResponse.InspectionResponseId ? updatedResponse : r,
        ),
      })),
    }));
  }

  // Merges a partial InspectionDetailResponse (from the summary PATCH or submit) into state.
  function applyInspectionUpdate(updatedInspection) {
    setInspection(updatedInspection);
  }

  if (loading) {
    return <LoadingSpinner fullPage label="Loading inspection…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={load} />;
  }

  const canEdit = hasAnyRole(user, [ADMINISTRATOR, MANAGER]) || user.UserId === inspection.InspectorUserId;
  const canRaiseIssues = hasAnyRole(user, CAN_CONDUCT_INSPECTIONS);

  return (
    <Outlet
      context={{
        inspection,
        property,
        canEdit,
        canRaiseIssues,
        reload: load,
        applyResponseUpdate,
        applyInspectionUpdate,
      }}
    />
  );
}
