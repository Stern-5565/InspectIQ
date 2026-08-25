/**
 * Wraps /api/properties/{id}/cleaning-areas and /api/inspections/{id}/cleaning, plus the
 * standalone /api/cleaning-inspections list/detail added alongside this module's frontend - see
 * app/api/cleaning.py. listAreas/createCleaningInspection started as Sub-phase E's "Grade
 * Cleaning Area" gateway action; everything else here is the standalone Cleaning module
 * (areas config on PropertyDetailPage, grading history list/detail) built afterward.
 */
import { apiClient } from "../api/client";

export async function listCleaningAreas(propertyId, { includeInactive } = {}) {
  const { data } = await apiClient.get(`/properties/${propertyId}/cleaning-areas`, {
    params: { include_inactive: includeInactive || undefined },
  });
  return data; // CleaningAreaResponse[]
}

export async function createCleaningArea(propertyId, { areaName, areaType }) {
  const { data } = await apiClient.post(`/properties/${propertyId}/cleaning-areas`, {
    AreaName: areaName,
    AreaType: areaType,
  });
  return data; // CleaningAreaResponse
}

export async function updateCleaningArea(areaId, payload) {
  const { data } = await apiClient.patch(`/cleaning-areas/${areaId}`, payload);
  return data; // CleaningAreaResponse
}

export async function createCleaningInspection(inspectionId, { cleaningAreaId, grade, cleaningRequired, urgent, notes }) {
  const { data } = await apiClient.post(`/inspections/${inspectionId}/cleaning`, {
    CleaningAreaId: cleaningAreaId,
    Grade: grade,
    CleaningRequired: cleaningRequired,
    Urgent: urgent,
    Notes: notes || undefined,
  });
  return data; // CleaningInspectionResponse
}

export async function listAllCleaningInspections({ page = 1, pageSize = 20, propertyId, grade, status } = {}) {
  const { data } = await apiClient.get("/cleaning-inspections", {
    params: {
      page,
      page_size: pageSize,
      property_id: propertyId || undefined,
      grade: grade || undefined,
      status: status || undefined,
    },
  });
  return data; // PaginatedResponse<CleaningInspectionSummaryResponse>
}

export async function getCleaningInspectionDetail(cleaningInspectionId) {
  const { data } = await apiClient.get(`/cleaning-inspections/${cleaningInspectionId}`);
  return data; // CleaningInspectionSummaryResponse (PropertyId/AreaName included)
}

/** ONE combined PATCH covering every field including Status/AssignedUserId - no separate
 * assign/status endpoints, matching app/schemas/cleaning.py's CleaningInspectionUpdate. */
export async function updateCleaningInspection(cleaningInspectionId, payload) {
  const { data } = await apiClient.patch(`/cleaning-inspections/${cleaningInspectionId}`, payload);
  return data; // CleaningInspectionResponse
}
