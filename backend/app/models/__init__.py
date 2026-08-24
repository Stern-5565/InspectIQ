"""
Importing every model here (not just under TYPE_CHECKING in the files that reference them via
string relationships) guarantees they're all registered with SQLAlchemy's declarative registry
together, regardless of which module happens to touch the ORM first.

Real bug this fixes, and every future model must respect the same rule: app/models/user.py's
`company: Mapped["Company"] = relationship(...)` only imports Company under `if TYPE_CHECKING`,
so at runtime nothing registered the Company class - a query against User raised
`sqlalchemy.exc.InvalidRequestError: ... failed to locate a name ('Company')` the first time a
real request (not a test) exercised it, even though every pytest test passed (a test file's own
import had incidentally registered it first, masking the bug). See docs/AI_MEMORY.md's
2026-08-23 Phase 5 entry for the full story. Every model added since is listed below for
exactly this reason, and each one is sanity-queried against real data before any route is
written that depends on it (Phase 7 onward).
"""
from app.models.base import Base
from app.models.cleaning_area import CleaningArea
from app.models.cleaning_inspection import CleaningInspection
from app.models.company import Company
from app.models.inspection import Inspection
from app.models.inspection_question import InspectionQuestion
from app.models.inspection_response import InspectionResponse
from app.models.inspection_section import InspectionSection
from app.models.inspection_template import InspectionTemplate
from app.models.maintenance_issue import MaintenanceIssue
from app.models.maintenance_update import MaintenanceUpdate
from app.models.media_file import MediaFile
from app.models.property import Property
from app.models.role import Role
from app.models.unit import Unit
from app.models.user import User, user_roles

__all__ = [
    "Base",
    "CleaningArea",
    "CleaningInspection",
    "Company",
    "Inspection",
    "InspectionQuestion",
    "InspectionResponse",
    "InspectionSection",
    "InspectionTemplate",
    "MaintenanceIssue",
    "MaintenanceUpdate",
    "MediaFile",
    "Property",
    "Role",
    "Unit",
    "User",
    "user_roles",
]
