/** Wraps /api/properties/{id}/units and /api/units/{id} - see app/api/units.py. */
import { apiClient } from "../api/client";

export async function listUnits(propertyId, { page = 1, pageSize = 20, occupancyStatus, includeInactive } = {}) {
  const { data } = await apiClient.get(`/properties/${propertyId}/units`, {
    params: {
      page,
      page_size: pageSize,
      occupancy_status: occupancyStatus || undefined,
      include_inactive: includeInactive || undefined,
    },
  });
  return data; // PaginatedResponse<UnitResponse>
}

export async function createUnit(propertyId, payload) {
  const { data } = await apiClient.post(`/properties/${propertyId}/units`, payload);
  return data;
}

export async function getUnit(unitId) {
  const { data } = await apiClient.get(`/units/${unitId}`);
  return data;
}

export async function updateUnit(unitId, payload) {
  const { data } = await apiClient.patch(`/units/${unitId}`, payload);
  return data;
}

export async function updateUnitOccupancy(unitId, occupancyStatus) {
  const { data } = await apiClient.patch(`/units/${unitId}/occupancy`, { OccupancyStatus: occupancyStatus });
  return data;
}
