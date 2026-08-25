import { FieldShell } from "./FieldShell";

export function FormField({ label, name, value, onChange, type = "text", required, error, placeholder, disabled }) {
  return (
    <FieldShell label={label} required={required} error={error} disabled={disabled}>
      {(fieldProps) => (
        <input
          {...fieldProps}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="form-field__input"
        />
      )}
    </FieldShell>
  );
}
