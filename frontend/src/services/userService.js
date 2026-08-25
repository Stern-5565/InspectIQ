/** Wraps /api/users - see app/api/users.py. Added for the Maintenance module's "assign to"
 * picker; view-only, no create/update/delete (user management is Admin Settings' job, a still
 * unbuilt Phase 16 page). */
import { apiClient } from "../api/client";

export async function listUsers({ includeInactive } = {}) {
  const { data } = await apiClient.get("/users", { params: { include_inactive: includeInactive || undefined } });
  return data; // UserResponse[]
}
