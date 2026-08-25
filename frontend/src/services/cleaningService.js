/**
 * Wraps /api/properties/{id}/cleaning-areas and /api/inspections/{id}/cleaning - see
 * app/api/cleaning.py. Only what Sub-phase E's "Grade Cleaning Area" gateway action needs
 * (listAreas, createCleaningInspection) - the CleaningAreas management screen (create/edit an
 * area) and the standalone Cleaning module are still unbuilt Phase 16 pages.
 */
import { apiClient } from "../api/client";

export async function listCleaningAreas(propertyId) {
  const { data } = await apiClient.get(`/properties/${propertyId}/cleaning-areas`);
  return data; // CleaningAreaResponse[]
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
