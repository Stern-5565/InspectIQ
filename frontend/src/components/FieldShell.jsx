/**
 * Internal helper shared by FormField/SelectField/DateField - the label/error/aria-wiring
 * those field types have in common (id generation, associating the error message via
 * aria-describedby, marking the input aria-invalid). Mirrors PropertyManager's FieldShell.
 *
 * `children` is a render prop - `(fieldProps) => <input {...fieldProps} />` - rather than a
 * plain element, so a field type that needs to wrap its input in something else can still put
 * `fieldProps` on the actual input.
 */
import { useId } from "react";

export function FieldShell({ label, required, error, disabled, children }) {
  const id = useId();
  const errorId = `${id}-error`;

  const fieldProps = {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error ? errorId : undefined,
    required,
    disabled,
  };

  return (
    <label className="form-field" htmlFor={id}>
      <span>
        {label}
        {required && (
          <span aria-hidden="true" className="form-field__required">
            {" "}
            *
          </span>
        )}
      </span>
      {children(fieldProps)}
      {error && (
        <span id={errorId} className="form-field__error" role="alert">
          {error}
        </span>
      )}
    </label>
  );
}
