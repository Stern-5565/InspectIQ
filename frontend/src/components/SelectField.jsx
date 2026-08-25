/**
 * Labeled <select> - for every fixed-choice field across every module (PropertyType,
 * OccupancyStatus, ...). `options` is always [{ value, label }] regardless of what the
 * underlying values are, so this stays one component instead of one per enum.
 */
import { FieldShell } from "./FieldShell";

export function SelectField({ label, name, value, onChange, options, required, error, placeholder, disabled }) {
  return (
    <FieldShell label={label} required={required} error={error} disabled={disabled}>
      {(fieldProps) => (
        <select {...fieldProps} name={name} value={value} onChange={onChange} className="form-field__input">
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}
    </FieldShell>
  );
}
