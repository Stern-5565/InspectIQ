from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RiskMatrixLevel(Base):
    """Configurable risk-level bands (scope §19: "the exact risk matrix should remain
    configurable"). CompanyId NULLABLE - NULL rows are the global default matrix, the same
    nullable-CompanyId pattern InspectionTemplates uses, but with different lookup semantics:
    a company's own bands fully REPLACE the global default once any exist (not an additive
    "global + extra" list like Templates) - see app/services/risk_service.py's
    get_risk_matrix_for_company for why a partial mix of global and company bands would leave
    gaps/overlaps a template list never risks."""

    __tablename__ = "RiskMatrixLevels"

    RiskMatrixLevelId: Mapped[int] = mapped_column(Integer, primary_key=True)
    CompanyId: Mapped[int | None] = mapped_column(Integer, ForeignKey("Companies.CompanyId"))
    MinScore: Mapped[int] = mapped_column(Integer, nullable=False)
    MaxScore: Mapped[int] = mapped_column(Integer, nullable=False)
    LevelName: Mapped[str] = mapped_column(String(20), nullable=False)
    SortOrder: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ColorHint: Mapped[str | None] = mapped_column(String(20))
