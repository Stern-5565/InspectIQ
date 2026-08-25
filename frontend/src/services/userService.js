/** Wraps /api/users - see app/api/users.py. listUsers started as the Maintenance module's
 * "assign to" picker (view-only). createUser/updateUser are Admin Settings' own addition -
 * Administrator-only on the backend (enforced there; this file doesn't re-check roles). */
import { apiClient } from "../api/client";

export async function listUsers({ includeInactive } = {}) {
  const { data } = await apiClient.get("/users", { params: { include_inactive: includeInactive || undefined } });
  return data; // UserResponse[]
}

export async function createUser({ firstName, lastName, email, phone, password, roleName }) {
  const { data } = await apiClient.post("/users", {
    FirstName: firstName,
    LastName: lastName,
    Email: email,
    Phone: phone || undefined,
    Password: password,
    RoleName: roleName,
  });
  return data; // UserResponse
}

export async function updateUser(userId, payload) {
  const { data } = await apiClient.patch(`/users/${userId}`, payload);
  return data; // UserResponse
}
