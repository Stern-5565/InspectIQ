/**
 * Inline error display for a failed request - pass it whatever utilities/apiError.js's
 * getErrorMessage(err) returns. Takes a plain string, not the raw error object, so this
 * component never needs to know anything about Axios/the backend's error shape.
 */
export function ErrorMessage({ message, onRetry }) {
  return (
    <div className="error-message" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="button button--secondary" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
