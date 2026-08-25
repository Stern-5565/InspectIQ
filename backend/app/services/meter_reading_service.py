"""AI/OCR Meter Reading (Phase 14, scope §11).

A hybrid authorization tier for update/confirm - genuinely synthesized from this module's own
shape, not copied wholesale from either Phase 11-12's Inspection-anchored pattern or Phase 13's
Admin/Manager-only one, because `MeterReading.InspectionResponseId` sits in between them:
nullable, like `RiskAssessment.InspectionId` (a meter can be read standalone, not necessarily
tied to one specific checklist question), but scope §11's own flow text is explicit that "the
inspector" is the one who confirms or corrects the AI-detected value - unlike Risk Assessments,
where nothing in scope suggests the same person who raised a risk should be the one closing it
out. `ensure_can_edit_reading` below reflects both facts at once: when a reading IS linked to an
InspectionResponse, it reuses `inspection_service.ensure_can_edit` (the assigned inspector or
Admin/Manager) exactly like Cleaning/VacantUnit; when it's standalone, there is no Inspection to
check, so it falls back to Administrator/Manager only, exactly like Risk Assessments' reasoning
for the same structural situation.

View (list/get): any company member, as always. Create: Administrator/Manager/Inspector (the
same `_conduct_inspections` tier Cleaning/VacantUnit use) - taking and uploading a meter photo
is squarely part of conducting an inspection per scope §11's own framing.

Create is a single combined action, not a create-then-separate-upload: scope §11's flow (photo
uploaded -> sent to OCR -> AI reading displayed -> inspector confirms) happens as one request
here. The photo is stored through the SAME polymorphic media system every other module uses
(`EntityType="MeterReading"`), not a bespoke upload path - `PhotoMediaFileId` is then just a
denormalized pointer to that one MediaFiles row, kept in sync here, not a parallel mechanism.
"""
from typing import BinaryIO

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.meter_reading import MeterReading
from app.models.user import User
from app.repositories import inspection_response_repository as response_repo
from app.repositories import meter_reading_repository as repo
from app.schemas.enums import MeterType
from app.schemas.meter_reading import MeterReadingUpdate
from app.security import roles
from app.services import inspection_service, property_service
from app.services.media_storage import IMediaStorageService
from app.services.meter_ocr import IMeterReadingOcrService, get_ocr_service

_MANAGE_ROLES = {roles.ADMINISTRATOR, roles.MANAGER}


def _resolve_inspection(db: Session, current_user: User, reading: MeterReading):
    if reading.InspectionResponseId is None:
        return None
    # Same repository function Phase 9 added for exactly this situation (a bare response_id
    # with no already-authorized Inspection in hand yet) - its third real caller now.
    response = response_repo.get_response_by_id_for_company(
        db, current_user.CompanyId, reading.InspectionResponseId
    )
    if response is None:
        return None
    return inspection_service.get_inspection(db, current_user, response.InspectionId)


def ensure_can_edit_reading(db: Session, current_user: User, reading: MeterReading) -> None:
    inspection = _resolve_inspection(db, current_user, reading)
    if inspection is not None:
        inspection_service.ensure_can_edit(current_user, inspection)
        return

    user_role_names = {role.RoleName for role in current_user.roles}
    if not user_role_names.intersection(_MANAGE_ROLES):
        raise ForbiddenError(
            "Only an Administrator or Manager can modify a meter reading not linked to an inspection."
        )


def create_meter_reading(
    db: Session,
    current_user: User,
    *,
    property_id: int,
    meter_type: str,
    inspection_response_id: int | None,
    meter_serial_number: str | None,
    inspector_notes: str | None,
    file: UploadFile,
    storage: IMediaStorageService | None = None,
    ocr: IMeterReadingOcrService | None = None,
) -> MeterReading:
    try:
        MeterType(meter_type)
    except ValueError:
        raise ValidationError(
            f"Unsupported MeterType '{meter_type}'. Supported: {', '.join(m.value for m in MeterType)}."
        )

    property_ = property_service.get_property(db, current_user, property_id)

    if inspection_response_id is not None:
        response = response_repo.get_response_by_id_for_company(
            db, current_user.CompanyId, inspection_response_id
        )
        if response is None:
            raise NotFoundError("Inspection response not found.")
        inspection = inspection_service.get_inspection(db, current_user, response.InspectionId)
        if inspection.PropertyId != property_.PropertyId:
            raise ValidationError("InspectionResponseId does not belong to the given property.")

    reading = MeterReading(
        PropertyId=property_.PropertyId,
        InspectionResponseId=inspection_response_id,
        MeterType=meter_type,
        MeterSerialNumber=meter_serial_number,
        InspectorNotes=inspector_notes,
    )
    reading = repo.create_meter_reading(db, reading)

    # Local import: media_service's own entity-type dispatch for EntityType="MeterReading"
    # calls BACK into this module (ensure_can_edit_reading, get_meter_reading) - a top-level
    # import either direction would be circular. See media_service.py's
    # _view_meter_reading/_mutate_meter_reading for the matching local import there. Same
    # pattern as maintenance_service.upload_photo (Phase 10).
    from app.services import media_service

    media_file = media_service.upload_media(
        db,
        current_user,
        entity_type="MeterReading",
        entity_id=reading.MeterReadingId,
        file=file,
        caption=None,
        storage=storage,
    )
    reading.PhotoMediaFileId = media_file.MediaFileId

    ocr = ocr or get_ocr_service()
    stream: BinaryIO = media_service.open_media_stream(media_file, storage=storage)
    try:
        result = ocr.detect_reading(stream)
    finally:
        stream.close()
    reading.AIDetectedReading = result.detected_reading
    reading.AIConfidence = result.confidence

    return repo.save_meter_reading(db, reading)


def list_meter_readings(
    db: Session,
    current_user: User,
    *,
    page: int,
    page_size: int,
    property_id: int | None = None,
    meter_type: str | None = None,
    inspection_response_id: int | None = None,
) -> tuple[list, int]:
    """Returns (MeterReading, PropertyName, InspectionId) rows - see
    repo.list_meter_readings's own docstring for why enriching this in place (rather than adding
    a parallel function, the way Cleaning/VacantUnits' company-wide queries had to) is safe here:
    this was the ONLY caller of the underlying query even before the standalone module existed."""
    return repo.list_meter_readings(
        db,
        current_user.CompanyId,
        page=page,
        page_size=page_size,
        property_id=property_id,
        meter_type=meter_type,
        inspection_response_id=inspection_response_id,
    )


def get_meter_reading(db: Session, current_user: User, meter_reading_id: int) -> MeterReading:
    reading = repo.get_meter_reading_by_id(db, current_user.CompanyId, meter_reading_id)
    if reading is None:
        raise NotFoundError("Meter reading not found.")
    return reading


def get_meter_reading_detail(db: Session, current_user: User, meter_reading_id: int):
    """The standalone module's own single-detail lookup, returning (MeterReading, PropertyName,
    InspectionId) - kept SEPARATE from get_meter_reading above, which several other callers
    (media_service's authorization dispatch, update_meter_reading's mutation) depend on
    returning a bare MeterReading, not a tuple."""
    row = repo.get_meter_reading_with_property_name(db, current_user.CompanyId, meter_reading_id)
    if row is None:
        raise NotFoundError("Meter reading not found.")
    return row


def update_meter_reading(
    db: Session, current_user: User, meter_reading_id: int, payload: MeterReadingUpdate
) -> MeterReading:
    reading = get_meter_reading(db, current_user, meter_reading_id)
    ensure_can_edit_reading(db, current_user, reading)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reading, field, value)
    return repo.save_meter_reading(db, reading)
