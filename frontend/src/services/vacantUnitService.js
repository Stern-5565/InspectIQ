/**
 * Wraps /api/inspections/{id}/vacant-unit-inspections, plus the standalone
 * /api/vacant-unit-inspections list/detail added alongside this module's frontend - see
 * app/api/vacant_units.py. createVacantUnitInspection started as Sub-phase E's "Add Empty Unit"
 * gateway action; listAllVacantUnitInspections/getVacantUnitInspectionDetail/
 * updateVacantUnitInspection are the standalone Vacant Units module (browse/edit history) built
 * afterward.
 */
import { apiClient } from "../api/client";

export async function createVacantUnitInspection(inspectionId, payload) {
  const { data } = await apiClient.post(`/inspections/${inspectionId}/vacant-unit-inspections`, payload);
  return data; // VacantUnitInspectionResponse
}

export async function listAllVacantUnitInspections({ page = 1, pageSize = 20, propertyId } = {}) {
  const { data } = await apiClient.get("/vacant-unit-inspections", {
    params: { page, page_size: pageSize, property_id: propertyId || undefined },
  });
  return data; // PaginatedResponse<VacantUnitInspectionSummaryResponse>
}

export async function getVacantUnitInspectionDetail(vacantUnitInspectionId) {
  const { data } = await apiClient.get(`/vacant-unit-inspections/${vacantUnitInspectionId}`);
  return data; // VacantUnitInspectionSummaryResponse (PropertyId/UnitNumber included)
}

export async function updateVacantUnitInspection(vacantUnitInspectionId, payload) {
  const { data } = await apiClient.patch(`/vacant-unit-inspections/${vacantUnitInspectionId}`, payload);
  return data; // VacantUnitInspectionResponse
}
