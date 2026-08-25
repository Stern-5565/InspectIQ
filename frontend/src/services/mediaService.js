/**
 * Wraps /api/media - see app/api/media.py. One generic polymorphic service, not one per
 * EntityType, matching the backend's own single-router design (Phase 9). Every caller supplies
 * entityType/entityId (one of app/schemas/media_file.py's ENTITY_TYPES) - authorization is
 * resolved server-side per request, this file has no permission logic of its own.
 */
import { apiClient } from "../api/client";

export async function listMedia({ entityType, entityId, page = 1, pageSize = 50 }) {
  const { data } = await apiClient.get("/media", {
    params: { entity_type: entityType, entity_id: entityId, page, page_size: pageSize },
  });
  return data; // PaginatedResponse<MediaFileResponse>
}

export async function uploadMedia({ entityType, entityId, file, caption }) {
  const formData = new FormData();
  formData.append("entity_type", entityType);
  formData.append("entity_id", entityId);
  formData.append("file", file);
  if (caption) {
    formData.append("caption", caption);
  }
  // No explicit Content-Type header here - Axios sets the correct multipart boundary itself
  // when the body is a FormData instance, and apiClient's request interceptor only adds
  // Authorization, never a Content-Type that would override it.
  const { data } = await apiClient.post("/media", formData);
  return data; // MediaFileResponse
}

/** GET /{id}/download requires the same Bearer token as every other request, so a plain <img
 * src="..."> can't load it directly - callers fetch the bytes as a blob and build their own
 * object URL (see components/MediaAttachments.jsx), revoking it when no longer needed. */
export async function downloadMediaBlob(mediaFileId) {
  const { data } = await apiClient.get(`/media/${mediaFileId}/download`, { responseType: "blob" });
  return data;
}

export async function deleteMedia(mediaFileId) {
  await apiClient.delete(`/media/${mediaFileId}`);
}
