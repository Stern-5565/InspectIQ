/**
 * Wraps /api/risk-assessments and /api/risk-matrix-levels - see app/api/risk.py.
 * createRiskAssessment started as Sub-phase C's quick-create modal (only InspectionResponseId/
 * Hazard/Likelihood/Severity/Notes) and is generalized here to the full RiskAssessmentCreate
 * field set for the standalone Risk Register's own create form - existing callers passing only
 * the original fields are unaffected, since every new parameter is optional. getRiskMatrix was
 * Sub-phase F's Review screen; it's this module's own reference data too (RiskLevel options and
 * badge context both come from it, not a hardcoded list).
 */
import { apiClient } from "../api/client";

export async function createRiskAssessment({
  propertyId,
  inspectionResponseId,
  location,
  hazard,
  whoMayBeAffected,
  existingControls,
  likelihood,
  severity,
  additionalActionRequired,
  responsiblePersonUserId,
  targetCompletionDate,
  notes,
}) {
  const { data } = await apiClient.post("/risk-assessments", {
    PropertyId: propertyId || undefined,
    InspectionResponseId: inspectionResponseId || undefined,
    Location: location || undefined,
    Hazard: hazard,
    WhoMayBeAffected: whoMayBeAffected || undefined,
    ExistingControls: existingControls || undefined,
    Likelihood: likelihood,
    Severity: severity,
    AdditionalActionRequired: additionalActionRequired || undefined,
    ResponsiblePersonUserId: responsiblePersonUserId || undefined,
    TargetCompletionDate: targetCompletionDate || undefined,
    Notes: notes || undefined,
  });
  return data; // RiskAssessmentResponse
}

export async function listRiskAssessments({ page = 1, pageSize = 20, status, riskLevel, propertyId } = {}) {
  const { data } = await apiClient.get("/risk-assessments", {
    params: {
      page,
      page_size: pageSize,
      status: status || undefined,
      risk_level: riskLevel || undefined,
      property_id: propertyId || undefined,
    },
  });
  return data; // PaginatedResponse<RiskAssessmentResponse>
}

export async function getRiskAssessment(riskAssessmentId) {
  const { data } = await apiClient.get(`/risk-assessments/${riskAssessmentId}`);
  return data; // RiskAssessmentResponse
}

/** Administrator/Manager only - ONE combined PATCH covering every field including Status/
 * ResponsiblePersonUserId/TargetCompletionDate (app/schemas/risk_assessment.py's own
 * RiskAssessmentUpdate - no separate assign/status endpoints the way Maintenance has). */
export async function updateRiskAssessment(riskAssessmentId, payload) {
  const { data } = await apiClient.patch(`/risk-assessments/${riskAssessmentId}`, payload);
  return data; // RiskAssessmentResponse
}

export async function getRiskMatrix() {
  const { data } = await apiClient.get("/risk-matrix-levels");
  return data; // RiskMatrixLevelResponse[]
}

/** Administrator/Manager only. Creating a level always creates a COMPANY-specific row (never a
 * global-default one - those are seeded once, company-less, and read-only through this API) -
 * app/schemas/risk_matrix_level.py's own RiskMatrixLevelCreate docstring. */
export async function createRiskMatrixLevel({ minScore, maxScore, levelName, sortOrder, colorHint }) {
  const { data } = await apiClient.post("/risk-matrix-levels", {
    MinScore: minScore,
    MaxScore: maxScore,
    LevelName: levelName,
    SortOrder: sortOrder ?? 0,
    ColorHint: colorHint || undefined,
  });
  return data; // RiskMatrixLevelResponse
}

/** Administrator/Manager only. Scoped server-side to THIS company's own rows - a global-default
 * row's ID 404s here (app/repositories/risk_repository.py's get_risk_matrix_level_by_id). */
export async function updateRiskMatrixLevel(riskMatrixLevelId, payload) {
  const { data } = await apiClient.patch(`/risk-matrix-levels/${riskMatrixLevelId}`, payload);
  return data; // RiskMatrixLevelResponse
}
