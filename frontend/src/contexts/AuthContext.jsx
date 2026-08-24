/**
 * Authentication state for the whole app.
 *
 * Session restore on page load: there's no access token to restore (it's memory-only, see
 * api/client.js's module docstring) - instead, if a refresh token was left in sessionStorage
 * from an earlier visit, we silently exchange it for a fresh access token and re-fetch the
 * current user, so a page reload doesn't force a re-login. If that refresh fails (or there's
 * no stored refresh token at all), the user just lands on the login page.
 */
import { createContext, useContext, useEffect, useMemo, useState, useCallback } from "react";
import {
  setAccessToken,
  getStoredRefreshToken,
  setStoredRefreshToken,
  setOnAuthExpired,
} from "../api/client";
import * as authService from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);

  const clearSession = useCallback(() => {
    setAccessToken(null);
    setStoredRefreshToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setOnAuthExpired(clearSession);
  }, [clearSession]);

  useEffect(() => {
    const storedRefreshToken = getStoredRefreshToken();
    if (!storedRefreshToken) {
      setInitializing(false);
      return;
    }

    authService
      .refresh(storedRefreshToken)
      .then(async ({ access_token }) => {
        setAccessToken(access_token);
        const currentUser = await authService.getCurrentUser();
        setUser(currentUser);
      })
      .catch(() => {
        clearSession();
      })
      .finally(() => {
        setInitializing(false);
      });
    // Runs once on mount only - this is a one-time "am I already logged in" check, not
    // something that should re-run on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(async (email, password) => {
    const { access_token, refresh_token } = await authService.login(email, password);
    setAccessToken(access_token);
    setStoredRefreshToken(refresh_token);
    const currentUser = await authService.getCurrentUser();
    setUser(currentUser);
    return currentUser;
  }, []);

  // Purely client-side - see authService.js's comment on why there's no backend call here.
  const logout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: user !== null,
      initializing,
      login,
      logout,
    }),
    [user, initializing, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
