/**
 * Wraps /api/inspections/{id}/vacant-unit-inspections - see app/api/vacant_units.py. Only
 * createVacantUnitInspection is needed so far (Sub-phase E's "Add Empty Unit" gateway action) -
 * services/unitService.js's existing listUnits already covers picking which unit, and the
 * standalone Vacant Units module is still an unbuilt Phase 16 page.
 */
import { apiClient } from "../api/client";

export async function createVacantUnitInspection(inspectionId, payload) {
  const { data } = await apiClient.post(`/inspections/${inspectionId}/vacant-unit-inspections`, payload);
  return data; // VacantUnitInspectionResponse
}
