/**
 * Shared Axios instance for every API call in the app.
 *
 * Token storage, explained (see also contexts/AuthContext.jsx):
 * - The ACCESS token lives only in memory (the `accessToken` variable below), never in
 *   localStorage/sessionStorage - anything readable by JavaScript is readable by an XSS
 *   payload too. It's lost on a full page reload, which is intentional; see the refresh flow
 *   below.
 * - The REFRESH token is longer-lived and more sensitive. The ideal place for it is an
 *   httpOnly cookie the browser attaches automatically and JavaScript can never read at all -
 *   but the backend issues it as a plain JSON field (app/schemas/auth.py's TokenResponse), not
 *   a cookie, so there is nothing for the browser to attach automatically. Given that, this
 *   frontend stores the refresh token in sessionStorage (cleared when the tab closes, unlike
 *   localStorage) so a page reload doesn't force a full re-login. This is a deliberate,
 *   documented compromise (the same one validated on PropertyManager's frontend), not an
 *   oversight - upgrading to httpOnly-cookie delivery would need a backend change.
 */

import axios from "axios";

const REFRESH_TOKEN_STORAGE_KEY = "iq_refresh_token";

let accessToken = null;
let onAuthExpired = null;

export function setAccessToken(token) {
  accessToken = token;
}

export function getStoredRefreshToken() {
  return sessionStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
}

export function setStoredRefreshToken(token) {
  if (token) {
    sessionStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  } else {
    sessionStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  }
}

/** AuthContext registers a callback here so this module (which can't use React hooks) can
 * tell it "the session is gone, log the user out" after a refresh attempt fails. */
export function setOnAuthExpired(callback) {
  onAuthExpired = callback;
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// Refresh-and-retry flow: a 401 usually means the access token expired (they're short-lived -
// 30 minutes by default, see backend/app/core/config.py's JWT_ACCESS_TOKEN_EXPIRE_MINUTES).
// Rather than surfacing that to the user as a login prompt immediately, try ONE silent
// refresh using the stored refresh token and replay the original request. Only give up (and
// log the user out) if the refresh itself fails (refresh token missing, expired, or invalid).
let refreshPromise = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const isAuthEndpoint = originalRequest?.url?.startsWith("/auth/");

    if (error.response?.status !== 401 || isAuthEndpoint || originalRequest._retried) {
      return Promise.reject(error);
    }

    const refreshToken = getStoredRefreshToken();
    if (!refreshToken) {
      onAuthExpired?.();
      return Promise.reject(error);
    }

    originalRequest._retried = true;
    try {
      // Multiple requests can 401 at once (e.g. a page firing several calls in parallel) -
      // share one in-flight refresh instead of firing a refresh call per failed request.
      refreshPromise ??= apiClient
        .post("/auth/refresh", { refresh_token: refreshToken })
        .finally(() => {
          refreshPromise = null;
        });
      const { data } = await refreshPromise;
      setAccessToken(data.access_token);
      originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      setAccessToken(null);
      setStoredRefreshToken(null);
      onAuthExpired?.();
      return Promise.reject(refreshError);
    }
  },
);
