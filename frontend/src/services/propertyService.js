/**
 * Wraps /api/properties - see app/api/properties.py. Deactivate is soft-delete only
 * (IsActive -> false via a dedicated POST, not DELETE) with no reactivate endpoint - the
 * backend has none (docs/DATABASE.md's soft-delete-only design, PROJECT_PLAN.md §13).
 */
import { apiClient } from "../api/client";

export async function listProperties({
  page = 1,
  pageSize = 20,
  search,
  propertyType,
  propertyStatus,
  includeInactive,
} = {}) {
  const { data } = await apiClient.get("/properties", {
    params: {
      page,
      page_size: pageSize,
      search: search || undefined,
      property_type: propertyType || undefined,
      property_status: propertyStatus || undefined,
      include_inactive: includeInactive || undefined,
    },
  });
  return data; // PaginatedResponse<PropertyResponse>
}

export async function getProperty(propertyId) {
  const { data } = await apiClient.get(`/properties/${propertyId}`);
  return data;
}

export async function createProperty(payload) {
  const { data } = await apiClient.post("/properties", payload);
  return data;
}

export async function updateProperty(propertyId, payload) {
  const { data } = await apiClient.patch(`/properties/${propertyId}`, payload);
  return data;
}

export async function deactivateProperty(propertyId) {
  const { data } = await apiClient.post(`/properties/${propertyId}/deactivate`);
  return data;
}
