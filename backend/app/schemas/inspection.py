from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InspectionCreate(BaseModel):
    PropertyId: int
    InspectionTemplateId: int
    InspectionType: str | None = Field(default=None, max_length=50)
    InspectionDate: date | None = None  # defaults to today if not supplied

    # Deliberately no InspectorUserId field - starting an inspection always self-assigns to
    # the authenticated user (app/services/inspection_service.py). No "assign to someone else"
    # flow exists yet (that's scope §24's inspection-scheduling territory, not this phase).


class InspectionResponseUpdate(BaseModel):
    """PATCH semantics - only supplied fields are changed. Covers answer/notes/mark-NA in one
    endpoint, matching scope Prompt 8's "answer questions / add notes / mark not applicable" as
    one unified inspector action, not three separate API calls."""

    AnswerText: str | None = None
    AnswerNumber: Decimal | None = None
    AnswerDate: date | None = None
    IsNotApplicable: bool | None = None
    Notes: str | None = None


class InspectionResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    InspectionResponseId: int
    InspectionQuestionId: int
    QuestionTextSnapshot: str
    SectionNameSnapshot: str
    AnswerTypeSnapshot: str
    AnswerText: str | None
    AnswerNumber: Decimal | None
    AnswerDate: date | None
    IsNotApplicable: bool
    Notes: str | None
    CreatedAt: datetime
    UpdatedAt: datetime | None


class InspectionSectionGroup(BaseModel):
    SectionName: str
    Responses: list[InspectionResponseSchema]


class InspectionSummaryResponse(BaseModel):
    """List view - lightweight, no responses. Matches the established pattern (Properties,
    InspectionTemplates): list is cheap, detail is where the full structure lives."""

    model_config = ConfigDict(from_attributes=True)

    InspectionId: int
    PropertyId: int
    InspectorUserId: int
    InspectionTemplateId: int
    InspectionType: str | None
    InspectionDate: date
    Status: str
    StartedAt: datetime | None
    SubmittedAt: datetime | None


class InspectionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    InspectionId: int
    PropertyId: int
    InspectorUserId: int
    InspectionTemplateId: int
    TemplateVersionUsed: int
    InspectionType: str | None
    InspectionDate: date
    StartedAt: datetime | None
    CompletedAt: datetime | None
    NextInspectionDueDate: date | None
    Status: str
    GeneralNotes: str | None
    OverallCondition: str | None
    OverallRiskRating: str | None
    SubmittedAt: datetime | None
    CreatedAt: datetime
    CompletionPercentage: float
    Sections: list[InspectionSectionGroup]

    @classmethod
    def from_inspection(cls, inspection, completion_percentage: float) -> "InspectionDetailResponse":
        sections: list[InspectionSectionGroup] = []
        for response in inspection.responses:
            # Responses are already in template order (InspectionResponseId, see the model's
            # own relationship comment) - consecutive equal SectionNameSnapshot values form a
            # contiguous run, so grouping is a simple linear scan, no GROUP BY needed.
            if not sections or sections[-1].SectionName != response.SectionNameSnapshot:
                sections.append(InspectionSectionGroup(SectionName=response.SectionNameSnapshot, Responses=[]))
            sections[-1].Responses.append(InspectionResponseSchema.model_validate(response))

        return cls(
            InspectionId=inspection.InspectionId,
            PropertyId=inspection.PropertyId,
            InspectorUserId=inspection.InspectorUserId,
            InspectionTemplateId=inspection.InspectionTemplateId,
            TemplateVersionUsed=inspection.TemplateVersionUsed,
            InspectionType=inspection.InspectionType,
            InspectionDate=inspection.InspectionDate,
            StartedAt=inspection.StartedAt,
            CompletedAt=inspection.CompletedAt,
            NextInspectionDueDate=inspection.NextInspectionDueDate,
            Status=inspection.Status,
            GeneralNotes=inspection.GeneralNotes,
            OverallCondition=inspection.OverallCondition,
            OverallRiskRating=inspection.OverallRiskRating,
            SubmittedAt=inspection.SubmittedAt,
            CreatedAt=inspection.CreatedAt,
            CompletionPercentage=completion_percentage,
            Sections=sections,
        )
