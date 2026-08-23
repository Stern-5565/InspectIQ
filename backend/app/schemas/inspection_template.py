from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InspectionQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    InspectionQuestionId: int
    QuestionText: str
    AnswerType: str
    SortOrder: int
    AllowNotes: bool
    AllowPhoto: bool
    RequirePhoto: bool
    AllowMaintenanceFlag: bool
    AllowRiskFlag: bool
    IsMandatory: bool
    IsActive: bool


class InspectionSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    InspectionSectionId: int
    SectionName: str
    SortOrder: int
    IsActive: bool
    Questions: list[InspectionQuestionResponse]

    @classmethod
    def from_section(cls, section) -> "InspectionSectionResponse":
        return cls(
            InspectionSectionId=section.InspectionSectionId,
            SectionName=section.SectionName,
            SortOrder=section.SortOrder,
            IsActive=section.IsActive,
            Questions=[InspectionQuestionResponse.model_validate(q) for q in section.questions],
        )


class InspectionTemplateResponse(BaseModel):
    """List view - lightweight, no nested sections/questions."""

    model_config = ConfigDict(from_attributes=True)

    InspectionTemplateId: int
    CompanyId: int | None
    TemplateName: str
    Description: str | None
    IsActive: bool
    Version: int
    CreatedAt: datetime
    CreatedBy: int | None


class InspectionTemplateDetailResponse(InspectionTemplateResponse):
    """Single-item view - full nested tree, everything a mobile client needs to render the
    checklist or start an inspection in one request (PROJECT_PLAN.md §7: "design APIs with a
    mobile frontend in mind")."""

    Sections: list[InspectionSectionResponse]

    @classmethod
    def from_template(cls, template) -> "InspectionTemplateDetailResponse":
        return cls(
            InspectionTemplateId=template.InspectionTemplateId,
            CompanyId=template.CompanyId,
            TemplateName=template.TemplateName,
            Description=template.Description,
            IsActive=template.IsActive,
            Version=template.Version,
            CreatedAt=template.CreatedAt,
            CreatedBy=template.CreatedBy,
            Sections=[InspectionSectionResponse.from_section(s) for s in template.sections],
        )
