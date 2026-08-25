/**
 * Wraps /api/risk-assessments and /api/risk-matrix-levels - see app/api/risk.py. createRiskAssessment
 * is Sub-phase C's quick-create modal; getRiskMatrix is Sub-phase F's Review screen (its
 * `LevelName`s - e.g. "Low"/"Medium"/"High"/"Critical" from the seeded global default - populate
 * the OverallRiskRating select, matching app/schemas/inspection.py's own reasoning: an
 * inspector's overall rating should use the same vocabulary their company's configurable matrix
 * does, not a hardcoded list). The full Risk Register module is one of Phase 16's remaining
 * pages, not built yet.
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

export async function getRiskMatrix() {
  const { data } = await apiClient.get("/risk-matrix-levels");
  return data; // RiskMatrixLevelResponse[]
}
