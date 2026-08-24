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


# Named MaintenanceX rather than bare X (unlike PropertyType/PropertyStatus above) precisely so
# the schema field name (Category/Priority, matching the DB column) never collides with the
# enum's own class name - sidesteps the Phase 6 Python 3.14 lazy-annotation gotcha
# (schemas/property.py's header comment) at the naming level instead of needing an aliased
# import in every schema file that uses these.
class MaintenanceCategory(str, Enum):
    ELECTRICAL = "Electrical"
    PLUMBING = "Plumbing"
    HEATING = "Heating"
    FIRE_SAFETY = "FireSafety"
    EMERGENCY_LIGHTING = "EmergencyLighting"
    CLEANING = "Cleaning"
    GARDEN = "Garden"
    STRUCTURAL = "Structural"
    DOORS_WINDOWS = "DoorsWindows"
    PEST_CONTROL = "PestControl"
    DECORATION = "Decoration"
    APPLIANCE = "Appliance"
    SECURITY = "Security"
    OTHER = "Other"


class MaintenancePriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"
    EMERGENCY = "Emergency"


class MaintenanceIssueStatus(str, Enum):
    OPEN = "Open"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "InProgress"
    WAITING = "Waiting"
    COMPLETED = "Completed"
    CLOSED = "Closed"


class CleaningAreaType(str, Enum):
    ENTRANCE = "Entrance"
    HALLWAY = "Hallway"
    STAIRCASE = "Staircase"
    LANDING = "Landing"
    COMMUNAL_KITCHEN = "CommunalKitchen"
    COMMUNAL_BATHROOM = "CommunalBathroom"
    BIN_AREA = "BinArea"
    GARDEN = "Garden"
    LAUNDRY_AREA = "LaundryArea"
    LIFT = "Lift"
    OTHER = "Other"


class CleaningGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class CleaningInspectionStatus(str, Enum):
    PENDING = "Pending"
    ASSIGNED = "Assigned"
    COMPLETED = "Completed"


class RiskAssessmentStatus(str, Enum):
    OPEN = "Open"
    ACTION_PLANNED = "ActionPlanned"
    CLOSED = "Closed"


class MeterType(str, Enum):
    ELECTRICITY = "Electricity"
    GAS = "Gas"
    WATER = "Water"
