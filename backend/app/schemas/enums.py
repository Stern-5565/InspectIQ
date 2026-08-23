"""
Python enums mirroring the CHECK constraint value lists in database/constraints/09_Constraints.sql
exactly. Validating these at the API layer (via Pydantic) means a bad value gets a clean 422
with a helpful message before it ever reaches SQL Server, rather than surfacing as a raw
"CHECK constraint violation" SQL error. Keep these in sync with the DB constraints by hand -
there's no shared source of truth between T-SQL and Python in this project (see
docs/DATABASE.md for why enums are CHECK constraints, not lookup tables).
"""
from enum import Enum


class PropertyType(str, Enum):
    HMO = "HMO"
    BLOCK_OF_FLATS = "BlockOfFlats"
    RESIDENTIAL_HOUSE = "ResidentialHouse"
    COMMERCIAL_BUILDING = "CommercialBuilding"
    MIXED_USE = "MixedUse"
    OFFICE = "Office"
    OTHER = "Other"


class PropertyStatus(str, Enum):
    ACTIVE = "Active"
    UNDER_REFURBISHMENT = "UnderRefurbishment"
    FOR_SALE = "ForSale"
    NOT_IN_USE = "NotInUse"
    OTHER = "Other"


class InspectionFrequency(str, Enum):
    WEEKLY = "Weekly"
    FORTNIGHTLY = "Fortnightly"
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    SEMI_ANNUALLY = "SemiAnnually"
    ANNUALLY = "Annually"
    CUSTOM = "Custom"


class OccupancyStatus(str, Enum):
    OCCUPIED = "Occupied"
    VACANT = "Vacant"
    UNDER_REFURBISHMENT = "UnderRefurbishment"
    UNAVAILABLE = "Unavailable"
    UNKNOWN = "Unknown"
