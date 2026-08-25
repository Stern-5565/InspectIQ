/** Mirrors docs/SCOPE.md §19's exact Likelihood/Severity scale ("Risk Calculation") - not an
 * invented labeling, the scope document's own wording. */
export const LIKELIHOOD_OPTIONS = [
  { value: "1", label: "1 - Rare" },
  { value: "2", label: "2 - Unlikely" },
  { value: "3", label: "3 - Possible" },
  { value: "4", label: "4 - Likely" },
  { value: "5", label: "5 - Very Likely" },
];

export const SEVERITY_OPTIONS = [
  { value: "1", label: "1 - Insignificant" },
  { value: "2", label: "2 - Minor" },
  { value: "3", label: "3 - Moderate" },
  { value: "4", label: "4 - Major" },
  { value: "5", label: "5 - Severe" },
];
