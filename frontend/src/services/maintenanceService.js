/**
 * Wraps /api/maintenance-issues - see app/api/maintenance.py. Only createMaintenanceIssue exists
 * so far, for Sub-phase C's quick-create modal - the full Maintenance module (list/detail/
 * assign/status/notes/photos) is one of Phase 16's remaining pages, not built yet.
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
