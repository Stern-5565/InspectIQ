/**
 * Wraps /api/risk-assessments - see app/api/risk.py. Only createRiskAssessment exists so far,
 * for Sub-phase C's quick-create modal - the full Risk Register module is one of Phase 16's
 * remaining pages, not built yet.
 */
import { apiClient } from "../api/client";

export async function createRiskAssessment({ inspectionResponseId, hazard, likelihood, severity, notes }) {
  const { data } = await apiClient.post("/risk-assessments", {
    InspectionResponseId: inspectionResponseId,
    Hazard: hazard,
    Likelihood: likelihood,
    Severity: severity,
    Notes: notes || undefined,
  });
  return data; // RiskAssessmentResponse
}
