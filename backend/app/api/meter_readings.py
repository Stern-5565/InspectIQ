"""
Create is a single multipart request (property/meter details + the photo together), not a JSON
body - it triggers the whole scope §11 flow (store the reading, upload the photo through the
same polymorphic media system every other module uses, run it through the mock OCR provider,
return the AI-detected value) in one call, matching the maintenance/cleaning photo-upload routes'
Form(...)-based convention rather than inventing a JSON+multipart hybrid. Route-level gating:
create is Administrator/Manager/Inspector (conducting an inspection), matching Cleaning/
VacantUnit's create tier. View has no role restriction. Update (the inspector's confirm-or-
correct step) is open to any authenticated user at the ROUTE level - the real gate is
meter_reading_service.ensure_can_edit_reading's hybrid tier, which can only be evaluated once the
specific reading (and whether it's Inspection-linked) is loaded.

list's inspection_response_id filter was added during Phase 16 Sub-phase D, not Phase 14 - the
MeterReading answer type's Question screen needs to know whether a reading already exists for
THIS response (to show the confirm/correct UI instead of the initial capture-photo one), and
InspectionResponseSchema carries no pointer back to a MeterReadingId (docs/DATABASE.md's ERD
only points the other way, MeterReadings -> InspectionResponses).

List/detail now return `MeterReadingSummaryResponse` (PropertyName/InspectionId added), for the
standalone Phase 16 module's list/detail pages - a superset of `MeterReadingResponse`, so
MeterReadingControl.jsx's existing `listMeterReadings()` calls are unaffected by the extra
fields. Unlike Cleaning/VacantUnits, no NEW routes were needed here: this list/detail were
ALREADY company-wide since Phase 14 (MeterReadings was never nested under one Inspection), so
enriching the existing ones in place was enough - see
app/repositories/meter_reading_repository.py's module docstring.
"""
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.meter_reading import MeterReadingResponse, MeterReadingSummaryResponse, MeterReadingUpdate
from app.schemas.pagination import PaginatedResponse
from app.security import roles
from app.security.dependencies import get_current_user, require_roles
from app.services import meter_reading_service

router = APIRouter(prefix="/meter-readings", tags=["meter-readings"])

_conduct_inspections = require_roles(roles.ADMINISTRATOR, roles.MANAGER, roles.INSPECTOR)


@router.post("", response_model=MeterReadingResponse, status_code=201)
def create_meter_reading(
    property_id: int = Form(...),
    meter_type: str = Form(...),
    inspection_response_id: int | None = Form(default=None),
    meter_serial_number: str | None = Form(default=None),
    inspector_notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: User = Depends(_conduct_inspections),
    db: Session = Depends(get_db),
) -> MeterReadingResponse:
    reading = meter_reading_service.create_meter_reading(
        db,
        current_user,
        property_id=property_id,
        meter_type=meter_type,
        inspection_response_id=inspection_response_id,
        meter_serial_number=meter_serial_number,
        inspector_notes=inspector_notes,
        file=file,
    )
    return MeterReadingResponse.model_validate(reading)


@router.get("", response_model=PaginatedResponse[MeterReadingSummaryResponse])
def list_meter_readings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    property_id: int | None = Query(default=None),
    meter_type: str | None = Query(default=None),
    inspection_response_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[MeterReadingSummaryResponse]:
    rows, total = meter_reading_service.list_meter_readings(
        db,
        current_user,
        page=page,
        page_size=page_size,
        property_id=property_id,
        meter_type=meter_type,
        inspection_response_id=inspection_response_id,
    )
    return PaginatedResponse(
        items=[MeterReadingSummaryResponse.from_row(r, name, insp_id) for r, name, insp_id in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{meter_reading_id}", response_model=MeterReadingSummaryResponse)
def get_meter_reading(
    meter_reading_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeterReadingSummaryResponse:
    reading, property_name, inspection_id = meter_reading_service.get_meter_reading_detail(
        db, current_user, meter_reading_id
    )
    return MeterReadingSummaryResponse.from_row(reading, property_name, inspection_id)


@router.patch("/{meter_reading_id}", response_model=MeterReadingResponse)
def update_meter_reading(
    meter_reading_id: int,
    payload: MeterReadingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeterReadingResponse:
    reading = meter_reading_service.update_meter_reading(db, current_user, meter_reading_id, payload)
    return MeterReadingResponse.model_validate(reading)
