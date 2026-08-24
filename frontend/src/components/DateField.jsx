/**
 * Labeled date input. Value is always an ISO "YYYY-MM-DD" string, matching both the native
 * <input type="date"> format and what the backend's Pydantic `date` fields serialize as.
 */
import { FieldShell } from "./FieldShell";

export function DateField({ label, name, value, onChange, required, error, min, max }) {
  return (
    <FieldShell label={label} required={required} error={error}>
      {(fieldProps) => (
        <input
          {...fieldProps}
          name={name}
          type="date"
          value={value}
          onChange={onChange}
          min={min}
          max={max}
          className="form-field__input"
        />
      )}
    </FieldShell>
  );
}
