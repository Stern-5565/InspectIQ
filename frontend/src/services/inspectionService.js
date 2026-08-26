/**
 * Wraps /api/inspections - see app/api/inspections.py. "Resume" isn't a separate operation
 * (that file's own module docstring) - resuming an in-progress inspection is just getInspection
 * again, since every answer/note/N-A change saves immediately, nothing is staged client-side.
 */
import { apiClient } from "../api/client";

export async function listInspections({ page = 1, pageSize = 20, propertyId, status, inspectorUserId } = {}) {
  const { data } = await apiClient.get("/inspections", {
    params: {
      page,
      page_size: pageSize,
      property_id: propertyId || undefined,
      status: status || undefined,
      inspector_user_id: inspectorUserId || undefined,
    },
  });
  return data; // PaginatedResponse<InspectionSummaryResponse>
}

export async function startInspection({ propertyId, inspectionTemplateId, inspectionType, inspectionDate }) {
  const { data } = await apiClient.post("/inspections", {
    PropertyId: propertyId,
    InspectionTemplateId: inspectionTemplateId,
    InspectionType: inspectionType || undefined,
    InspectionDate: inspectionDate || undefined,
  });
  return data; // InspectionDetailResponse
}

export async function getInspection(inspectionId) {
  const { data } = await apiClient.get(`/inspections/${inspectionId}`);
  return data; // InspectionDetailResponse - Sections -> Responses, already grouped/ordered
}

/** GeneralNotes/OverallCondition/OverallRiskRating - the Inspection Review screen's own
 * summary fields, distinct from any per-question InspectionResponse. */
export async function updateInspectionSummary(inspectionId, payload) {
  const { data } = await apiClient.patch(`/inspections/${inspectionId}`, payload);
  return data;
}

/** Covers answer/notes/mark-N-A in one call, matching the backend's own unified endpoint. */
export async function updateResponse(inspectionId, responseId, payload) {
  const { data } = await apiClient.patch(`/inspections/${inspectionId}/responses/${responseId}`, payload);
  return data; // InspectionResponseSchema
}

export async function submitInspection(inspectionId) {
  const { data } = await apiClient.post(`/inspections/${inspectionId}/submit`);
  return data; // InspectionDetailResponse
}

/** Phase 17 - only ever succeeds once the inspection is Submitted (the backend's own 409
 * otherwise); same responseType: "blob" pattern mediaService.downloadMediaBlob established. */
export async function downloadInspectionReport(inspectionId) {
  const { data } = await apiClient.get(`/inspections/${inspectionId}/report`, { responseType: "blob" });
  return data; // PDF Blob
}
