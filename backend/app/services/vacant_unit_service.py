"""Vacant Unit Inspection (Phase 12, scope §7).

Simplest authorization shape of any module so far - a single tier, not two or three. There's no
per-property configuration table the way Cleaning needed (`Units` already exist as a first-class
entity from Phase 6), and the record itself has no `Status`/`AssignedUserId` workflow columns
(unlike MaintenanceIssues/CleaningInspections) - it's a one-time recorded finding, not its own
follow-up workflow. View: any company member. Mutate (create/update): the parent Inspection's
own assigned inspector or Administrator/Manager, reusing `inspection_service.ensure_can_edit`
directly - identical reasoning to CleaningInspection (Phase 11): recording what an inspector
found while walking a property is part of conducting that inspection. Locked with the same 409
once the parent Inspection is `Submitted`.

Scope §7's "A maintenance issue should be creatable directly from any of these questions" has no
dedicated `VacantUnitInspectionId` FK on `MaintenanceIssues` (docs/DATABASE.md's ERD lists only
`Unit`/`Inspection`/`InspectionResponse` as MaintenanceIssue's optional parents) - so this is
satisfied by the EXISTING `POST /api/maintenance-issues` accepting `PropertyId`/`UnitId`/
`InspectionId` directly, all of which a vacant-unit finding already has in hand, rather than
adding a new FK the schema was never designed to carry. No automatic MaintenanceIssue/
CleaningInspection creation happens here even when `MaintenanceRequired`/`CleaningRequired` is
flagged true - scope says "creatable," not "created automatically," and inventing that
automation isn't something this phase's requirements actually ask for.

Closes a gap flagged all the way back in Phase 6 (app/api/units.py's own module docstring):
"realistically an Inspector doing a walkthrough is often the one who discovers a unit is now
vacant... that flow belongs to the Inspection engine... which will call into unit occupancy
updates through its own service with its own permission story, not through this standalone
API." `create_vacant_unit_inspection` does exactly that: it calls `unit_service.
update_unit_occupancy` directly (which has NO permission check of its own - Units' standalone
API gates occupancy changes to Administrator/Manager only at the ROUTE level in
app/api/units.py, not inside the service function). Calling it from here, after this module's
own `ensure_can_edit` check has already run, is the "own permission story" the Phase 6 comment
anticipated - not a bypass of it.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.user import User
from app.models.vacant_unit_inspection import VacantUnitInspection
from app.repositories import vacant_unit_inspection_repository as repo
from app.schemas.enums import OccupancyStatus as OccupancyStatusEnum
from app.schemas.unit import UnitOccupancyUpdate
from app.schemas.vacant_unit_inspection import VacantUnitInspectionCreate, VacantUnitInspectionUpdate
from app.services import inspection_service, unit_service


def create_vacant_unit_inspection(
    db: Session, current_user: User, inspection_id: int, payload: VacantUnitInspectionCreate
) -> VacantUnitInspection:
    inspection = inspection_service.get_inspection(db, current_user, inspection_id)
    inspection_service.ensure_can_edit(current_user, inspection)
    if inspection.Status == "Submitted":
        raise ConflictError("Cannot record a vacant unit inspection on a submitted inspection.")

    unit = unit_service.get_unit(db, current_user, payload.UnitId)
    if unit.PropertyId != inspection.PropertyId:
        raise ValidationError("UnitId does not belong to this inspection's property.")

    record = VacantUnitInspection(
        InspectionId=inspection.InspectionId,
        UnitId=unit.UnitId,
        DateIdentifiedVacant=payload.DateIdentifiedVacant or date.today(),
        Condition=payload.Condition,
        ElectricityOn=payload.ElectricityOn,
        WaterOn=payload.WaterOn,
        HeatingWorking=payload.HeatingWorking,
        WindowsSecure=payload.WindowsSecure,
        DoorsSecure=payload.DoorsSecure,
        SignsOfLeaks=payload.SignsOfLeaks,
        SignsOfDamp=payload.SignsOfDamp,
        SignsOfPests=payload.SignsOfPests,
        CleaningRequired=payload.CleaningRequired,
        WasteItemsLeftBehind=payload.WasteItemsLeftBehind,
        MaintenanceRequired=payload.MaintenanceRequired,
        Notes=payload.Notes,
    )
    record = repo.create_vacant_unit_inspection(db, record)

    # Recording this finding IS confirming the unit is vacant - not a guess at intent, scope §7
    # frames the whole flow as "Add Empty Unit." Idempotent no-op if already Vacant.
    unit_service.update_unit_occupancy(
        db, current_user, unit.UnitId, UnitOccupancyUpdate(OccupancyStatus=OccupancyStatusEnum.VACANT)
    )

    return record


def list_vacant_unit_inspections(
    db: Session, current_user: User, inspection_id: int
) -> list[VacantUnitInspection]:
    inspection_service.get_inspection(db, current_user, inspection_id)  # 404s if not visible
    return repo.list_for_inspection(db, inspection_id)


def get_vacant_unit_inspection(
    db: Session, current_user: User, vacant_unit_inspection_id: int
) -> VacantUnitInspection:
    record = repo.get_vacant_unit_inspection_by_id(db, current_user.CompanyId, vacant_unit_inspection_id)
    if record is None:
        raise NotFoundError("Vacant unit inspection not found.")
    return record


def list_vacant_unit_inspections_for_company(
    db: Session,
    current_user: User,
    *,
    page: int,
    page_size: int,
    property_id: int | None = None,
) -> tuple[list, int]:
    """The standalone Vacant Units module's list - see repo.
    list_vacant_unit_inspections_for_company's own docstring for why this didn't exist before
    that module needed it."""
    return repo.list_vacant_unit_inspections_for_company(
        db, current_user.CompanyId, page=page, page_size=page_size, property_id=property_id
    )


def get_vacant_unit_inspection_detail(db: Session, current_user: User, vacant_unit_inspection_id: int):
    """The standalone Vacant Units module's single-detail lookup - composes three already-
    existing, already-authorized single-object fetchers (this function's own
    get_vacant_unit_inspection, inspection_service.get_inspection for PropertyId,
    unit_service.get_unit for UnitNumber), the same "compose, don't add a new joined query"
    reasoning as cleaning_service.get_cleaning_inspection_detail - a single detail lookup is
    cheap enough as three plain calls, and reusing them means no isolation logic is duplicated."""
    record = get_vacant_unit_inspection(db, current_user, vacant_unit_inspection_id)
    inspection = inspection_service.get_inspection(db, current_user, record.InspectionId)
    unit = unit_service.get_unit(db, current_user, record.UnitId)
    return record, inspection.PropertyId, unit.UnitNumber


def update_vacant_unit_inspection(
    db: Session, current_user: User, vacant_unit_inspection_id: int, payload: VacantUnitInspectionUpdate
) -> VacantUnitInspection:
    record = get_vacant_unit_inspection(db, current_user, vacant_unit_inspection_id)
    inspection = inspection_service.get_inspection(db, current_user, record.InspectionId)
    inspection_service.ensure_can_edit(current_user, inspection)
    if inspection.Status == "Submitted":
        raise ConflictError("Cannot modify a vacant unit inspection on a submitted inspection.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    return repo.save_vacant_unit_inspection(db, record)
