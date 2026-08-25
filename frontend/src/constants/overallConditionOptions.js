/** Mirrors app/schemas/enums.py's OverallCondition exactly - the real DB CK_Inspections_
 * OverallCondition CHECK constraint that existed since Phase 2, unused by the frontend until
 * PATCH /api/inspections/{id} (added during Sub-phase A planning) and now this Review screen. */
export const OVERALL_CONDITION_OPTIONS = [
  { value: "Excellent", label: "Excellent" },
  { value: "Good", label: "Good" },
  { value: "Satisfactory", label: "Satisfactory" },
  { value: "NeedsAttention", label: "Needs Attention" },
  { value: "Poor", label: "Poor" },
  { value: "Critical", label: "Critical" },
];
