/**
 * Mirrors app/services/inspection_service.py's own `_is_answered` exactly - a response counts
 * as answered if it's marked Not Applicable OR has non-empty AnswerText, so the frontend's
 * displayed completion always agrees with the backend's own CompletionPercentage rather than
 * computing it a different way.
 */
export function isAnswered(response) {
  return response.IsNotApplicable || Boolean(response.AnswerText && response.AnswerText.trim());
}

/**
 * "Failed" only applies to PassFail answers with AnswerText === "Fail" - the one answer type
 * with a real, service-enforced failure value (`_VALID_PASSFAIL` in inspection_service.py).
 * Condition's freeform values (even this app's own Good/Fair/Poor preset buttons) deliberately
 * do NOT drive this - that would invent a "Poor means failed" rule the backend doesn't define.
 */
export function isFailed(response) {
  return response.AnswerTypeSnapshot === "PassFail" && response.AnswerText === "Fail";
}
