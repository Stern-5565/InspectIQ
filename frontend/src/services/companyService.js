/** Wraps /api/company - see app/api/company.py. No path parameter (a user only ever sees/edits
 * their own company, resolved server-side from their token) - Admin Settings' Company Profile
 * section. */
import { apiClient } from "../api/client";

export async function getCompany() {
  const { data } = await apiClient.get("/company");
  return data; // CompanyResponse
}

export async function updateCompany(payload) {
  const { data } = await apiClient.patch("/company", payload);
  return data; // CompanyResponse
}
