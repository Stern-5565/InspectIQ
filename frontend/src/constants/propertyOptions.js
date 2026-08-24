/**
 * Mirrors app/schemas/enums.py's PropertyType/PropertyStatus/InspectionFrequency exactly -
 * value strings must match the backend's enum values byte-for-byte (they're sent straight
 * through to Pydantic, which 422s on anything else).
 */
export const PROPERTY_TYPE_OPTIONS = [
  { value: "HMO", label: "HMO" },
  { value: "BlockOfFlats", label: "Block of Flats" },
  { value: "ResidentialHouse", label: "Residential House" },
  { value: "CommercialBuilding", label: "Commercial Building" },
  { value: "MixedUse", label: "Mixed Use" },
  { value: "Office", label: "Office" },
  { value: "Other", label: "Other" },
];

export const PROPERTY_STATUS_OPTIONS = [
  { value: "Active", label: "Active" },
  { value: "UnderRefurbishment", label: "Under Refurbishment" },
  { value: "ForSale", label: "For Sale" },
  { value: "NotInUse", label: "Not In Use" },
  { value: "Other", label: "Other" },
];

export const INSPECTION_FREQUENCY_OPTIONS = [
  { value: "Weekly", label: "Weekly" },
  { value: "Fortnightly", label: "Fortnightly" },
  { value: "Monthly", label: "Monthly" },
  { value: "Quarterly", label: "Quarterly" },
  { value: "SemiAnnually", label: "Semi-Annually" },
  { value: "Annually", label: "Annually" },
  { value: "Custom", label: "Custom" },
];
