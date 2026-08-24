/**
 * Thin wrapper around /api/auth/* - the pattern every future module's service file follows: a
 * service module owns "how do I call this part of the API," components and contexts never
 * call apiClient directly.
 *
 * Field names sent to login/refresh match app/schemas/auth.py exactly - lowercase `email`/
 * `password`/`refresh_token`, unlike every other resource's PascalCase request bodies
 * elsewhere in this API (app/schemas/*.py). Auth is the one deliberate exception, not a typo.
 */
import { apiClient } from "../api/client";

export async function login(email, password) {
  const { data } = await apiClient.post("/auth/login", { email, password });
  return data; // { access_token, refresh_token, token_type }
}

export async function refresh(refreshToken) {
  const { data } = await apiClient.post("/auth/refresh", { refresh_token: refreshToken });
  return data; // { access_token, token_type }
}

export async function getCurrentUser() {
  const { data } = await apiClient.get("/auth/me");
  return data; // { UserId, CompanyId, FirstName, LastName, Email, Phone, IsActive, CreatedAt, LastLoginAt, Roles }
}

// No logout() wrapper - the backend has no POST /api/auth/logout endpoint (app/api/auth.py
// only defines login/refresh/me). There's no server-side session to invalidate (JWTs are
// stateless), so "logging out" is purely a client-side action - see AuthContext.jsx's logout.
