"""
Importing every model here (not just under TYPE_CHECKING in the files that reference them via
string relationships) guarantees they're all registered with SQLAlchemy's declarative registry
together, regardless of which module happens to touch the ORM first.

Real bug this fixes: app/models/user.py's `company: Mapped["Company"] = relationship(...)`
only imports Company under `if TYPE_CHECKING`, so at runtime nothing registered the Company
class - a query against User raised `sqlalchemy.exc.InvalidRequestError: ... failed to locate
a name ('Company')` the first time a real request (not a test) exercised it. Every automated
test happened to pass anyway, because tests/test_auth.py imports `Company` directly for its own
fixture setup, which incidentally registered it before any query ran - masking the bug. Caught
only by starting a real uvicorn server and hitting /api/auth/login over actual HTTP. See
docs/AI_MEMORY.md's 2026-08-23 Phase 5 entry for the fuller story.
"""
from app.models.base import Base
from app.models.company import Company
from app.models.role import Role
from app.models.user import User, user_roles

__all__ = ["Base", "Company", "Role", "User", "user_roles"]
