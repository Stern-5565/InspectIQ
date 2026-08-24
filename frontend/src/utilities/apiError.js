/**
 * Backend error responses come in two shapes, both under `detail`:
 *   - Domain errors raised via app/core/exceptions.py's AppError subclasses:
 *     { "detail": "Human-readable message." }
 *   - FastAPI's own request-validation errors (a malformed request body, before any route
 *     code runs) - not overridden by any handler in app/main.py, so FastAPI's default shape
 *     applies: { "detail": [{ "loc": [...], "msg": "...", "type": "..." }, ...] }
 * This pulls a single human-readable message out of either shape (or an Axios/network-level
 * failure) so components never need to know which case they're in.
 */
export function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => item.msg).join(" ");
  }
  if (error?.response) {
    return `Request failed (${error.response.status}).`;
  }
  if (error?.request) {
    return "Could not reach the server. Check your connection and try again.";
  }
  return error?.message || "Something went wrong.";
}
