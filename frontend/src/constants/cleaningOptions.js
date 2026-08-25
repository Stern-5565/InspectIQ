/** Mirrors app/schemas/enums.py's CleaningGrade, using scope §16's own descriptive wording for
 * each letter grade rather than a bare A/B/C/D/E the inspector would have to memorize. */
export const CLEANING_GRADE_OPTIONS = [
  { value: "A", label: "A - Excellent (clean and well maintained)" },
  { value: "B", label: "B - Good (minor cleaning required)" },
  { value: "C", label: "C - Needs Attention (noticeable cleaning required)" },
  { value: "D", label: "D - Poor (significant cleaning required)" },
  { value: "E", label: "E - Critical (unacceptable, urgent action required)" },
];

/** Mirrors app/schemas/enums.py's CleaningInspectionStatus exactly. */
export const CLEANING_INSPECTION_STATUS_OPTIONS = [
  { value: "Pending", label: "Pending" },
  { value: "Assigned", label: "Assigned" },
  { value: "Completed", label: "Completed" },
];

/** Mirrors app/schemas/enums.py's CleaningAreaType exactly - scope §16's own "Areas could
 * include" list. */
export const CLEANING_AREA_TYPE_OPTIONS = [
  { value: "Entrance", label: "Entrance" },
  { value: "Hallway", label: "Hallway" },
  { value: "Staircase", label: "Staircase" },
  { value: "Landing", label: "Landing" },
  { value: "CommunalKitchen", label: "Communal Kitchen" },
  { value: "CommunalBathroom", label: "Communal Bathroom" },
  { value: "BinArea", label: "Bin Area" },
  { value: "Garden", label: "Garden" },
  { value: "LaundryArea", label: "Laundry Area" },
  { value: "Lift", label: "Lift" },
  { value: "Other", label: "Other" },
];
