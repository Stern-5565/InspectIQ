/** Mirrors app/schemas/enums.py's CleaningGrade, using scope §16's own descriptive wording for
 * each letter grade rather than a bare A/B/C/D/E the inspector would have to memorize. */
export const CLEANING_GRADE_OPTIONS = [
  { value: "A", label: "A - Excellent (clean and well maintained)" },
  { value: "B", label: "B - Good (minor cleaning required)" },
  { value: "C", label: "C - Needs Attention (noticeable cleaning required)" },
  { value: "D", label: "D - Poor (significant cleaning required)" },
  { value: "E", label: "E - Critical (unacceptable, urgent action required)" },
];
