/** Mirrors app/schemas/enums.py's MeterType exactly. */
export const METER_TYPE_OPTIONS = [
  { value: "Electricity", label: "Electricity" },
  { value: "Gas", label: "Gas" },
  { value: "Water", label: "Water" },
];

/** Best-effort default for the MeterType select, from the question's own section name (e.g. the
 * seeded template's "Electricity Meter" section) - a small "few taps" nicety, not a requirement;
 * falls back to no default when the section name doesn't name a meter type. */
export function guessMeterTypeFromSectionName(sectionName) {
  const match = METER_TYPE_OPTIONS.find((option) => sectionName?.toLowerCase().includes(option.value.toLowerCase()));
  return match?.value ?? "";
}
