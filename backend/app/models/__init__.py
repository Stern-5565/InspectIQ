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
2026-08-23 Phase 5 entry for the full story. Every model added since - Property, Unit - is
listed below for exactly this reason.
"""
from app.models.base import Base
from app.models.company import Company
from app.models.property import Property
from app.models.role import Role
from app.models.unit import Unit
from app.models.user import User, user_roles

__all__ = ["Base", "Company", "Property", "Role", "Unit", "User", "user_roles"]
