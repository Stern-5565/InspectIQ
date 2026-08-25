/**
 * Wraps /api/maintenance-issues - see app/api/maintenance.py. createMaintenanceIssue was Sub-
 * phase C's quick-create modal; everything else here is the standalone Maintenance module
 * (list/detail/assign/status/notes/photos) built afterward, once real records existed with
 * nowhere to be managed.
 */
import { apiClient } from "../api/client";

export async function createMaintenanceIssue({ inspectionResponseId, title, category, priority, description }) {
  const { data } = await apiClient.post("/maintenance-issues", {
    InspectionResponseId: inspectionResponseId,
    Title: title,
    Category: category,
    Priority: priority || undefined,
    Description: description || undefined,
  });
  return data; // MaintenanceIssueDetailResponse
}

export async function listMaintenanceIssues({
  page = 1,
  pageSize = 20,
  status,
  category,
  priority,
  propertyId,
  assignedUserId,
} = {}) {
  const { data } = await apiClient.get("/maintenance-issues", {
    params: {
      page,
      page_size: pageSize,
      status: status || undefined,
      category: category || undefined,
      priority: priority || undefined,
      property_id: propertyId || undefined,
      assigned_user_id: assignedUserId || undefined,
    },
  });
  return data; // PaginatedResponse<MaintenanceIssueSummaryResponse>
}

export async function getMaintenanceIssue(issueId) {
  const { data } = await apiClient.get(`/maintenance-issues/${issueId}`);
  return data; // MaintenanceIssueDetailResponse (Updates already embedded)
}

/** General field edits (Title/Description/Location/Category/Priority/DueDate/Notes) -
 * Administrator/Manager only. Deliberately excludes Status/AssignedUserId, which have their own
 * dedicated endpoints below - matches the backend's own MaintenanceIssueUpdate schema exactly. */
export async function updateMaintenanceIssue(issueId, payload) {
  const { data } = await apiClient.patch(`/maintenance-issues/${issueId}`, payload);
  return data; // MaintenanceIssueDetailResponse
}

export async function assignMaintenanceIssue(issueId, assignedUserId) {
  const { data } = await apiClient.patch(`/maintenance-issues/${issueId}/assign`, { AssignedUserId: assignedUserId });
  return data; // MaintenanceIssueDetailResponse
}

export async function updateMaintenanceStatus(issueId, newStatus, comment) {
  const { data } = await apiClient.patch(`/maintenance-issues/${issueId}/status`, {
    NewStatus: newStatus,
    Comment: comment || undefined,
  });
  return data; // MaintenanceIssueDetailResponse
}

export async function addMaintenanceNote(issueId, comment) {
  const { data } = await apiClient.post(`/maintenance-issues/${issueId}/notes`, { Comment: comment });
  return data; // MaintenanceUpdateResponse
}

/** The timeline-aware upload path (writes a PhotoUploaded MaintenanceUpdate entry) - NOT the
 * generic /api/media upload mediaService.uploadMedia uses, which would attach the photo
 * correctly but leave no timeline trace. See MediaAttachments.jsx's `onUpload` override. */
export async function uploadMaintenancePhoto(issueId, file, caption) {
  const formData = new FormData();
  formData.append("file", file);
  if (caption) {
    formData.append("caption", caption);
  }
  const { data } = await apiClient.post(`/maintenance-issues/${issueId}/photos`, formData);
  return data; // MediaFileResponse
}
