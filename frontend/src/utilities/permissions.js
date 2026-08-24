/**
 * `user.Roles` (from AuthContext, ultimately GET /api/auth/me) is a plain array of role name
 * strings - this just checks whether any of them is in an allowed-roles list, so every future
 * module's "should this button/route be visible" check reads the same way instead of each page
 * reimplementing `.some(...)`.
 */
export function hasAnyRole(user, allowedRoles) {
  if (!user) {
    return false;
  }
  return user.Roles.some((role) => allowedRoles.includes(role));
}

/**
 * "/" (Dashboard) is the default post-login landing page. Unlike PropertyManager, no role is
 * currently excluded from it (GET /api/dashboard has no role gate at all - see
 * constants/roles.js), so this is trivial for now - but it stays a function, not a hardcoded
 * "/" literal at each call site, so the day a role-restricted module needs a different landing
 * page for one role, only this one place changes.
 */
export function getDefaultLandingPath() {
  return "/";
}
