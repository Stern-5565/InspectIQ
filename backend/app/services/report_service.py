"""Phase 17: PDF Inspection Reports (scope §22, PROJECT_PLAN.md §9).

One ReportService-shaped module of plain functions - matches this project's function-based
service convention (no class), the same shape every other service already uses. Reads a
SUBMITTED inspection only - "reports must represent the inspection exactly as it existed at
submission" is already an established rule in inspection_service.py (post-submission
immutability); a report of an in-progress inspection isn't "the report" scope §22 describes
("When an inspection is completed generate a professional report").

Two scope-named fields were never actually built anywhere in this app and are NOT invented
here, just rendered honestly: `Company.LogoPath` (no upload flow exists -
app/schemas/company.py's own module docstring explicitly deferred it) renders as a text-only
header, and `Inspection.InspectorSignaturePath` (no signature-capture UI exists anywhere in
this project) renders as "Not signed" rather than smuggling a signature-pad feature into a
"generate a report" task.

Deliberately excludes `Property.AlarmAccessCode` - a plaintext access code
(docs/DATABASE.md §10.4's own flagged risk) has no business being embedded in a
downloadable/printable/forwardable PDF, a materially worse exposure surface than the app UI
itself already accepts.

The Inspection Checklist section is rendered from InspectionResponse.SectionNameSnapshot in
existing (frozen, creation-order) order - NEVER a hardcoded section list. Scope §22's own report
section list ("Fire Safety", "Front Garden", ...) is just the seeded demo template's own section
names; this whole engine is checklist/template-driven by design since Phase 1, so a real
company's differently-shaped template must render correctly here too, not just the demo one.

Photos are embedded INLINE with whatever record they're attached to (a question, a maintenance
issue, a meter reading, ...) rather than collected into one separate "Photos" appendix - scope's
own "Electricity Meter Reading (incl. photo)" phrasing frames photos as part of their record's
context, not a disconnected dump at the end.
"""
from io import BytesIO
from xml.sax.saxutils import escape as _xml_escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.cleaning_area import CleaningArea
from app.models.cleaning_inspection import CleaningInspection
from app.models.maintenance_issue import MaintenanceIssue
from app.models.meter_reading import MeterReading
from app.models.risk_assessment import RiskAssessment
from app.models.unit import Unit
from app.models.user import User
from app.models.vacant_unit_inspection import VacantUnitInspection
from app.repositories import media_file_repository
from app.services import inspection_service
from app.services.media_storage import get_storage_service

_LABEL_WIDTH = 4.5 * cm
_VALUE_WIDTH = 13.5 * cm
_MAX_PHOTO_SIZE = 6 * cm

# Every unset-field placeholder below uses "N/A", not the "—" (em dash) the rest of the app's
# own frontend uses - confirmed for real that ReportLab's default base-14 fonts don't reliably
# round-trip that character (isolated with a two-line reproduction: `canvas.drawString` with a
# literal em dash, read back with pypdf, came back as U+FFFD). Plain ASCII sidesteps the whole
# question of whether it's a genuine rendering bug or just an extraction quirk in whatever PDF
# viewer/tool a reader opens this in.


def _para(text, style) -> Paragraph:
    """Every dynamic/user-supplied string going into a Paragraph must go through this - raw
    text can contain `<`/`&`/etc that ReportLab's mini-XML parser would otherwise choke on or
    misinterpret as markup. Plain strings inside a Table cell (used everywhere below via
    `_kv_table`) are NOT parsed as markup by ReportLab, so only Paragraph calls need this."""
    escaped = _xml_escape(str(text)).replace("\n", "<br/>")
    return Paragraph(escaped, style)


def _kv_table(rows: list[list[str]]) -> Table:
    table = Table(rows, colWidths=[_LABEL_WIDTH, _VALUE_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportCompanyName", parent=styles["Title"], fontSize=18, spaceAfter=2))
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            spaceBefore=14,
            spaceAfter=6,
            textColor=colors.HexColor("#1d4ed8"),
        )
    )
    styles.add(ParagraphStyle(name="RecordHeading", parent=styles["Heading3"], spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name="QuestionText", parent=styles["Normal"], spaceBefore=6, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="AnswerText", parent=styles["Normal"], leftIndent=10))
    styles.add(
        ParagraphStyle(name="NotesText", parent=styles["Normal"], leftIndent=10, textColor=colors.grey, fontSize=9)
    )
    return styles


# --- gathering ---------------------------------------------------------------------------------


def _list_maintenance_issues(db: Session, inspection_id: int) -> list[MaintenanceIssue]:
    stmt = (
        select(MaintenanceIssue)
        .where(MaintenanceIssue.InspectionId == inspection_id)
        .order_by(MaintenanceIssue.MaintenanceIssueId)
    )
    return list(db.execute(stmt).scalars().all())


def _list_risk_assessments(db: Session, inspection_id: int) -> list[RiskAssessment]:
    stmt = (
        select(RiskAssessment)
        .where(RiskAssessment.InspectionId == inspection_id)
        .order_by(RiskAssessment.RiskAssessmentId)
    )
    return list(db.execute(stmt).scalars().all())


def _list_cleaning_inspections(db: Session, inspection_id: int) -> list[CleaningInspection]:
    stmt = (
        select(CleaningInspection)
        .where(CleaningInspection.InspectionId == inspection_id)
        .order_by(CleaningInspection.CleaningInspectionId)
    )
    return list(db.execute(stmt).scalars().all())


def _list_vacant_unit_inspections(db: Session, inspection_id: int) -> list[VacantUnitInspection]:
    stmt = (
        select(VacantUnitInspection)
        .where(VacantUnitInspection.InspectionId == inspection_id)
        .order_by(VacantUnitInspection.VacantUnitInspectionId)
    )
    return list(db.execute(stmt).scalars().all())


def _list_meter_readings(db: Session, response_ids: list[int]) -> list[MeterReading]:
    # MeterReading has no direct InspectionId column, only a nullable InspectionResponseId -
    # same join every Meter Readings module query already uses.
    if not response_ids:
        return []
    stmt = (
        select(MeterReading).where(MeterReading.InspectionResponseId.in_(response_ids)).order_by(MeterReading.MeterReadingId)
    )
    return list(db.execute(stmt).scalars().all())


def _group_responses_by_section(responses) -> dict:
    # Plain dict preserves first-insertion order (Python 3.7+) - responses arrive already
    # ordered by InspectionResponseId (creation order = frozen template SortOrder at start
    # time, per Inspection.responses' own relationship ordering), so grouping like this
    # reproduces the template's real section order without a second sort.
    sections: dict[str, list] = {}
    for response in responses:
        sections.setdefault(response.SectionNameSnapshot, []).append(response)
    return sections


def _is_answered(response) -> bool:
    # Mirrors inspection_service._is_answered / frontend isAnswered() exactly - the same
    # canonical definition duplicated on purpose (the frontend's own isAnswered() docstring
    # already establishes duplicating this one-line rule, with a comment naming the source of
    # truth, as this project's standing convention for keeping three layers in agreement).
    return response.IsNotApplicable or bool(response.AnswerText and response.AnswerText.strip())


def _is_failed(response) -> bool:
    # Mirrors frontend isFailed() exactly - "Failed" only ever applies to a PassFail question
    # answered "Fail" (the one answer type with a real, service-enforced failure value).
    return response.AnswerTypeSnapshot == "PassFail" and response.AnswerText == "Fail"


def _compute_summary(responses, maintenance_issues, risk_assessments) -> dict:
    return {
        "total": len(responses),
        "answered": sum(1 for r in responses if _is_answered(r)),
        "not_applicable": sum(1 for r in responses if r.IsNotApplicable),
        "failed": sum(1 for r in responses if _is_failed(r)),
        "maintenance_issues": len(maintenance_issues),
        "risk_assessments": len(risk_assessments),
    }


# --- photos --------------------------------------------------------------------------------


def _build_photos(db: Session, company_id: int, entity_type: str, entity_id: int, styles) -> list:
    media_files, _total = media_file_repository.list_media_files_for_entity(
        db, company_id, entity_type, entity_id, page=1, page_size=100
    )
    if not media_files:
        return []

    storage = get_storage_service()
    story: list = []
    for media_file in media_files:
        if not media_file.ContentType.startswith("image/"):
            story.append(_para(f"Attachment: {media_file.OriginalFileName}", styles["NotesText"]))
            continue
        try:
            stream = storage.open_stream(media_file.StorageKey)
            try:
                data = stream.read()
            finally:
                stream.close()
            pil_image = PILImage.open(BytesIO(data))
            # Force the FULL decode now, inside this try/except - PIL.Image.open() only reads
            # the header lazily, so without this, a corrupt image would only fail later, deep
            # inside doc.build() (ReportLab re-decodes the image from scratch at render time,
            # not at RLImage() construction), a code path with no exception handling at all -
            # confirmed for real: a genuinely truncated PNG crashed the ENTIRE report (all other
            # valid sections included) with an unhandled 500 until this .load() call was added.
            pil_image.load()
            orig_w, orig_h = pil_image.size
            scale = min(_MAX_PHOTO_SIZE / orig_w, _MAX_PHOTO_SIZE / orig_h, 1.0)
            story.append(RLImage(BytesIO(data), width=orig_w * scale, height=orig_h * scale))
            if media_file.Caption:
                story.append(_para(media_file.Caption, styles["NotesText"]))
        except (FileNotFoundError, OSError):
            # A missing file on disk or an unreadable/corrupt image shouldn't fail the whole
            # report - skip that one photo and keep going, the same "don't let one bad record
            # take down the whole operation" instinct as every other resilient loop in this
            # codebase.
            story.append(_para(f"Photo unavailable: {media_file.OriginalFileName}", styles["NotesText"]))
        story.append(Spacer(1, 0.1 * cm))
    return story


# --- section builders --------------------------------------------------------------------------


def _build_header(company, property_, inspection, inspector, styles) -> list:
    story = [_para(company.CompanyName, styles["ReportCompanyName"])]
    story.append(Paragraph("Property Inspection Report", styles["Heading3"]))
    story.append(Spacer(1, 0.3 * cm))
    rows = [
        ["Property", property_.PropertyName],
        ["Inspection date", inspection.InspectionDate.isoformat()],
        ["Inspector", f"{inspector.FirstName} {inspector.LastName}"],
        [
            "Next inspection due",
            inspection.NextInspectionDueDate.isoformat() if inspection.NextInspectionDueDate else "Not scheduled",
        ],
    ]
    story.append(_kv_table(rows))
    story.append(Spacer(1, 0.4 * cm))
    return story


def _build_property_summary(property_, styles) -> list:
    story = [Paragraph("Property Summary", styles["SectionHeading"])]
    address = ", ".join(filter(None, [property_.AddressLine1, property_.AddressLine2, property_.City, property_.Postcode]))
    rows = [
        ["Address", address],
        ["Property type", property_.PropertyType],
        ["Number of units", str(property_.NumberOfUnits) if property_.NumberOfUnits is not None else "N/A"],
        ["Main contact", property_.MainContactName or "N/A"],
        ["Access instructions", property_.AccessInstructions or "N/A"],
        ["Key location", property_.KeyLocation or "N/A"],
    ]
    story.append(_kv_table(rows))
    return story


def _build_overall_summary(inspection, summary: dict, styles) -> list:
    story = [Paragraph("Overall Summary", styles["SectionHeading"])]
    rows = [
        ["Overall condition", inspection.OverallCondition or "Not set"],
        ["Overall risk rating", inspection.OverallRiskRating or "Not set"],
        ["Questions answered", f"{summary['answered']} of {summary['total']}"],
        ["Not applicable", str(summary["not_applicable"])],
        ["Failed", str(summary["failed"])],
        ["Maintenance issues raised", str(summary["maintenance_issues"])],
        ["Risk assessments raised", str(summary["risk_assessments"])],
    ]
    story.append(_kv_table(rows))
    if inspection.GeneralNotes:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("General notes:", styles["Normal"]))
        story.append(_para(inspection.GeneralNotes, styles["NotesText"]))
    return story


def _build_checklist(db: Session, company_id: int, sections: dict, styles) -> list:
    story = [Paragraph("Inspection Checklist", styles["SectionHeading"])]
    for section_name, responses in sections.items():
        story.append(_para(section_name, styles["RecordHeading"]))
        for response in responses:
            story.append(_para(response.QuestionTextSnapshot, styles["QuestionText"]))
            if response.IsNotApplicable:
                answer_display = "Not Applicable"
            elif response.AnswerText:
                answer_display = response.AnswerText + ("  (FAILED)" if _is_failed(response) else "")
            else:
                answer_display = "Not answered"
            story.append(_para(f"Answer: {answer_display}", styles["AnswerText"]))
            if response.Notes:
                story.append(_para(f"Notes: {response.Notes}", styles["NotesText"]))
            story += _build_photos(db, company_id, "InspectionResponse", response.InspectionResponseId, styles)
            story.append(Spacer(1, 0.15 * cm))
    return story


def _build_meter_readings_section(db: Session, company_id: int, readings: list[MeterReading], styles) -> list:
    if not readings:
        return []
    story = [Paragraph("Meter Readings", styles["SectionHeading"])]
    for reading in readings:
        story.append(_para(f"{reading.MeterType} meter", styles["RecordHeading"]))
        rows = [
            ["AI-detected reading", str(reading.AIDetectedReading) if reading.AIDetectedReading is not None else "N/A"],
            ["Confirmed reading", str(reading.ConfirmedReading) if reading.ConfirmedReading is not None else "Not yet confirmed"],
            ["Serial number", reading.MeterSerialNumber or "N/A"],
        ]
        story.append(_kv_table(rows))
        if reading.InspectorNotes:
            story.append(_para(f"Notes: {reading.InspectorNotes}", styles["NotesText"]))
        story += _build_photos(db, company_id, "MeterReading", reading.MeterReadingId, styles)
        story.append(Spacer(1, 0.2 * cm))
    return story


_VACANT_UNIT_CHECK_FIELDS = [
    ("Electricity on", "ElectricityOn"),
    ("Water on", "WaterOn"),
    ("Heating working", "HeatingWorking"),
    ("Windows secure", "WindowsSecure"),
    ("Doors secure", "DoorsSecure"),
    ("Signs of leaks", "SignsOfLeaks"),
    ("Signs of damp", "SignsOfDamp"),
    ("Signs of pests", "SignsOfPests"),
    ("Cleaning required", "CleaningRequired"),
    ("Waste/items left behind", "WasteItemsLeftBehind"),
    ("Maintenance required", "MaintenanceRequired"),
]


def _tri_state_label(value: bool | None) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Not checked"


def _build_vacant_units_section(db: Session, company_id: int, records: list[VacantUnitInspection], styles) -> list:
    if not records:
        return []
    story = [Paragraph("Vacant Unit Inspections", styles["SectionHeading"])]
    for record in records:
        unit = db.get(Unit, record.UnitId)
        story.append(_para(unit.UnitNumber if unit else f"Unit #{record.UnitId}", styles["RecordHeading"]))
        rows = [
            ["Date identified vacant", record.DateIdentifiedVacant.isoformat()],
            ["Condition", record.Condition or "N/A"],
        ]
        rows += [[label, _tri_state_label(getattr(record, field))] for label, field in _VACANT_UNIT_CHECK_FIELDS]
        story.append(_kv_table(rows))
        if record.Notes:
            story.append(_para(f"Notes: {record.Notes}", styles["NotesText"]))
        story += _build_photos(db, company_id, "VacantUnitInspection", record.VacantUnitInspectionId, styles)
        story.append(Spacer(1, 0.2 * cm))
    return story


def _build_cleaning_section(db: Session, company_id: int, records: list[CleaningInspection], styles) -> list:
    if not records:
        return []
    story = [Paragraph("Communal Cleaning", styles["SectionHeading"])]
    for record in records:
        area = db.get(CleaningArea, record.CleaningAreaId)
        story.append(_para(area.AreaName if area else f"Area #{record.CleaningAreaId}", styles["RecordHeading"]))
        rows = [
            ["Grade", record.Grade],
            ["Status", record.Status],
            ["Cleaning required", "Yes" if record.CleaningRequired else "No"],
            ["Urgent", "Yes" if record.Urgent else "No"],
        ]
        story.append(_kv_table(rows))
        if record.Notes:
            story.append(_para(f"Notes: {record.Notes}", styles["NotesText"]))
        story += _build_photos(db, company_id, "CleaningInspection", record.CleaningInspectionId, styles)
        story.append(Spacer(1, 0.2 * cm))
    return story


def _build_maintenance_section(db: Session, company_id: int, records: list[MaintenanceIssue], styles) -> list:
    if not records:
        return []
    story = [Paragraph("Maintenance Issues", styles["SectionHeading"])]
    for record in records:
        story.append(_para(record.Title, styles["RecordHeading"]))
        rows = [
            ["Category", record.Category],
            ["Priority", record.Priority],
            ["Status", record.Status],
            ["Location", record.Location or "N/A"],
        ]
        story.append(_kv_table(rows))
        if record.Description:
            story.append(_para(f"Description: {record.Description}", styles["NotesText"]))
        story += _build_photos(db, company_id, "MaintenanceIssue", record.MaintenanceIssueId, styles)
        story.append(Spacer(1, 0.2 * cm))
    return story


def _build_risk_section(db: Session, company_id: int, records: list[RiskAssessment], styles) -> list:
    if not records:
        return []
    story = [Paragraph("Risk Assessments", styles["SectionHeading"])]
    for record in records:
        story.append(_para(record.Hazard, styles["RecordHeading"]))
        rows = [
            ["Location", record.Location or "N/A"],
            ["Likelihood x Severity", f"{record.Likelihood} x {record.Severity} = {record.RiskScore}"],
            ["Risk level", record.RiskLevel],
            ["Status", record.Status],
        ]
        story.append(_kv_table(rows))
        if record.ExistingControls:
            story.append(_para(f"Existing controls: {record.ExistingControls}", styles["NotesText"]))
        if record.AdditionalActionRequired:
            story.append(_para(f"Additional action required: {record.AdditionalActionRequired}", styles["NotesText"]))
        if record.Notes:
            story.append(_para(f"Notes: {record.Notes}", styles["NotesText"]))
        story += _build_photos(db, company_id, "RiskAssessment", record.RiskAssessmentId, styles)
        story.append(Spacer(1, 0.2 * cm))
    return story


def _build_footer(inspection, styles) -> list:
    story = [Spacer(1, 0.3 * cm), Paragraph("Sign-off", styles["SectionHeading"])]
    rows = [
        # No signature-capture flow exists anywhere in this app yet (see module docstring) -
        # rendering "Not signed" honestly rather than inventing a value.
        ["Inspector signature", "Not signed"],
        ["Date submitted", inspection.SubmittedAt.strftime("%Y-%m-%d %H:%M") if inspection.SubmittedAt else "N/A"],
    ]
    story.append(_kv_table(rows))
    return story


# --- entry point ---------------------------------------------------------------------------


def generate_inspection_report_pdf(db: Session, current_user: User, inspection_id: int) -> bytes:
    inspection = inspection_service.get_inspection(db, current_user, inspection_id)
    if inspection.Status != "Submitted":
        raise ConflictError("A report can only be generated for a submitted inspection.")

    property_ = inspection.property
    company = property_.company
    inspector = inspection.inspector
    company_id = current_user.CompanyId

    responses = inspection.responses
    response_ids = [r.InspectionResponseId for r in responses]
    sections = _group_responses_by_section(responses)

    maintenance_issues = _list_maintenance_issues(db, inspection_id)
    risk_assessments = _list_risk_assessments(db, inspection_id)
    cleaning_inspections = _list_cleaning_inspections(db, inspection_id)
    vacant_unit_inspections = _list_vacant_unit_inspections(db, inspection_id)
    meter_readings = _list_meter_readings(db, response_ids)

    summary = _compute_summary(responses, maintenance_issues, risk_assessments)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        title=f"Inspection Report - {property_.PropertyName}",
    )
    styles = _build_styles()

    story: list = []
    story += _build_header(company, property_, inspection, inspector, styles)
    story += _build_property_summary(property_, styles)
    story += _build_overall_summary(inspection, summary, styles)
    story += _build_checklist(db, company_id, sections, styles)
    story += _build_meter_readings_section(db, company_id, meter_readings, styles)
    story += _build_vacant_units_section(db, company_id, vacant_unit_inspections, styles)
    story += _build_cleaning_section(db, company_id, cleaning_inspections, styles)
    story += _build_maintenance_section(db, company_id, maintenance_issues, styles)
    story += _build_risk_section(db, company_id, risk_assessments, styles)
    story += _build_footer(inspection, styles)

    doc.build(story)
    return buffer.getvalue()
