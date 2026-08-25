/**
 * Wraps /api/inspection-templates - see app/api/inspection_templates.py. Read-only: no
 * create/edit/delete exists yet (scope treats template authoring as "eventually," not part of
 * this phase - that file's own module docstring). Not paginated - the backend returns a plain
 * list, not a PaginatedResponse, since the realistic number of templates per company is small.
 */
import { apiClient } from "../api/client";

export async function listTemplates({ includeInactive } = {}) {
  const { data } = await apiClient.get("/inspection-templates", {
    params: { include_inactive: includeInactive || undefined },
  });
  return data; // InspectionTemplateResponse[]
}

export async function getTemplate(templateId) {
  const { data } = await apiClient.get(`/inspection-templates/${templateId}`);
  return data; // InspectionTemplateDetailResponse - full nested Sections -> Questions tree
}
