# AI_HANDOFF

Current status. Overwrite/update this file at the end of every session or phase — unlike
`AI_MEMORY.md`, this one should reflect the *current* state, not history.

## What has been completed

- Repo scaffolded (`backend/`, `frontend/`, `database/`, `docs/`, `prompts/`), git initialized.
- Scope document preserved (`docs/SCOPE.md`) and split into phase prompts (`prompts/`).
- **Phase 1 (Architecture) complete** — full design in `docs/PROJECT_PLAN.md`, including the
  reviewed-and-confirmed `InspectionResponse` snapshot strategy (§13.1).
- **Phase 2 (Database Design + full SQL) complete**, verified against a real local SQL Server
  instance (`localhost\SQLEXPRESS`, database `InspectIQDb`, Windows auth) — every layer, not just
  the table shapes:
  - `docs/DATABASE.md` — the 25-table design doc.
  - `database/00_CreateDatabase.sql`, `database/tables/01`–`08` — all 25 tables.
  - `database/constraints/09_Constraints.sql` — every enum `CHECK` constraint, plus 3
    `INSTEAD OF DELETE` triggers making the Phase 1 soft-delete-only requirement a real DB
    guarantee, not just a documented convention.
  - `database/indexes/10_Indexes.sql` — 43 non-clustered indexes.
  - `database/seed/11_SeedRoles.sql` (5 roles), `12_SeedInspectionTemplate.sql` (the Monthly
    Property Inspection template — 21 sections, 102 questions, per scope Prompt 4),
    `13_SeedSampleData.sql` (global default risk matrix as core config + 2 demo companies/4
    properties/11 units as local-dev-only data — `Users` deliberately NOT seeded yet, see below).
  - `database/views/14_InspectionViews.sql` — 5 reusable views (`vw_InspectionSummary`,
    `vw_OverdueInspections`, `vw_OpenMaintenanceIssues`, `vw_ActiveRiskAssessments`,
    `vw_PropertyUnitCounts`).
  - `database/reports/15_DashboardQueries.sql` — every scope §23 dashboard metric as a
    standalone, company-scoped, `ISNULL`-safe query, ready to lift into `DashboardRepository`
    in Phase 15.
  - `database/scripts/00_RunAll.sql` — **tested for real**: dropped `InspectIQDb` entirely and
    rebuilt it from nothing via this one script, then re-verified every count (25 tables, 5
    roles, 21 sections/102 questions, 2 companies/4 properties, 4 risk levels, 43 indexes, 3
    triggers, 5 views). It genuinely works end-to-end, not just "each file worked in isolation."
- **Phase 4 (FastAPI foundation) complete**, verified against the real `InspectIQDb` (not just
  "the code looks right"):
  - `backend/app/core/config.py` — `pydantic-settings`-based `Settings`, with the JWT-secret
    placeholder/length guard and `APP_DEBUG=False` default built in from day one (per
    `PROJECT_PLAN.md §12.2`, not retrofitted the way PropertyManager had to).
  - `backend/app/database/session.py` — SQLAlchemy engine/session, ODBC connection string
    builder supporting both Windows-trusted-connection (local dev) and SQL-auth-with-`Encrypt=yes`
    (production) branches.
  - `backend/app/models/base.py` — SQLAlchemy 2.0-style `DeclarativeBase`. No table models yet —
    those get added module-by-module starting Phase 5/6, not all at once.
  - `backend/app/core/exceptions.py` + handlers in `main.py` — domain exceptions
    (`NotFoundError`/`ValidationError`/`UnauthorizedError`/`ForbiddenError`/`ConflictError`) with
    HTTP status mapping; a catch-all handler that logs the real exception server-side but never
    returns it to the client.
  - `backend/app/core/logging_config.py`, `backend/app/api/health.py` — health check genuinely
    queries the DB (`SELECT 1`), not a stub that always returns 200.
  - `backend/tests/` — 6 tests, all passing against the real DB (no mocks): the health check
    over a real DB round-trip, and 5 tests exercising the JWT-secret guard (placeholder/short
    secret rejected outside dev, allowed in dev, real secret accepted, CORS origin parsing).
  - **Verified two ways**: `pytest` (in-process, via `TestClient`) AND a real `uvicorn` server
    started standalone and hit with actual `curl` over HTTP (`/api/health` and `/docs` both
    confirmed working), then cleanly stopped. Not just "tests pass" — the server genuinely runs.
- **Phase 5 (Authentication) complete**, per scope Prompt 6:
  - `app/models/company.py`, `role.py`, `user.py` (+ `UserRoles` as a plain `Table`, not a
    mapped class — pure M:N join with no extra columns).
  - `app/security/password.py` (`bcrypt`), `roles.py` (centralized role-name constants),
    `jwt.py` (access + refresh tokens — deliberately carry only `sub`/`type`, never `CompanyId`,
    since `get_current_user` always reloads the full user from the DB anyway),
    `dependencies.py` (`get_current_user` re-checks `IsActive` from the DB on every request;
    `require_roles(*names)` factory dependency).
  - `app/repositories/user_repository.py`, `app/services/auth_service.py` (login, token issuance,
    refresh — same generic "Incorrect email or password." message whether the email doesn't
    exist, the password is wrong, or the account is disabled, to avoid account enumeration).
  - `app/api/auth.py` — `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me`.
  - `backend/tests/test_auth.py` — 12 new tests (18 total now), all against the real DB with
    throwaway users cleaned up in fixture teardown: login success/wrong-password/no-such-user/
    disabled-account, `/me` with valid/missing/garbage token, **the deactivation-mid-session
    case** (issue a token, deactivate the user, confirm the same token is rejected on the very
    next request), refresh token success + rejecting an access token used as a refresh token,
    and `require_roles` accept/reject.
  - **A real bug was found and fixed only by testing with an actual running server, not by
    pytest**: `User.company` relationship referenced `"Company"` by string, but nothing at
    runtime ever imported `app.models.company` outside `TYPE_CHECKING` — every `pytest` test
    passed anyway because `tests/test_auth.py` happens to import `Company` directly for its own
    fixture, which incidentally registered it first and masked the bug. `POST /api/auth/login`
    against a real running server returned a raw 500 for a nonexistent email. Fixed with
    `app/models/__init__.py` importing every model together, itself imported from
    `app/database/session.py` so it's guaranteed to run before any query. Full story in
    `docs/AI_MEMORY.md`'s 2026-08-23 Phase 5 entry.
  - `backend/scripts/seed_demo_users.py` — one-off script (run via
    `python -m scripts.seed_demo_users` from `backend/`) using the app's real `hash_password`,
    closing the gap flagged since Phase 2: 6 working demo logins now exist (5 Northgate — one
    per role — + 1 Bright Spaces Administrator), all password `Password123!`. Verified for real:
    logged in as `admin@northgatepm.example` against a live server and got back real tokens.
- **Phase 6 (Properties + Units) complete**, per scope Prompt 7, verified against the real DB
  and a real running server:
  - `app/models/property.py`, `unit.py` (both added to `models/__init__.py` immediately, before
    writing any route — applying the Phase 5 lesson instead of relearning it).
  - `app/schemas/enums.py` — `PropertyType`/`PropertyStatus`/`InspectionFrequency`/
    `OccupancyStatus` as Python enums mirroring the DB `CHECK` constraints exactly, so a bad
    value gets a clean 422 before reaching SQL Server. **Real Python-3.14-specific gotcha hit
    and fixed**: a Pydantic field named the same as its own enum type (e.g.
    `PropertyType: PropertyType`) fails under Python 3.14's lazy annotation evaluation (PEP
    649) — confirmed with a real `TypeError: unsupported operand type(s) for |: 'NoneType' and
    'NoneType'` before fixing it by aliasing every enum import (`PropertyType as
    PropertyTypeEnum`, etc.) in `schemas/property.py` and `schemas/unit.py`.
  - `app/schemas/pagination.py` — one generic `PaginatedResponse[T]` reused by both modules.
  - `app/repositories/property_repository.py` (has its own `CompanyId` column, straightforward
    isolation filter), `unit_repository.py` (Units has **no** `CompanyId` column of its own —
    every query joins through `Properties` and filters on `Properties.CompanyId`).
  - `app/services/property_service.py`, `unit_service.py` — **cross-company access returns 404,
    not 403**, a deliberate choice so a property/unit belonging to another company is
    indistinguishable from one that doesn't exist (verified with a real cross-company test and
    live curl request, not just asserted).
  - `app/api/properties.py`, `units.py` — list/get open to any authenticated company user
    (view), create/update/deactivate/occupancy-change gated to Administrator/Manager via
    `require_roles`. **Interpretive call, documented in the route file itself**: the scope's
    "Inspectors can view properties they have permission to inspect" has no per-property
    assignment table in the schema, so "permission to inspect" was read as company membership.
  - 14 new tests (32 total), all against the real DB with throwaway users/properties/units
    cleaned up per-test: authentication required, company-scoped listing, cross-company 404 on
    both properties and units (including creating a unit under another company's property),
    role-based create authorization, invalid-enum rejection, partial-update semantics,
    deactivate hiding from the default list but not direct lookup, the dedicated
    occupancy-change endpoint proven independent from the general PATCH.
  - **Verified live**: real demo login → list properties → list units → cross-company 404, all
    against a genuinely running server with the actual seeded demo data, not just pytest.
- **Phase 7 (Inspection Templates API) complete** — deliberately scoped as read-only (list +
  full-nested-detail), since scope §9 treats template *authoring* as an "eventually" feature,
  not MVP-critical; these two endpoints exist because Phase 8 (the inspection engine) will need
  to fetch a template to start an inspection from:
  - `app/models/inspection_template.py`, `inspection_section.py`, `inspection_question.py` —
    added to `models/__init__.py` immediately, and a real query against them (`SessionLocal` +
    the relationships) was run and checked *before* writing any route, applying the Phase 5
    lesson proactively rather than discovering a registration bug live again.
  - Both `sections` and `questions` relationships carry `order_by=...SortOrder` at the model
    level, so every query path (list, detail, future inspection-start logic) gets them in the
    right order for free — not left to callers to remember.
  - `app/repositories/inspection_template_repository.py` — the "global default + per-company
    override" isolation pattern (`CompanyId IS NULL OR CompanyId = @company_id`), same family as
    `RiskMatrixLevels`. A company-specific template belonging to another company matches neither
    condition, so it's excluded by the `WHERE` clause itself — the same 404-not-403 outcome as
    Properties/Units, achieved here without an extra check.
  - `GET /api/inspection-templates` (lightweight list), `GET /api/inspection-templates/{id}`
    (full nested Sections→Questions tree in one response — a mobile client needs the whole
    checklist structure at once, not N+1 calls per section).
  - 5 new tests (37 total): auth required, the global default appears in the list (and the list
    response omits nested `Sections`), the detail response returns all 21 sections/102 questions
    in the correct `SortOrder`, a nonexistent template 404s, and a throwaway company-specific
    template is invisible to another company both by direct ID and in the list view.
  - **A real test-cleanup wrinkle, not an app bug**: the throwaway company-specific template
    created for the isolation test hit the Phase 2 `INSTEAD OF DELETE` trigger on hard `DELETE`
    (working as designed — it protects real data). Test teardown uses the same
    disable-trigger/delete/re-enable-trigger pattern originally used to verify the trigger
    itself, and explicitly confirms afterward that the trigger is back to `is_disabled = 0` —
    this escape hatch is for test cleanup only, application code must never use it.
  - **Verified live**: a real Inspector demo login listed the template and fetched its full
    102-question structure over actual HTTP, not just through pytest.
- **Phase 8 (Inspection Engine) complete** — the biggest phase so far, per scope Prompt 8.
  Deliberately excludes photos/videos (Phase 9), creating a maintenance issue or risk
  assessment from a response (Phases 10/13 — those modules don't exist yet), and any
  "Scheduled"/"Cancelled" status transitions (no endpoint requests them in Prompt 8's own
  action list) — noted explicitly in `app/api/inspections.py`'s module docstring.
  - `app/models/inspection.py`, `inspection_response.py` — added to `models/__init__.py` and
    sanity-queried against real data before any route was written (now a standing habit, not a
    one-off). `Inspection.responses` and both template relationships carry `order_by=...` at
    the model level; `InspectionResponse` ordering relies on `InspectionResponseId` (creation
    order), since responses are batch-inserted in template `SortOrder` at start time and
    `SortOrder` itself is deliberately *not* one of the frozen snapshot columns — reordering the
    live template later must never reshuffle an already-started inspection's response order,
    which a live join would risk.
  - `app/services/inspection_service.py` — the actual engine: `start_inspection` resolves and
    isolation-checks the property/template (reusing `property_service`/
    `inspection_template_service`, not reimplementing the check), self-assigns
    `InspectorUserId` to the current user (no "assign to someone else" flow exists),
    batch-creates one frozen `InspectionResponse` per active question. `calculate_completion_percentage`
    counts a response as done if answered (non-empty `AnswerText`) or marked N/A.
    `update_response` validates `YesNo`/`PassFail` answers strictly against a fixed set (a typo
    there is meaningless, not a matter of taste) and keeps `AnswerText` in sync when
    `AnswerNumber`/`AnswerDate` is what was actually sent. `submit_inspection` checks mandatory
    questions against the **live** `InspectionQuestion.IsMandatory` (a deliberate, documented
    exception to "always use the snapshot" — a validation *rule* reasonably applies as currently
    configured, unlike response *content*, which must stay historically frozen).
  - **A narrower authorization rule than every other module so far**: only the inspection's own
    assigned inspector, or an Administrator/Manager, can answer questions or submit — a plain
    Inspector role at the company is *not* enough, unlike Properties/Templates' "any company
    member can view, Admin/Manager can mutate." Documented explicitly in
    `inspection_service._ensure_can_edit` as a deliberate departure, since an in-progress
    inspection is one specific person's active work, not shared company data. Verified with a
    real second-inspector test (403) and a real manager-override test (200).
  - **Immutability after submission is enforced at the service layer, not the DB** (unlike
    `InspectionTemplates`' real trigger) — `update_response`/`submit_inspection` both check
    `Status == "Submitted"` and reject with 409. Verified: editing a response after submit
    returns 409; submitting twice returns 409 (this is also literally the "duplicate submission"
    edge case scope's Prompt 19 testing checklist calls out — covered here, ahead of Phase 18).
  - `GET/POST /api/inspections`, `GET /api/inspections/{id}`,
    `PATCH /api/inspections/{id}/responses/{id}`, `POST /api/inspections/{id}/submit`. No
    separate "resume" endpoint — resuming is just re-fetching an in-progress inspection, since
    every answer saves immediately (no draft/staging state exists).
  - 14 new tests (51 total): snapshot creation in correct order/count, cross-company 404 on
    start and on get, role-gated start (Maintenance blocked), answer validation (bad `YesNo`
    value rejected, `AnswerNumber` correctly normalizes `AnswerText`), the
    assigned-inspector-only rule (both the 403 and the manager-override 200), completion
    percentage math verified against an exact expected value (not just "some percentage
    changed"), mandatory-question submit gating, duplicate-submission 409, post-submission
    immutability 409.
  - **Verified live**: a real Inspector login → real property → real template → started a real
    inspection (21 sections, 102 responses) → answered one question → confirmed completion moved
    to exactly 1.0% → attempted submit and got back the correct "12 mandatory questions remain"
    message (13 total mandatory minus the one just answered) — all over actual HTTP against the
    real seeded data, then cleaned up.
- **Phase 9 (Photo & Video Uploads) complete**, per scope §20 / `PROJECT_PLAN.md §8`. No new
  SQL — `MediaFiles` has existed since Phase 2.
  - `app/services/media_storage.py` — `IMediaStorageService` Protocol (`save`/`open_stream`/
    `get_url`/`delete`) + `LocalFileStorageService` (dev; files under `backend/uploads/`,
    gitignored). `open_stream` is an addition to the original §8 sketch — see the module
    docstring for why local dev needs it (no static file server, since that would bypass the
    per-request permission check) and how the production blob implementation should use
    `get_url` instead (Phase 20).
  - `app/models/media_file.py`, `app/schemas/media_file.py`, `app/repositories/
    media_file_repository.py` — the usual layering; `MediaFiles` has its own denormalized
    `CompanyId` (docs/DATABASE.md §7), so get/list filter on it directly rather than joining
    through a parent entity.
  - `app/services/media_service.py` — the actual authorization logic. Two levels per entity
    type: **view** (list/download) reuses each parent module's own "get" (any company member);
    **mutate** (upload) is the SAME as view for Property/Unit (scope gives Inspector "upload
    evidence" as its own capability, separate from editing the property/unit record), but for
    Inspection/InspectionResponse reuses `inspection_service.ensure_can_edit` — the Phase 8
    assigned-inspector-or-Admin/Manager rule (renamed from `_ensure_can_edit`, made
    module-public for this reuse). Caption-edit/delete are narrower still: uploader or
    Admin/Manager only. `SUPPORTED_ENTITY_TYPES` originally excluded MeterReading/
    MaintenanceIssue/RiskAssessment/CleaningInspection, whose own services didn't exist yet;
    all of them have since been added (MaintenanceIssue Phase 10, CleaningInspection Phase 11,
    VacantUnitInspection Phase 12, RiskAssessment Phase 13, MeterReading Phase 14, see below) —
    `SUPPORTED_ENTITY_TYPES` now covers every entity type scope §20 names, nothing left deferred.
  - `app/repositories/inspection_response_repository.py` gained
    `get_response_by_id_for_company` — the one function there that takes `company_id` directly
    (documented as a deliberate exception to the file's own "no company_id param" rule), needed
    because media's `EntityType`/`EntityId` pair gives only a bare `response_id`, with no
    already-authorized `InspectionId` in hand yet the way every other caller has.
  - `app/api/media.py` — generic polymorphic router (`POST/GET /api/media`,
    `GET /api/media/{id}`, `GET /api/media/{id}/download`, `PATCH /api/media/{id}`,
    `DELETE /api/media/{id}`), not nested per parent module.
  - **A real bug found only by testing with an actual running server on Windows**: the first
    `/download` implementation handed `open_stream()`'s raw file object straight to
    `StreamingResponse`, which iterates content but never closes it — the handle leaked on
    every download. Surfaced as a genuine `PermissionError: [WinError 32]` the moment a test
    tried to delete the same file right after downloading it. Fixed with an `_iter_and_close`
    generator in `app/api/media.py` that reads in chunks and closes the stream in `finally`.
    Full story in `docs/AI_MEMORY.md`'s 2026-08-24 entry.
  - 8 new tests (59 total), all against the real DB with throwaway users/media rows/files
    cleaned up per-test (files actually deleted from `backend/uploads/`, not just DB rows):
    upload+download+list round-trip (byte-for-byte content check), cross-company 404 on upload,
    unsupported EntityType/content-type both 422, delete-by-uploader removes row+file, delete by
    non-uploader-non-admin 403, upload to an Inspection by an unassigned Inspector 403, caption
    update by the uploader.
  - **Verified live**: real Inspector login → real property → upload via curl → download
    (byte-for-byte match) → list → cross-company 404 (Bright Spaces admin) → delete → confirmed
    gone (404) → confirmed no orphaned file left in `backend/uploads/`.
- **Phase 10 (Maintenance Issue System) complete**, per scope §17/§18. No new SQL —
  `MaintenanceIssues`/`MaintenanceUpdates` have existed since Phase 2.
  - `app/models/maintenance_issue.py`, `maintenance_update.py` — added to `models/__init__.py`
    and sanity-queried before any route was written (the now-standing habit since Phase 5).
  - **Three authorization tiers, not two** — see `app/services/maintenance_service.py`'s module
    docstring for the full reasoning: view (any company member) · general field edits + assign
    (Administrator/Manager only, gated at the ROUTE level via `require_roles`, same as
    Properties/Units) · status/notes/photos (the issue's own `AssignedUserId`, or
    Administrator/Manager — reuses Phase 8's `ensure_can_edit` shape, gated at the SERVICE level
    because the assignee can hold any role, so a route-level role list can't express it).
  - `create_issue` handles both entry points from one endpoint: a manual `PropertyId`, or an
    `InspectionResponseId`/`InspectionId` that the service resolves the Property from itself
    (scope §17: "automatically copying Property, Inspection..." — the client-supplied
    `PropertyId` is ignored/overridden whenever a response/inspection is linked, never trusted
    alongside one). `Location` auto-fills from the response's `SectionNameSnapshot`/
    `QuestionTextSnapshot` when not explicitly supplied — no separate section/question columns
    were added to `MaintenanceIssues` itself, since `InspectionResponseId` is already a stable
    FK back to the authoritative snapshot.
  - **A genuine two-service circular dependency, resolved with local imports on both sides**:
    `maintenance_service.upload_photo` needs `media_service.upload_media` (to reuse validation/
    storage without duplicating it), and `media_service`'s own entity-type dispatch for
    `EntityType="MaintenanceIssue"` needs to call BACK into `maintenance_service.get_issue`/
    `ensure_can_edit`. Both sides use a function-local `from app.services import ...` instead of
    a top-level import — documented in both files at the exact lines involved. Confirmed working
    (not just "should work") both via `app.main` importing cleanly and via a live curl upload
    that produced a real `MediaFile` row.
  - `app/repositories/inspection_response_repository.py`'s `get_response_by_id_for_company`
    (added in Phase 9) got its second caller here — proof it generalizes, not a one-off.
  - `app/api/maintenance.py` — `POST/GET /api/maintenance-issues`, `GET /{id}`,
    `GET /{id}/timeline`, `PATCH /{id}` (general edit, Admin/Manager), `PATCH /{id}/assign`
    (Admin/Manager — auto-advances `Open` → `Assigned`, never moves a further-along issue
    backwards on reassignment), `PATCH /{id}/status` (assigned-or-Admin/Manager; sets
    `CompletedDate` once on first entering `Completed`; rejects a no-op transition to the same
    status with 422), `POST /{id}/notes`, `POST /{id}/photos` (writes a `PhotoUploaded` timeline
    entry after delegating the actual upload to `media_service`).
  - 14 new tests (73 total), all against the real DB with issues/updates/media files cleaned up
    per-test (including the file on disk): manual create, role-gated create (Maintenance
    blocked), cross-company 404 on create, missing-Property-and-Inspection 422, create-from-
    response derives Property/Inspection/Location correctly, assignment auto-sets
    `AssignedUserId` and starting status, cross-company get 404, general-edit Admin-only (403
    for the assigned Maintenance worker), assign moves Open→Assigned with a timeline entry,
    status update by the assigned user succeeds while an unassigned user gets 403 and a
    same-status transition gets 422, `Completed` sets `CompletedDate`, note-adding writes a
    `Comment` timeline entry, photo upload writes both a `MediaFile` and a `PhotoUploaded`
    timeline entry (checked via both the maintenance detail response AND the generic
    `/api/media` list, proving the cross-service integration end-to-end).
  - **Verified live**: real Inspector login created an issue → real Admin assigned it to the
    Maintenance demo user (Open → Assigned) → the unassigned Inspector got 403 on a status
    update, the assigned Maintenance worker got 200 (Assigned → InProgress) → a note was added →
    a real photo was uploaded via curl and appeared both in the issue's timeline (`PhotoUploaded`)
    and in `GET /api/media?entity_type=MaintenanceIssue...` → Bright Spaces admin got 404 on the
    issue → all test data cleaned up from the DB and `backend/uploads/` afterward (confirming the
    `SET ANSI_NULLS ON`/`SET QUOTED_IDENTIFIER ON` gotcha from Phase 2 still applies to any
    hand-written cleanup script touching `MaintenanceIssues`, which carries a filtered index).
- **Phase 11 (Communal Cleaning Grading) complete**, per scope §16. No new SQL —
  `CleaningAreas`/`CleaningInspections` have existed since Phase 2.
  - `app/models/cleaning_area.py`, `cleaning_inspection.py` — added to `models/__init__.py` and
    sanity-queried before any route was written. Neither table has a denormalized `CompanyId`
    (unlike MediaFiles/MaintenanceIssues) — `app/repositories/cleaning_repository.py` joins
    through `Properties` for `CleaningArea` isolation and through `Inspections`→`Properties` for
    `CleaningInspection` isolation.
  - **Two tiers, deliberately simpler than Maintenance's three** — see
    `app/services/cleaning_service.py`'s module docstring: `CleaningAreas` (per-property config)
    mirror Properties/Units exactly (view = any company member, mutate = Admin/Manager,
    route-gated). `CleaningInspections` (grading records, always tied to a real `Inspection` —
    `InspectionId` is `NOT NULL` by design) mirror the Inspection engine instead: view = any
    company member, mutate = the inspection's own assigned inspector or Admin/Manager, reusing
    `inspection_service.ensure_can_edit` directly — no independent "assignee can edit" carve-out
    the way MaintenanceIssue has one, since there's no "Cleaner" role in this system and
    `AssignedUserId` here just names who should do the work, not who's authorized to grade it.
    Locked with the same 409 once the parent Inspection is `Submitted`.
  - **Closed a real, previously-flagged gap**: `docs/DATABASE.md §10`'s "Possible Problems" #5
    warned that a new property gets zero `CleaningAreas` until someone configures them — noted
    at Phase 1 as "decide during Phase 6," but Phase 6 shipped without addressing it.
    `property_service.create_property` now calls
    `cleaning_service.seed_default_areas_for_property` right after creating a property, seeding
    the exact 3-area default (Entrance/Hallway/BinArea) `DATABASE.md` itself suggested. Existing
    pre-Phase-11 seeded demo properties are unaffected (only newly-created ones get seeded) —
    "15 High Road" has no communal areas of its own (it's an HMO); "Elm Court" does, from the
    original Phase 2 demo data.
  - **A second real circular-import situation, resolved two different ways depending on
    direction**: `property_service.create_property` needs `cleaning_service` (to seed areas) —
    a function-LOCAL import, mirroring Phase 10's `media_service`↔`maintenance_service` pattern,
    since `cleaning_service` imports `property_service` at the top level for its own
    authorization checks. But `media_service`'s new `CleaningInspection` entity-type resolver
    uses a plain TOP-level import of `cleaning_service` instead — there's no cycle on that side,
    since `cleaning_service` never needs to import `media_service` back (no photo-upload
    convenience wrapper was needed here, unlike Maintenance's). Worth remembering: the fix isn't
    "always use a local import for cross-service calls," it's "use one only where an actual
    cycle exists" — confirmed by checking each direction independently rather than copying the
    Phase 10 workaround by default.
  - `app/api/cleaning.py` — `POST/GET /api/properties/{id}/cleaning-areas`,
    `PATCH /api/cleaning-areas/{id}`, `POST/GET /api/inspections/{id}/cleaning`,
    `PATCH /api/cleaning-inspections/{id}` — one router with mixed paths and no shared prefix,
    the same pattern `units.py` already established for a sub-resource nested under two
    different parents.
  - 12 new tests (85 total), all against the real DB with areas/inspections/media cleaned up
    per-test: auto-seed-on-create (3 areas, correct types), area create/update role gating and
    cross-company 404, grade-create as the assigned inspector, `AssignedUserId` at create time
    starting `Status="Assigned"`, a `CleaningAreaId` from a different property rejected 422, an
    unassigned inspector 403, grading a `Submitted` inspection 409, a partial `PATCH` proven to
    leave other fields untouched, and a photo uploaded through the *generic* `/api/media`
    endpoint with `EntityType="CleaningInspection"` — proving that integration end-to-end, not
    just at the import level.
  - **A real test-fixture gap, not an app bug**: an early test fixture assumed the demo property
    "15 High Road" would have an `Entrance` `CleaningArea` (it doesn't — only "Elm Court" got
    seeded communal areas in Phase 2's demo data, and Phase 11's auto-seed only applies to newly
    created properties). Fixed by having the fixture create its own throwaway area rather than
    depending on which demo property happens to have one.
  - **Verified live**: created a real property via curl → confirmed exactly 3 auto-seeded areas
    → started a real inspection → graded a communal area (`Pending`) → a Bright Spaces admin got
    404 on the cleaning list → an Admin override updated the grade to `Completed` → a real photo
    uploaded via `EntityType=CleaningInspection` appeared in the generic media list → all test
    data (property, areas, inspection, responses, cleaning grade, media row and file) cleaned up
    afterward.
- **Phase 12 (Vacant Unit Inspection) complete**, per scope §7. No new SQL —
  `VacantUnitInspections` has existed since Phase 2.
  - `app/models/vacant_unit_inspection.py` — added to `models/__init__.py` and sanity-queried
    before any route was written. Every `BIT` column (`ElectricityOn`, `WaterOn`, etc.) is
    nullable with no DB default — kept genuinely tri-state (`bool | None`, `None` = not
    checked) through the ORM and Pydantic schemas rather than defaulting to `False`, which would
    silently misreport "confirmed off" for something the inspector simply skipped.
  - **Simplest authorization shape yet — a single tier, not two or three**: view (any company
    member) · create/update (the parent `Inspection`'s own assigned inspector or Admin/Manager,
    reusing `inspection_service.ensure_can_edit` directly, same as Phase 11's
    `CleaningInspection`). No per-property config table was needed the way Cleaning needed
    `CleaningAreas` (`Units` already exist from Phase 6), and the record itself has no
    `Status`/`AssignedUserId` workflow columns at all — it's a one-time recorded finding, not
    its own follow-up workflow. See `app/services/vacant_unit_service.py`'s module docstring.
  - **Closed a second gap flagged since Phase 6** (`app/api/units.py`'s own docstring:
    "realistically an Inspector doing a walkthrough is often the one who discovers a unit is now
    vacant... that flow belongs to the Inspection engine... with its own permission story").
    `create_vacant_unit_inspection` now calls `unit_service.update_unit_occupancy` directly
    right after recording the finding, flipping the unit to `Vacant` — that service function has
    NO permission check of its own (Units' standalone API gates occupancy changes to
    Administrator/Manager only at the ROUTE level, not inside the service), so calling it here
    — after this module's OWN `ensure_can_edit` check has already run — is exactly the "own
    permission story" the Phase 6 comment anticipated, not a bypass. Confirmed live: an
    Inspector (not Admin/Manager) recording a vacant-unit finding successfully flipped a real
    demo unit's `OccupancyStatus`.
  - Scope §7's "a maintenance issue should be creatable directly from any of these questions"
    has no dedicated `VacantUnitInspectionId` FK on `MaintenanceIssues` (`docs/DATABASE.md`'s
    ERD lists only `Unit`/`Inspection`/`InspectionResponse`) — satisfied by the EXISTING
    `POST /api/maintenance-issues` accepting `PropertyId`/`UnitId`/`InspectionId` directly
    (documented as a deliberate interpretive call in `vacant_unit_service.py`, not a gap). No
    automatic MaintenanceIssue/CleaningInspection creation happens even when
    `MaintenanceRequired`/`CleaningRequired` is flagged true — scope says "creatable," not
    "created automatically."
  - Added `VacantUnitInspection` to `media_service.py`'s supported entity types (scope §7 lists
    Photos/Videos) — a plain top-level import, same as `CleaningInspection`; no circular
    dependency on this side either.
  - `app/api/vacant_units.py` — `POST/GET /api/inspections/{id}/vacant-unit-inspections`,
    `PATCH /api/vacant-unit-inspections/{id}`.
  - 7 new tests (92 total), all against the real DB: create-as-assigned-inspector (with the
    occupancy-flip verified via a real `GET /api/units/{id}` call, and the nullable tri-state
    fields checked to stay `None`, not `False`, when never supplied), a `UnitId` from another
    property rejected 422, an unassigned inspector 403, a `Submitted` inspection 409,
    cross-company 404, a partial `PATCH` proven to leave other fields untouched, and a photo
    uploaded through the generic `/api/media` endpoint with `EntityType=VacantUnitInspection`.
    One fixture (`occupied_unit_id`) deliberately mutates real seeded demo data (flips "Flat 1"
    to test the occupancy side effect) and restores it to `Occupied` in teardown — the only test
    fixture in this project that mutates shared seed data rather than only adding/removing its
    own throwaway rows, called out explicitly in the fixture's own docstring.
  - **Verified live**: a real Inspector recorded a vacant-unit finding on a real demo unit
    (currently `Occupied`) → confirmed the response's nullable fields stayed genuinely `null`
    for anything not supplied → confirmed the unit flipped to `Vacant` via a real `GET` →
    confirmed a Bright Spaces admin got 404 on the list → uploaded a real photo via
    `EntityType=VacantUnitInspection` → updated the record's `Notes` via `PATCH` → all of it
    (inspection, its 102 snapshot responses, the vacant-unit record, the media row and file)
    cleaned up afterward, including manually restoring the demo unit's `OccupancyStatus` back
    to `Occupied`.
- **Phase 13 (Risk Assessments) complete**, per scope §19. No new SQL —
  `RiskAssessments`/`RiskMatrixLevels` have existed since Phase 2.
  - `app/models/risk_assessment.py`, `risk_matrix_level.py` — added to `models/__init__.py` and
    sanity-queried before any route was written, including a real **insert-then-refresh test**
    to confirm the `Computed` mapping for `RiskScore` actually works end-to-end (not just
    imports cleanly) before building anything on top of it — `RiskScore` is the project's first
    real SQL Server `PERSISTED` computed column touched by the ORM; `Computed("Likelihood *
    Severity", persisted=True)` tells SQLAlchemy to exclude it from generated INSERT/UPDATE
    statements automatically, and the repository's existing `db.refresh()` after insert
    populates it back from the server. Confirmed with a real `Likelihood=4, Severity=5` insert
    that came back `RiskScore=20` before any route existed.
  - **A third distinct authorization shape — two tiers, but not the same two as Cleaning's**,
    re-derived independently rather than copied: view (any company member) · create
    (Administrator/Manager/Inspector — raising a hazard is the same tier Maintenance's create
    uses) · update (Administrator/Manager only, covering EVERY field including `Status`/
    `ResponsiblePersonUserId` in ONE combined `PATCH`, no separate assign/status endpoints and
    no assigned-inspector carve-out). The reasoning for the update tier, either half sufficient
    on its own: scope §19 names no audit-trail requirement the way §18 explicitly names
    "Maintenance History," and — structurally — `RiskAssessment.InspectionId` is NULLABLE, so a
    standalone Property-level risk register entry may have no parent `Inspection` at all to run
    `ensure_can_edit` against. See `app/services/risk_service.py`'s module docstring.
  - `create_risk_assessment` follows the exact `MaintenanceIssueCreate`/`CleaningInspectionCreate`
    linkage convention: a manual `PropertyId`, or `InspectionId`/`InspectionResponseId` that
    derives `PropertyId` server-side (never trusted from the client alongside one); an optional
    `MaintenanceIssueId` link is isolation-checked via `maintenance_service.get_issue` but does
    NOT independently derive `PropertyId` (scope's own create-form field list only names
    Property/Inspection, not MaintenanceIssue — the FK exists per `docs/DATABASE.md`'s ERD for
    linking, not as its own creation path).
  - **`RiskMatrixLevels` gets its own small CRUD surface** — not optional polish, scope §19
    says outright "the exact risk matrix should remain configurable." View: any company member
    (rates/colors aren't sensitive). Create/update: Administrator/Manager only, matching
    `CleaningAreas`' exact per-company-configuration shape. **A company's own bands fully
    REPLACE the global default the moment any exist** — a real, deliberate override, NOT the
    additive "global + company" list `InspectionTemplates` uses, because mixing leftover global
    bands with a company's own could leave score gaps or overlaps a coherent matrix must never
    have (`app/repositories/risk_repository.py`'s `get_risk_matrix_for_company`). No delete
    endpoint — a matrix's bands must stay contiguous, and scope doesn't ask for that lifecycle
    management.
  - `RiskAssessment`'s media mutate check is the SAME function as its view check (any company
    member) — matching Property/Unit's "upload evidence is broader than edit" shape, NOT
    Maintenance/Cleaning/VacantUnit's narrower `ensure_can_edit`-based one. Confirmed live: an
    Inspector who got a genuine 403 trying to `PATCH` a risk assessment successfully uploaded a
    photo to the same record moments later.
  - `app/api/risk.py` — `GET/POST /api/risk-matrix-levels`, `PATCH /api/risk-matrix-levels/{id}`,
    `POST/GET /api/risk-assessments`, `GET /api/risk-assessments/{id}`,
    `PATCH /api/risk-assessments/{id}`.
  - 16 new tests (108 total), all against the real DB: standalone create with `RiskScore`/
    `RiskLevel` verified against two different score bands (20→Critical, 6→Medium), role-gated
    create (Maintenance blocked, Inspector allowed), missing-Property-and-Inspection 422,
    cross-company 404 on create, create-from-response deriving Property/Inspection correctly,
    cross-company get 404, an Admin update that changes `Severity` and confirms `RiskLevel` is
    RE-derived (not left stale), an Inspector getting 403 on update EVEN FOR THEIR OWN just-created
    record (proving the tier really is role-based, not ownership-based), the global default
    matrix, a company override fully replacing the global default (verified both on a
    subsequent risk assessment's resolved level AND that a *different* company's matrix is
    unaffected), `MinScore > MaxScore` rejected 422, and photo upload by an Inspector who
    cannot edit the record.
  - **Verified live**: real Inspector login created a risk assessment (`Likelihood=4,
    Severity=4` → confirmed `RiskScore=16`, `RiskLevel="High"`) → the same Inspector got a real
    403 trying to `PATCH` it → a real Admin update changed `Severity` and confirmed `RiskLevel`
    recomputed to `"Low"` → a Bright Spaces admin got 404 on the record → the Inspector
    successfully uploaded evidence to the same record they couldn't edit → all test data (the
    assessment, media row, and file) cleaned up afterward.
- **Phase 14 (AI/OCR Meter Reading) complete**, per scope §11. No new SQL —
  `MeterReadings` has existed since Phase 2. `SUPPORTED_ENTITY_TYPES` in `media_service.py` now
  covers every scope §20 entity type — MeterReading was the last one.
  - `app/models/meter_reading.py` — added to `models/__init__.py` and sanity-queried before any
    route was written. `AIDetectedReading`/`ConfirmedReading` stay separate columns, matching
    the DB design exactly — scope §11 is explicit the AI value must never silently become the
    confirmed one. `PhotoMediaFileId` is a direct 1:1 FK to one `MediaFiles` row, unlike every
    other module's polymorphic many-photos pattern — the row still gets created through the SAME
    `EntityType="MeterReading"` polymorphic mechanism as everywhere else, just with this column
    denormalizing a pointer to it, since a meter reading has exactly one confirmable photo.
  - `app/services/meter_ocr.py` — `IMeterReadingOcrService` Protocol (mirroring
    `IMediaStorageService`'s local-now/swappable-later shape from Phase 9) + a
    `MockMeterReadingOcrService` that returns scope §11's own illustrative example value
    (`18294.6`, confidence `0.87`) without inspecting the actual image — a real OCR/vision API
    integration is a future drop-in second implementation of the same Protocol, per scope's own
    "mock provider first" instruction.
  - **A genuinely hybrid authorization tier** for confirm/update — not copied wholesale from
    Cleaning/VacantUnit's Inspection-anchored pattern OR Risk's Admin/Manager-only one, because
    `MeterReading.InspectionResponseId` is nullable (like Risk) but scope §11's own flow text
    explicitly names "the inspector" as who confirms/corrects (unlike Risk, where nothing
    suggests the raiser should be the closer). `ensure_can_edit_reading` checks both facts:
    Inspection-linked → reuses `inspection_service.ensure_can_edit`; standalone → falls back to
    Administrator/Manager only. See `app/services/meter_reading_service.py`'s module docstring.
  - **A real bug, caught by a failing test before it ever reached a route**: the first version
    of `MeterReading`'s media MUTATE check reused `ensure_can_edit_reading` directly (the
    confirm/update tier) — which 403'd the very Inspector legitimately creating a brand-new
    STANDALONE reading, since a freshly-created reading has no `AssignedUserId`/Inspection yet
    to satisfy that check. Fixed by making the media mutate check the SAME as the view check
    (any company member), matching `RiskAssessment`'s exact reasoning: the photo is attached
    automatically as an integral part of CREATE (a broader, earlier moment, already gated by the
    route's own Administrator/Manager/Inspector role check), while `ensure_can_edit_reading`'s
    narrower hybrid tier governs only the SEPARATE later confirm-or-correct action. Full story
    in `docs/AI_MEMORY.md`'s 2026-08-24 entry.
  - Create is one combined multipart request (property/meter details + the photo together via
    `Form(...)`/`File(...)`, not a JSON body), matching the maintenance/cleaning photo-upload
    routes' convention — it triggers store-reading → upload-photo-through-the-polymorphic-
    system → run-mock-OCR → return-the-AI-reading as one atomic action, mirroring scope §11's
    own flow exactly.
  - `app/api/meter_readings.py` — `POST/GET /api/meter-readings`, `GET /api/meter-readings/{id}`,
    `PATCH /api/meter-readings/{id}` (the confirm/correct step).
  - 11 new tests (119 total), all against the real DB: create runs the mock OCR and returns the
    expected fixed values with `ConfirmedReading` still `None`, role-gated create (Maintenance
    blocked), cross-company 404 on create, invalid `MeterType` 422, create linked to a real
    `InspectionResponse` correctly stores the link, cross-company get 404, the photo visible via
    the *generic* `/api/media` endpoint (proving the polymorphic integration), confirm by the
    assigned inspector (Inspection-linked) succeeds while confirm by a DIFFERENT inspector 403s,
    confirm on a STANDALONE reading 403s for an Inspector but succeeds for an Admin (the hybrid
    tier's two branches, both exercised), and a basic list/filter check.
  - **Verified live**: a real Inspector uploaded a real meter photo via curl → the mock OCR
    returned `AIDetectedReading=18294.6000`/`AIConfidence=0.8700` matching scope's own example →
    that same Inspector got a real 403 trying to confirm their own standalone reading → a real
    Administrator successfully confirmed it → a Bright Spaces admin got 404 on the record → the
    photo appeared correctly via a plain `GET /api/media?entity_type=MeterReading...` call → all
    test data (the reading, media row, and file) cleaned up afterward.
- **Phase 15 (Dashboard API) complete**, per scope §23. No new SQL, no new authorization design -
  view = any company member, same as every other module's read side. The thinnest phase since
  Phase 7: `database/reports/15_DashboardQueries.sql` already had every metric as a standalone,
  company-scoped, `ISNULL`-safe query since Phase 2, written specifically to be lifted into this
  phase.
  - `app/repositories/dashboard_repository.py` - nine functions, each mirroring one query block
    in `15_DashboardQueries.sql` 1:1, built with SQLAlchemy Core (`select`/`case`/`func.sum`) to
    match this project's standing no-raw-SQL-in-repositories convention rather than the source
    file's literal wording. Every `SUM()` aggregate coalesced with `or 0` in Python (the Phase 2
    `NULL`-not-`0` gotcha, application-layer form).
  - **A real bug caught immediately by the Phase-5-established sanity-query-before-writing-routes
    habit**: `Property.IsActive.is_(True)` compiles to `WHERE [IsActive] IS 1`, a hard T-SQL
    syntax error on SQL Server (`Msg 102`) - MSSQL's `IS` only accepts `NULL`/`NOT NULL`. Fixed to
    `Property.IsActive == True  # noqa: E712`, the same pattern `property_repository.py` already
    used - see `docs/AI_MEMORY.md`'s 2026-08-24 entry for the full story and why it's worth
    remembering explicitly for any future `Boolean` column filter on this project.
  - The cleaning-grade query is this project's first ORM-mapped `ROW_NUMBER() OVER (PARTITION BY
    ...)` window function (`func.row_number().over(...)` inside a `.subquery()`).
  - Recent-activity queries deliberately join `Property`/`User` for `PropertyName`/`InspectorName`
    (via `.concat()`, the portable per-dialect-correct string-concat method, not Python `+`) -
    the one place in the API that departs from every other Response schema's "bare ID, frontend
    resolves the name" convention, since a dashboard feed needs to be human-readable without N+1
    follow-up calls (scope §23).
  - `app/schemas/dashboard.py` - field names match `15_DashboardQueries.sql`'s own column aliases
    (`DueToday`, `OpenCount`, `GradeAOrB`, etc.), same PascalCase-matches-source convention as
    every other Response schema, but without `ConfigDict(from_attributes=True)` since a dashboard
    metric isn't a row from any single ORM entity.
  - `GET /api/dashboard` - one endpoint, any authenticated company member.
  - 5 new tests (124 total): auth required, a Maintenance-role user (the most restricted role
    elsewhere in this project) can view it, a real Urgent maintenance issue moves
    `OpenCount`/`UrgentOrEmergency` by exactly +1 and shows up in `RecentActivity`, a real
    Likelihood=5/Severity=5 risk assessment computes `Critical` and moves
    `CriticalCount`/`OutstandingCount` by +1, and cross-company isolation confirmed end-to-end
    through the real aggregate queries (a Bright Spaces admin never sees a Northgate-created
    issue in `RecentActivity`).
  - **Verified live**: a real Administrator login → `GET /api/dashboard` over actual HTTP
    returned the correct shape and real seeded-data counts (`TotalActiveProperties=3`,
    `PropertiesRequiringAttention=1`) → confirmed a real 401 with no token → server stopped
    cleanly.
- **Phase 16 (React Frontend) — scaffold + auth done, NOT the full phase.** Prompt 16 names ~19
  pages; only the auth flow and a real Dashboard page exist so far. Everything else (Properties,
  Inspections, Maintenance, Risk, Cleaning, Vacant Units, Meter Readings, Admin Settings, and
  Prompt 17's mobile inspection screen) is still to come, built module-by-module against the
  already-complete, already-tested backend - same incremental order the backend itself followed.
  - `frontend/` scaffolded with Vite + React 18 + React Router + Axios, mirroring
    PropertyManager's own frontend architecture (`C:\Users\shmil\Projects\
    property-management-system\frontend`) file-for-file where InspectIQ's schema allows -
    `api/client.js` (Axios instance, memory-only access token, sessionStorage refresh token,
    silent-refresh-and-retry on 401), `contexts/AuthContext.jsx` (session restore on reload via
    the stored refresh token), `routes/ProtectedRoute.jsx` (auth-gated, optionally
    role-gated), `services/` (one file per resource, no component calls Axios directly),
    `layouts/` (MainLayout/Header/Sidebar), `pages/`, `constants/roles.js` (mirrors
    `app/security/roles.py` exactly), `utilities/` (apiError.js, permissions.js).
  - **Two real, deliberate departures from the PropertyManager pattern being mirrored, not
    oversights**: (1) `authService.js` sends lowercase `email`/`password` to
    `/auth/login` (`app/schemas/auth.py`'s `LoginRequest`), not PropertyManager's PascalCase
    `Email`/`Password` - InspectIQ's auth schema is the one deliberately-lowercase exception
    among otherwise-PascalCase request bodies, confirmed by reading the schema, not assumed.
    (2) There is no `logout()` API call - `app/api/auth.py` has no `POST /api/auth/logout`
    endpoint at all (only login/refresh/me exist, unlike PropertyManager's backend), so
    `AuthContext.logout` is purely client-side (clears tokens), documented in
    `authService.js`'s own comment for why.
  - `pages/DashboardPage.jsx` consumes the real `GET /api/dashboard` end-to-end (not a stub) -
    doubles as the actual proof scaffold + auth works against the real backend, matching the
    "verify against a real running server" discipline every backend phase held itself to.
  - **CSP built into `index.html` from this first commit** (`PROJECT_PLAN.md §7`'s explicit
    PropertyManager lesson: that project deferred CSP and paid for it twice). A real, reproduced
    dev-only problem was found and fixed here, not assumed away: Vite's dev server injects live
    CSS as an inline `<style>` tag for HMR (not a real external stylesheet the way `vite build`
    emits) - a strict `style-src 'self'` blocked it outright, confirmed by both a genuine
    "Applying inline style violates ... style-src" console error AND `getComputedStyle` showing
    every button/card stuck on default unstyled browser chrome. Fixed with a mode-scoped CSP
    variable (`frontend/.env.development` sets `style-src 'self' 'unsafe-inline'`,
    `.env.production` keeps it strict at `'self'` - confirmed correct by actually running
    `npm run build` and inspecting `dist/index.html`, which has a real
    `<link rel="stylesheet">`, no inline tag). A second, NOT-fixable dev-mode-only gap was found
    and documented rather than silently left unnoticed: Vite also prepends its own inline
    React-Refresh-preamble `<script type="module">` at the very top of `<head>`, ahead of this
    file's own CSP `<meta>` tag regardless of source order (confirmed by fetching the page's own
    served HTML) - a `<meta>` CSP cannot govern content parsed before its own position, and this
    is Vite's own trusted dev tooling that doesn't exist in a production build at all (confirmed
    by inspecting `dist/index.html`), so it's accepted as a known dev-only limitation, not
    something worth working around. Full story in `docs/AI_MEMORY.md`'s 2026-08-24 entry.
  - **A real, unrelated CVE fixed before it became technical debt across 19 future pages**:
    `npm audit` flagged `react-router-dom` 6.x for a moderate-severity open-redirect
    advisory (CVE-2025-68470 bypass). Bumped to `^7.18.2` (`npm audit` now shows 0
    vulnerabilities) - the classic component-based routing API this scaffold uses
    (`BrowserRouter`/`Routes`/`Route`/`Outlet`/`NavLink`/`useNavigate`) is unchanged between v6
    and v7, confirmed by the full login → dashboard → logout → 404 flow working identically
    after the bump, not assumed compatible from the changelog alone.
  - Mobile-first CSS (`src/styles/global.css`) with a single responsive `MainLayout` (off-canvas
    `Sidebar` below 768px, toggled by a hamburger `Header` button; always-visible sticky sidebar
    above it) - deliberately ONE shell for now, not `PROJECT_PLAN.md §6`'s eventual separate
    desktop/mobile layout components, since only Dashboard exists so far and there's nothing yet
    to differentiate a "field" vs. "management" navigation pattern; `Sidebar`/`Header` are
    already their own components specifically so that split is a later two-file change, not a
    rewrite, when it's actually needed.
  - **Verified live, through the real running UI** (backend `uvicorn` + frontend `npm run dev`,
    not just unit-level): real login as a Northgate Administrator → real dashboard data rendered
    matching the exact backend response (`DueThisWeek=1`, `Overdue=1`, `TotalActiveProperties=3`,
    `PropertiesRequiringAttention=1`) → full page reload preserved the session via a real
    `POST /api/auth/refresh` call (no re-login) → logout → real redirect to `/login` → direct
    navigation to `/` while logged out redirected to `/login` → an unknown URL rendered the 404
    page → a second login as an Inspector (a role Dashboard doesn't restrict) also succeeded →
    both servers stopped cleanly afterward.
  - `.claude/launch.json`-equivalent: no per-repo file (the preview tooling reads the *primary
    working directory's* `.claude/launch.json`, not one inside the InspectIQ repo itself - an
    `inspectiq-frontend` entry was added there instead, alongside PropertyManager's pre-existing
    `frontend` entry).
- **Phase 16 continued — Properties + Units frontend module**, the first full List/Detail/Form
  module (Dashboard has no such shape - a dashboard has no create/edit). Ported PropertyManager's
  shared component library (`PageHeader`/`DataTable`/`Pagination`/`SearchInput`/`FilterPanel`/
  `SelectField`/`FormField`/`FieldShell`/`DateField`/`ErrorMessage`/`EmptyState`/
  `ConfirmationDialog`/`Toast`/`StatusBadge`) into `frontend/src/components/`, file-for-file
  where InspectIQ's own schema allows - these are now the reusable base every future module's
  frontend builds on, not re-ported per module.
  - `frontend/src/constants/propertyOptions.js`/`unitOptions.js` mirror
    `app/schemas/enums.py`'s `PropertyType`/`PropertyStatus`/`InspectionFrequency`/
    `OccupancyStatus` value strings exactly (sent straight through to Pydantic, which 422s on
    anything else). `constants/roles.js` gained `CAN_MANAGE_PROPERTIES` - no
    `CAN_VIEW_PROPERTIES`, same "every role needs it" reasoning as Dashboard, confirmed against
    `app/api/properties.py`'s own module docstring (view = any company member, mutate =
    Administrator/Manager only, both Properties and Units - one constant covers both).
  - `services/propertyService.js`, `unitService.js` wrap `/api/properties` and
    `/api/properties/{id}/units` + `/api/units/{id}` respectively.
  - `pages/properties/PropertiesListPage.jsx`, `PropertyDetailPage.jsx`, `PropertyFormPage.jsx` -
    the List/Detail/Form triad. **Units have no list/detail/form pages of their own** - scope's
    own named page list ("Properties, Property Details," `prompts/frontend_prompt.md`) has no
    separate Units module, and the backend's own routes are nested under a property
    (`/api/properties/{id}/units`), not standalone - so unit management (add/edit/change
    occupancy) lives entirely inside `PropertyDetailPage` as an embedded section, matching the
    backend's own nesting rather than inventing a flat module the scope/API don't have.
  - `PropertyFormPage`'s `AlarmAccessCode` field uses `type="password"` with a show/hide toggle,
    and `PropertyDetailPage` masks it behind a "Show" button by default - the backend still
    stores it as plaintext (`docs/DATABASE.md §10.4`, a real, documented, not-yet-mitigated
    risk this doesn't fix), but there was no reason for the frontend to also leave it sitting in
    plain view on screen once it became the first UI to actually touch that field.
  - **Verified live, through the real running UI** as a real Administrator: created a property
    with the full 17-field form → added a unit → changed its occupancy status (persisted,
    re-confirmed via the real API response, not just local state) → inline-edited the unit's
    tenant name (persisted) → edited the property itself, including its status → deactivated it
    (confirmation dialog → real `POST /deactivate` → correctly hidden from the default list,
    correctly shown with "Include deactivated") → confirmed a Bright Spaces Administrator gets a
    real "Property not found." on the same URL (cross-company isolation, exercised through the
    UI, not just the API directly) → confirmed no page-level horizontal overflow at a 375px
    mobile viewport (the units/properties table scrolls within its own wrapper instead) → all
    test data cleaned up from the real DB afterward (including the property's 3 auto-seeded
    `CleaningAreas` from Phase 11 - the first hard-delete cleanup this session hit that FK, since
    Properties has no soft-delete-only trigger the way `InspectionTemplates`/Sections/Questions
    do) → both servers stopped cleanly.
- **Phase 16 continued — Inspection Templates frontend module.** Read-only end to end, matching
  the backend's own scope (`app/api/inspection_templates.py`'s module docstring: template
  authoring is "eventually," not this phase) - no create/edit/delete anywhere, no
  `CAN_MANAGE_INSPECTION_TEMPLATES` constant, and neither route nested under a role-narrowing
  `ProtectedRoute` at all.
  - `services/inspectionTemplateService.js` wraps `/api/inspection-templates` - a plain list,
    not `PaginatedResponse`, since the backend itself returns one (small realistic count per
    company).
  - `pages/inspection-templates/InspectionTemplatesListPage.jsx` - name/description/version/
    scope (global default vs. company-specific, from `CompanyId === null`)/status, with an
    "include inactive" checkbox (no search/filter beyond that - unlike Properties' larger
    portfolio, this list is small).
  - `pages/inspection-templates/InspectionTemplateDetailPage.jsx` - the full nested
    Sections→Questions tree in one request, rendered as native `<details>`/`<summary>` per
    section rather than custom collapse state - the default template alone is 21 sections/102
    questions, so something has to collapse, and `<details>` gets that free, accessibly, with no
    extra JS. Each question shows its `AnswerType` (YesNo/PassFail/Condition/Text/Number/Date/
    MeterReading - `database/constraints/09_Constraints.sql`'s own CHECK list) and its boolean
    flags (Mandatory/Notes/Photo/Photo required/Can raise maintenance/Can raise risk) as small
    pills - the same "good enough at a glance" spirit as `StatusBadge`, not a form (nothing here
    is editable).
  - **Verified live, through the real running UI**: real Administrator login → the seeded
    "Monthly Property Inspection" template listed correctly as "Global default"/"Active" →
    detail page showed the correct totals (21 sections, 102 questions) → expanded the
    "Electricity Meter" section and confirmed all 3 real questions rendered with correct answer
    types (`METERREADING`/`YESNO`/`CONDITION`) and flags, matching the actual seeded data exactly
    → confirmed every `/api/inspection-templates*` network call returned a real 200 → confirmed
    no page-level horizontal overflow at 375px mobile width.
- **Backend addition: `PATCH /api/inspections/{id}`**, made during Phase 16 planning for the
  Inspection Review screen, not Phase 8 - `GeneralNotes`/`OverallCondition`/`OverallRiskRating`
  have existed on `Inspection`/`InspectionDetailResponse` since Phase 8, but nothing could ever
  set them until Review needed to. Small, well-scoped: same auth (assigned inspector or
  Administrator/Manager) and post-submission immutability rules as `update_response`.
  - `app/schemas/enums.py` gained `OverallCondition` (Excellent/Good/Satisfactory/
    NeedsAttention/Poor/Critical - mirrors the real `CK_Inspections_OverallCondition` CHECK
    constraint that already existed in the DB since Phase 2, unused until now).
    `OverallRiskRating` is deliberately plain `str`, not an enum - unlike `OverallCondition`, the
    DB itself leaves it unconstrained, matching how `RiskAssessments`' own risk-level names come
    from each company's configurable `RiskMatrixLevels` (Phase 13), not a fixed list.
  - `app/schemas/inspection.py`'s new `InspectionUpdate`, `app/services/inspection_service.py`'s
    new `update_inspection`, `app/api/inspections.py`'s new route - all following the exact
    shape `update_response` already established.
  - 4 new tests (128 total): sets and persists all three fields (re-fetched, not just echoed
    back), an invalid `OverallCondition` value 422s, a different Inspector than the one assigned
    gets 403, and the same 409-after-submission rule `update_response` already enforces.
  - **Verified live**: a real Inspector's login → started a real inspection → `PATCH`'d all
    three fields over actual HTTP → confirmed they came back correctly → confirmed an invalid
    enum value still 422s → test inspection cleaned up.

- **Phase 16 continued — Inspection engine wizard, Sub-phase A (core wizard) complete.** The
  five plain answer types, autosave, and status badges - see `docs/AI_MEMORY.md`'s 2026-08-25
  entry for the full design discussion (the "gateway sections" discovery, the sub-phase
  breakdown, and why). Sub-phases B-F (photos, maintenance/risk quick-create, meter reading,
  gateway actions, review/submit) are NOT built yet - see Next tasks.
  - `services/inspectionService.js` wraps `/api/inspections` including the new
    `updateInspectionSummary` (the `PATCH /api/inspections/{id}` just added).
  - `constants/roles.js` gained `CAN_CONDUCT_INSPECTIONS` (Administrator/Manager/Inspector,
    mirroring `_conduct_inspections` in `app/api/inspections.py`) - but a route-level role check
    alone can't express the backend's per-record `ensure_can_edit` (only the assigned inspector,
    or Admin/Manager, may edit ONE SPECIFIC inspection), so that's computed at runtime instead
    (see `InspectionWizardLayout.jsx`), the same "role list isn't enough" pattern the constant's
    own comment documents.
  - `pages/inspections/InspectionsListPage.jsx` - the familiar list pattern (property/status
    filters, `DataTable`), with property names resolved via a one-off `listProperties` fetch
    (`InspectionSummaryResponse` only carries `PropertyId`, same as every other module).
  - `pages/inspections/StartInspectionPage.jsx` - property + template + date form;
    `?propertyId=` in the URL pre-selects the property, since `PropertyDetailPage` now has its
    own "Start Inspection" button linking here that way.
  - `pages/inspections/InspectionWizardLayout.jsx` - a layout route (same shape as `MainLayout`
    one level up) wrapping the Sections and Question screens, fetching the inspection (and its
    property, for the header) ONCE and sharing it via React Router's `useOutletContext()` -
    `applyResponseUpdate`/`applyInspectionUpdate` splice a PATCH's response back into local
    state instead of re-fetching the whole inspection after every answer, keeping question-to-
    question navigation instant. Also computes `canEdit` here, once, for the reason above.
  - `pages/inspections/InspectionSectionsPage.jsx` - property header + progress bar + tappable
    section list, each showing its own `answered/total` count.
  - `pages/inspections/InspectionQuestionPage.jsx` - one question at a time, Previous/Next
    computed from a flattened cross-section position list (so the boundary between sections is
    seamless, not a dead end), an `AnswerControl` sub-component switching on
    `AnswerTypeSnapshot`. Photo/Video/Create Maintenance/Create Risk buttons scope names for
    every question are deliberately NOT here - showing non-functional buttons would be worse
    than omitting them (sub-phases B/C).
  - `utilities/inspectionAnswers.js` - `isAnswered` (mirrors the backend's own `_is_answered`
    exactly, so the frontend's displayed completion never disagrees with
    `CompletionPercentage`) and `isFailed` (only `PassFail`+`"Fail"` - see the design-discussion
    memory entry for why `Condition`'s freeform values deliberately don't drive this).
  - **A real bug found and fixed during live verification, not left in**: the "Failed" badge
    initially showed even when a question was ALSO marked Not Applicable (the backend allows
    both flags true at once - marking N/A doesn't clear a prior `AnswerText`). Fixed so N/A
    takes display precedence - a stale Failed badge on a question the inspector has since
    marked N/A would be actively misleading, not just untidy.
  - **A real robustness gap found and fixed during live verification**: the original design
    saved Text/Number/Notes fields on blur only. Verifying this live surfaced that blur is not
    reliably triggerable/observable even in the *testing* tooling used for this session - which
    prompted checking whether it's reliable for real MOBILE use either, and it isn't (backgrounding
    an app or the OS dismissing a keyboard doesn't always fire blur). Added
    `utilities/useDebouncedCallback.js` - these three fields now save 700ms after the last
    keystroke (the primary path) with an immediate flush on blur as a fallback, not the only
    trigger. Confirmed working live: typing into Notes with no blur at all produced a real
    `PATCH` roughly 700ms after typing stopped.
  - **Verified live, through the real running UI**, covering every plain answer type: started a
    real inspection → answered a `YesNo` question (button tap, instant save, badge flipped to
    Answered) → a `PassFail` question answered "Fail" showed the Failed badge; the same
    question then marked Not Applicable correctly hid it → a `Condition` question answered
    "Poor" showed Answered with NO Failed badge (confirming the deliberate non-heuristic) → a
    `Date` question saved on change → `Notes` saved via the new debounced path with no blur
    triggered at all → a `MeterReading` question showed the honest placeholder while N/A/Notes
    stayed usable → Previous/Next correctly crossed a section boundary in both directions → the
    Sections screen's per-section counts and overall `3.9% complete (4/102)` matched the real
    answers given, exactly agreeing with the backend's own `CompletionPercentage` → a Viewer
    (not in `CAN_CONDUCT_INSPECTIONS`) could see the inspection with every control correctly
    disabled and a "view only" notice shown, and got blocked from `/inspections/new` entirely →
    a Bright Spaces Administrator got a real "Inspection not found." on the same inspection ID
    (cross-company isolation) → confirmed no page-level horizontal overflow at 375px mobile
    width → all test data cleaned up from the real DB afterward.

- **Phase 16 continued — Inspection engine wizard, Sub-phase B (Photo/Video per question)
  complete.** The frontend's first file-upload UI - see `docs/AI_MEMORY.md`'s 2026-08-25 entry
  for the full story.
  - `services/mediaService.js` wraps `/api/media` (list/upload/download-as-blob/delete).
  - `components/MediaAttachments.jsx` - a generic `entityType`/`entityId`/`editable` component,
    deliberately not scoped to InspectionResponse, since Sub-phases C/E's Maintenance/Risk/
    Cleaning quick-creates will need the identical upload/view/delete UI against a different
    entity. Wired into `InspectionQuestionPage.jsx` below Notes, reusing the page's existing
    `editable` variable - no new authorization concept, since `media_service.py` already gates
    InspectionResponse uploads through `inspection_service.ensure_can_edit` (Phase 9).
  - **Deliberate scope call, not a gap**: no AllowsPhoto/RequiresPhoto gating -
    `InspectionResponseSchema` doesn't carry those question-level flags in its frozen snapshot,
    and `inspection_service.py`'s submit gating never checks them either (confirmed by grepping
    the service file first). "Attach evidence" is available on every question uniformly.
  - **A real, reproduced CSP bug, caught only by live verification**: `GET /api/media/{id}/
    download` needs the same Bearer token as every request, so thumbnails are fetched as
    authenticated blobs and rendered via `URL.createObjectURL`, not a plain `<img src>`. The
    original CSP (`img-src 'self' data:`, no `media-src`) didn't allow `blob:` at all - every
    thumbnail failed silently (no visible error, just `img.naturalWidth: 0`) until the console
    showed a real CSP violation. Fixed in `frontend/index.html`: `blob:` added to `img-src`, a
    new `media-src 'self' blob:' added for `<video>`. `connect-src` deliberately NOT touched -
    loading an `<img>`/`<video>` element isn't a fetch/XHR call that directive gates.
  - **Verified live**: uploaded two real photos (confirmed both decode correctly post-fix,
    `naturalWidth` no longer `0`) → deleted one via the confirmation dialog (real `204`) → a
    full hard page reload correctly restored the session and the remaining photo → uploading
    against a since-deleted response correctly showed "Inspection response not found." inline,
    no crash → no horizontal overflow at 375px → all test data (inspection, 102 responses, both
    media rows/files) cleaned up afterward.

- **Phase 16 continued — Inspection engine wizard, Sub-phase C (Create Maintenance Issue /
  Create Risk quick-create) complete.**
  - `services/maintenanceService.js` (`createMaintenanceIssue`) and `services/riskService.js`
    (`createRiskAssessment`) - each wraps only the one endpoint Sub-phase C needs; the full
    Maintenance/Risk Register modules (list/detail/assign/status/timeline) are still unbuilt
    Phase 16 pages.
  - `components/Modal.jsx` - a small shared backdrop/Escape shell (reusing ConfirmationDialog's
    `.dialog-backdrop`/`.dialog` CSS) so the two new quick-create forms don't duplicate it.
    `components/CreateMaintenanceIssueModal.jsx`/`CreateRiskAssessmentModal.jsx` - genuinely
    minimal fields (Title/Category/Priority/Description; Hazard/Likelihood/Severity/Notes) -
    only `InspectionResponseId` is sent as linkage, since both backend services derive Property/
    Inspection/Location themselves and would ignore a client-supplied PropertyId anyway.
    `constants/maintenanceOptions.js` mirrors `MaintenanceCategory`/`MaintenancePriority`;
    `constants/riskOptions.js` uses scope §19's own exact Likelihood/Severity scale text (Rare/
    Unlikely/.../Insignificant/Minor/...), not an invented one.
  - **A real authorization distinction, caught by reading the service code first, not assumed
    from the Sub-phase B precedent**: these buttons are gated on a NEW `canRaiseIssues` (any
    `CAN_CONDUCT_INSPECTIONS` role), computed once in `InspectionWizardLayout.jsx` alongside
    `canEdit` - deliberately NOT `editable`. `maintenance_service.create_issue`/
    `risk_service.create_risk_assessment` resolve the inspection via `inspection_service.
    get_inspection` (a VIEW-level lookup), never `ensure_can_edit` - so any Administrator/
    Manager/Inspector at the company can raise an issue or risk against any response, not just
    the inspector assigned to that specific inspection. Confirmed by grepping both service
    functions before wiring the frontend gate.
  - **Verified live**: created a real Maintenance Issue (Title pre-filled from the question
    text, Category required via native HTML5 validation blocking an empty selection before the
    form's own JS validation even runs) - confirmed server-side via direct DB query that
    PropertyId/InspectionId were correctly derived and Location auto-filled from the response
    snapshot exactly as `maintenance_service.py` documents. Created a real Risk Assessment
    (Likelihood=4/Severity=5, scope's own worked example) - confirmed `RiskScore=20`/
    `RiskLevel=Critical` both in the toast and via direct DB query. Confirmed a Viewer (not in
    `CAN_CONDUCT_INSPECTIONS`) sees neither button, matching the Photo/Video gating precedent
    for that role even though the underlying authorization rule is different. All test data
    (inspection, 102 responses, the issue, the risk assessment) cleaned up afterward.

- **Phase 16 continued — Inspection engine wizard, Sub-phase D (MeterReading answer type: photo
  → mock OCR → confirm/correct) complete.** Wired to `/api/meter-readings`, not the generic
  `PATCH .../responses/{id}` endpoint every other answer type uses - a meter reading is its own
  record (`AIDetectedReading`/`ConfirmedReading`/`PhotoMediaFileId`), not free text on the
  response.
  - **A small, deliberate backend addition, not scope creep**: `GET /api/meter-readings` gained
    an `inspection_response_id` filter (`app/api/meter_readings.py`, `meter_reading_service.py`,
    `meter_reading_repository.py`) - the Question screen needs to know whether a reading already
    exists for THIS response, and `InspectionResponseSchema` carries no pointer back to a
    `MeterReadingId` (the ERD only points the other way). One new backend test
    (`test_list_filtered_by_inspection_response_id`, 130 total), full suite re-run clean.
  - `services/meterReadingService.js` (list/create/update) and `components/
    MeterReadingControl.jsx` - the actual state machine: no reading yet → capture form (meter
    type, defaulted from the question's own section name via a small heuristic - "Electricity
    Meter" section guesses `Electricity` - plus optional serial number, then a photo); reading
    exists, unconfirmed → shows the photo + AI value, with a Confirm form pre-filled from
    `AIDetectedReading`; confirmed → shows the confirmed value with a "Correct this reading"
    reopen. The photo is always visible regardless of role (view has no restriction, same as
    every other module) - only the CREATE and CONFIRM actions are gated.
  - **A third distinct authorization shape inside one control, confirmed by reading
    `meter_reading_service.py` before wiring either half** (same lesson as Sub-phase C's two
    modals): CREATE uses `canRaiseIssues` (`create_meter_reading` has no `ensure_can_edit`-style
    check at all - any Administrator/Manager/Inspector can take the photo); CONFIRM uses
    `editable` (`update_meter_reading` calls `ensure_can_edit_reading`, which for an
    Inspection-linked reading IS exactly the assigned-inspector-or-Admin/Manager rule). Two
    different gates on the same record, correctly split at the exact line each backend action
    actually checks.
  - **Closes a real, previously-open gap**: confirming a reading now also calls the existing
    generic `PATCH .../responses/{id}` with `AnswerNumber` (the backend auto-derives
    `AnswerText = str(AnswerNumber)`, same as the Number answer type - no new backend code
    needed) - before this, a MeterReading question could never count towards
    `CompletionPercentage` at all, since `_is_answered` only checks `AnswerText`. Deliberately
    wired at CONFIRM time only, not at photo-upload time - an unconfirmed AI value isn't "the
    answer" yet, mirroring Phase 14's "the AI value must never silently become the confirmed
    one."
  - **Verified live**: started a real inspection, navigated to the seeded "Electricity Meter"
    section - the meter-type guess correctly pre-selected `Electricity`. Uploaded a real photo →
    got back the mock OCR's own example value (`AIDetectedReading=18294.6000`,
    `AIConfidence=0.87`, matching scope §11 exactly) → badge stayed "Unanswered" (correct, not
    yet confirmed) → confirmed a corrected value (`18300.5`) → badge flipped to "Answered" → the
    Sections screen's completion count moved to `1/102` (and `Electricity Meter 1/3`) → confirmed
    via direct DB query that `InspectionResponses.AnswerText`/`AnswerNumber` were both correctly
    synced. Confirmed a Viewer sees the photo and both values but neither the create button nor
    "Correct this reading". No mobile overflow at 375px. All test data (inspection, 102
    responses, the meter reading, its media row and file) cleaned up afterward.

- **Phase 16 continued — Inspection engine wizard, Sub-phase E (the two global "gateway"
  quick-actions: Add Empty Unit / Grade Cleaning Area) complete.** No backend changes needed -
  both endpoints already existed. Placed on `InspectionSectionsPage.jsx`, not any one question
  screen - the seeded template's "Vacant Units"/"Communal Cleaning" sections only ask the
  inspector to CONFIRM these were recorded elsewhere.
  - `services/cleaningService.js` (listAreas/createCleaningInspection), `services/
    vacantUnitService.js` (createVacantUnitInspection - `listUnits` already existed in
    `unitService.js`), `constants/cleaningOptions.js` (`CLEANING_GRADE_OPTIONS` using scope
    §16's own descriptive wording, e.g. "D - Poor (significant cleaning required)").
  - `components/AddEmptyUnitModal.jsx` - genuinely all of scope §7's fields, not a trimmed-down
    "minimal" set like Sub-phase C's modals: Unit, Date identified vacant, Condition, and all 11
    Yes/No/Not-checked tri-state checks (Electricity on?/Water on?/.../Maintenance required?),
    plus Notes. A small local `TriStateRow` sub-component renders each check as three buttons
    (reusing the `.answer-button`/`.answer-buttons` CSS the plain-question YesNo/PassFail
    controls already use, for visual consistency, not new styling). Photos/Videos and "creatable
    maintenance issue from any of these questions" are real scope items, deliberately NOT here -
    documented in the component's own header comment as a follow-on refinement, the same
    explicit-deferral practice Sub-phase A used for its own buttons.
  - `components/GradeCleaningAreaModal.jsx` - Area/Grade/Cleaning required/Urgent/Notes;
    Assigned cleaner/Due date/Status deliberately deferred (Status has no field at all - it
    starts "Pending" automatically since no `AssignedUserId` is supplied).
  - **Both gateway create actions are gated on `editable`, NOT `canRaiseIssues`** - confirmed by
    reading `vacant_unit_service.create_vacant_unit_inspection` and `cleaning_service.
    create_cleaning_inspection` before wiring either button: both call
    `inspection_service.ensure_can_edit`, unlike Sub-phase C/D's create actions. The two gateway
    actions happened to land on the same tier as each other, but each was verified
    independently, not assumed from the other.
  - **A real, foreseeable CSS bug found before it could surface live, then confirmed with an
    actual measurement**: `.dialog` (shared by every modal since ConfirmationDialog) had no
    `max-height`/`overflow-y` - fine for short content, but `AddEmptyUnitModal`'s ~15 fields
    would overflow the viewport with no way to scroll, especially on mobile. Added
    `max-height: 90vh; overflow-y: auto` to `.dialog` globally (benefits any future
    longer-content modal too). Confirmed necessary, not speculative: measured at 375px width,
    the dialog's real content was `2267px` tall against a `731px` constrained `clientHeight`,
    `scrollHeight > clientHeight` confirming the scroll actually engages.
  - **Verified live**: started a real inspection on "Elm Court" (the demo property with actual
    seeded `CleaningAreas`, unlike "15 High Road"). Add Empty Unit - real units loaded in the
    select, toggled two tri-state checks to real (non-null) values, saved - confirmed via direct
    DB query that `ElectricityOn`/`SignsOfDamp` stored correctly and `WaterOn` stayed genuinely
    `NULL` (untouched), AND that the unit's `OccupancyStatus` flipped `Occupied` → `Vacant` (the
    Phase 12 side effect, now reachable from the wizard for the first time). Grade Cleaning Area
    - real areas loaded, graded "E" with `CleaningRequired=true` - confirmed via direct DB query
    (a first checkbox-toggle test using the native-property-setter pattern silently didn't take;
    switching to a plain `.click()` on the checkbox element resolved it - a testing-tooling
    quirk, re-verified as NOT an app bug via a second real save). Confirmed a Viewer sees neither
    button on the Sections screen. Confirmed the mobile scroll fix live (see above). All test
    data (inspection, 102 responses, the vacant-unit record, the cleaning record) cleaned up
    afterward, including manually restoring the demo unit's `OccupancyStatus` back to
    `Occupied`.

- **Phase 16 continued — Inspection engine wizard, Sub-phase F (Inspection Review and Submit)
  complete. This closes out the entire Prompt 17 wizard - all six sub-phases (A-F) done.** New
  `pages/inspections/InspectionReviewPage.jsx`, a third page nested under
  `InspectionWizardLayout` (alongside Sections and Question), reached via a new "Review & Submit"
  link on the Sections screen (relabels to "View Review Summary" once `Status === "Submitted"`).
  - Sets `GeneralNotes`/`OverallCondition`/`OverallRiskRating` via the existing
    `PATCH /api/inspections/{id}` (added during Sub-phase A's own planning specifically for
    this) - `OverallCondition` from a fixed enum select (`constants/
    overallConditionOptions.js`), `OverallRiskRating` from a NEW `riskService.getRiskMatrix()`
    call - the company's own configured risk-band `LevelName`s (`GET /api/risk-matrix-levels`),
    not a hardcoded list, matching `app/schemas/inspection.py`'s own documented reasoning for
    leaving that field a plain string. `GeneralNotes` debounce-saves the same way Notes does on
    the Question screen; both selects save instantly on change - same "as few taps as possible"
    instant-save philosophy as the rest of the wizard, no separate "Save" step anywhere on this
    page.
  - **Deliberately does NOT try to compute "which mandatory questions are unanswered" client-
    side** - `InspectionResponseSchema`'s frozen snapshot has no live `IsMandatory` flag (the
    same fact `MediaAttachments.jsx` already established for `AllowsPhoto`/`RequiresPhoto`), so
    reconstructing that logic here would risk silently disagreeing with the backend's own check.
    `submit_inspection` already computes the exact count and a preview of which questions on a
    422 - this page surfaces that message verbatim via `getErrorMessage()` rather than
    duplicating it.
  - `components/SelectField.jsx`/`FormField.jsx`/`FieldShell.jsx` gained a `disabled` prop -
    the FIRST place in the frontend needing a disabled select (Sections/Question screens
    disable native `<button>`/`<input>` elements directly, never through these shared
    components) - a real, if minor, gap found and closed rather than working around it with a
    one-off inline `<select>`.
  - After a successful submit, the page stays put and calls `applyInspectionUpdate` +  shows a
    local `Toast` - no navigation - the same "update in place" pattern
    `PropertyDetailPage`'s deactivate flow already uses, simpler than the create-then-redirect-
    with-`location.state` pattern that pattern's OWN toast machinery also supports.
  - **Verified live**: on a fresh 0%-complete inspection, attempting Submit correctly surfaced
    the backend's own precise message ("Cannot submit: 13 mandatory question(s)...", listing
    real question text) - confirmed the exact same wording appears, not a paraphrase. Set
    `OverallCondition=Good`/`OverallRiskRating=Low` (the real seeded matrix's own `LevelName`) -
    each PATCHed instantly, confirmed via a page reload that both persisted. Typed
    `GeneralNotes`, confirmed the debounced PATCH fired via `onBlur`. Answered every response
    directly via the API (`IsNotApplicable: true` on all 102 - type-agnostic, works regardless
    of `AnswerTypeSnapshot`) to reach 100% without needing to click through 102 questions for a
    verification pass, then submitted successfully through the real UI - `Status` flipped to
    `Submitted`, `SubmittedAt`/`CompletedAt` set, confirmed via a direct DB query that all three
    summary fields persisted exactly as entered. Confirmed every field/control on the Review
    page (and every answer control on a real Question page) became disabled once `Submitted`.
    Confirmed a direct `POST .../submit` against the ALREADY-submitted inspection correctly
    409s (double-submit protection, Phase 8's own rule, exercised here for real through this
    page for the first time). Confirmed a Viewer sees the same confirmed values read-only, no
    Submit button. No console errors beyond the deliberately-triggered 422 from the mandatory-
    validation test itself. No horizontal overflow at 375px. All test data (the inspection and
    its 102 responses) cleaned up from the real DB afterward.

- **Phase 16 continued — the standalone Maintenance module (list/detail/assign/status/notes/
  photos) complete.** The first of Phase 16's remaining standalone modules - closes the real gap
  flagged when the wizard finished: records the wizard's quick-create (Sub-phase C) fed in had
  nowhere to be browsed or managed afterward.
  - **A small, justified backend addition, found necessary while designing the frontend**:
    `GET /api/users` (`app/api/users.py`, new) - nothing in the backend could enumerate a
    company's users before this, and the Assign control needs a picker. View-only, no role
    restriction (matching every other view endpoint), company-isolated via a new
    `user_repository.list_users_for_company` (the repository file's own docstring had already
    flagged that a future "list users in a company" case would need `CompanyId` scoping, unlike
    its two existing lookups - this is that case). 3 new tests (132 total backend tests), full
    suite re-run clean.
  - `pages/maintenance/MaintenanceIssuesListPage.jsx` (filter by status/category/priority/
    property/assigned-to, mirroring `InspectionsListPage.jsx`'s one-off-fetch pattern for
    resolving Property names, extended here to also resolve Assigned-to names via the new
    `listUsers()`), `MaintenanceIssueDetailPage.jsx` (the real center of the module), and
    `MaintenanceIssueFormPage.jsx` (edit-only, no create mode - see below for why).
  - **Three authorization tiers rendered as three separately-gated sections, matching
    `maintenance_service.py`'s own module docstring exactly** rather than one blanket flag:
    `canManage` (Administrator/Manager, new `CAN_MANAGE_MAINTENANCE` constant) gates the Edit
    link and the Assign control; `canWork` (the issue's own `AssignedUserId`, OR `canManage` -
    computed per-record on the Detail page, mirroring `InspectionWizardLayout`'s `canEdit`)
    gates status changes, notes, and photo uploads; plain view (everything else) has no gating
    at all. The "New status" select excludes the issue's current status client-side, avoiding a
    guaranteed 422 the backend would otherwise correctly reject.
  - **`MediaAttachments.jsx` gained an optional `onUpload` override** - the first real consumer
    besides the generic path. `maintenance_service.upload_photo` writes a `PhotoUploaded`
    timeline entry the generic `/api/media` upload knows nothing about, so
    `MaintenanceIssueDetailPage` passes `onUpload={(file) => uploadMaintenancePhoto(...)}` to
    route CREATE through the timeline-aware endpoint while list/download/delete still use the
    generic one (no timeline entry needed for those). Every other `MediaAttachments` caller
    omits the prop and is unaffected.
  - **A real bug found and fixed during live verification, not shipped**: the Timeline section
    only reflected `issue.Updates` from the initial page load - uploading a photo correctly
    wrote a `PhotoUploaded` row server-side (confirmed via a page reload), but the live page
    didn't show it until manually refreshed. Fixed with a `refreshTimeline()` re-fetch chained
    onto the `onUpload` promise - deliberately NOT reusing `loadIssue()` for this, since that
    function flips `loading` and would unmount the whole detail page (`MediaAttachments`
    included) mid-upload; `refreshTimeline()` is a quiet re-fetch with no loading gate.
  - **A second real bug found and fixed**: the Edit form's success toast
    (`navigate(..., { state: { toast: ... } })`) never appeared, because
    `MaintenanceIssueDetailPage` never read `location.state?.toast` at all - copy-pasted the
    `useState(null)` toast pattern without the `location.state` initialization every other page
    using this exact navigate-with-toast convention (`PropertiesListPage`,
    `PropertyDetailPage`) already has. Fixed by adding the same `location.state?.toast` read +
    clear-on-mount effect.
  - **Deliberately no `/maintenance-issues/new` route** - scope §17 frames issue creation
    entirely as the wizard's job ("from any inspection question"), not a standalone flow; this
    module is specifically the other half (browse/manage what the wizard already created), not
    a duplicate creation path.
  - `StatusBadge`'s shared tone map gained Maintenance's Status/Priority values (open/assigned/
    inprogress/waiting/completed/closed, emergency/urgent/high/medium/low) - grown incrementally
    per the component's own stated design, not a one-off override at each call site.
  - **Verified live**: created a real issue via the API, then through the actual UI as
    Administrator - assigned it (Status auto-advanced Open→Assigned exactly per backend logic,
    confirmed in the Timeline), updated status to InProgress with a comment, added a note,
    uploaded two photos (Timeline updated live both times after the fix), edited the Title/Due
    date (toast confirmed after the fix). Confirmed the assigned Maintenance-role worker (not
    Admin/Manager) sees status/notes/photos controls but neither Edit nor Assign. Confirmed a
    Viewer sees a fully read-only page (including the two real photos, view has no role
    restriction). Confirmed cross-company isolation through the real UI (a Bright Spaces admin
    got "Maintenance issue not found."). No horizontal overflow at 375px on either List or
    Detail. All test data (the issue, its timeline, both media rows, and both files on disk)
    cleaned up from the real DB and disk afterward.

- **Phase 16 continued — the standalone Risk Register module (list/detail/create/edit)
  complete.** The second of Phase 16's remaining standalone modules, and noticeably simpler than
  Maintenance's - two static role tiers, no per-record assignee carve-out, no timeline table. No
  backend changes needed this time - unlike Maintenance's `GET /api/users` and Sub-phase D's
  `inspection_response_id` filter, the existing API surface already supported everything this
  module needed.
  - `pages/risk/RiskAssessmentsListPage.jsx`, `RiskAssessmentDetailPage.jsx`, and a genuinely
    dual-mode `RiskAssessmentFormPage.jsx` (`isEdit = id !== undefined`, mirroring
    `PropertyFormPage.jsx`'s shape) - `services/riskService.js`'s `createRiskAssessment` was
    generalized from Sub-phase C's five quick-create fields to the full `RiskAssessmentCreate`
    set (existing callers unaffected, every new param is optional), plus new
    `listRiskAssessments`/`getRiskAssessment`/`updateRiskAssessment`.
  - **A deliberate difference from Maintenance, not an inconsistency**: `/risk-assessments/new`
    IS a real route (`CAN_CONDUCT_INSPECTIONS`-gated, reusing the existing constant - no new one
    needed). Scope §19 doesn't frame risk creation as inspection-only the way §17 explicitly
    does for Maintenance ("from any inspection question"), and the backend's own
    `RiskAssessmentCreate` already supports a standalone, `PropertyId`-only entry - a genuine
    Risk Register use case (a manager logging a hazard noticed outside any inspection), not
    scope creep.
  - **Two tiers, confirmed independently by reading `risk_service.py` before assuming
    Maintenance's shape applied**: `canManage` (Administrator/Manager, new `CAN_MANAGE_RISK`)
    gates the Edit link - the ONE combined PATCH covering every field including Status/
    ResponsiblePersonUserId, with NO per-record carve-out at all (being the
    `ResponsiblePersonUserId` does not grant edit rights, unlike Maintenance's `AssignedUserId`
    tier) - so `/risk-assessments/:id/edit` is a plain role-gated route, no per-record
    computation needed on the page itself, unlike Maintenance's `canWork`.
  - **A third, genuinely different tier for Photos specifically, confirmed by reading
    `media_service.py`**: RiskAssessment's media mutate check is the SAME as its view check (any
    company member) - matching Property/Unit's "uploading evidence is broader than editing the
    record" shape, not Maintenance's `ensure_can_edit`-gated one. `MediaAttachments` gets
    `editable={true}` unconditionally on this page - verified live with a real Viewer login
    successfully uploading a photo to a record they have no other access to modify.
  - `StatusBadge`'s shared tone map gained `critical`/`actionplanned` (RiskLevel/Status values) -
    grown incrementally again, same as Maintenance's addition.
  - **Verified live, across three different users**: created a real risk assessment as an
    Inspector (Likelihood=4/Severity=5 → confirmed `RiskScore=20`/`RiskLevel=Critical`, matching
    scope's own worked example) → that same Inspector successfully uploaded a photo (no Edit
    link shown, correctly gated) → an Administrator edited it (Severity→2, Status→ActionPlanned,
    assigned a Responsible person) → confirmed `RiskLevel` was RE-derived to `Medium` (4×2=8,
    the 5-9 band) and the toast/resolved name both appeared correctly → a cross-company
    Administrator got a real 404 → a Viewer saw a fully read-only detail page EXCEPT the photo
    upload control, which correctly still worked (confirmed with a real successful upload,
    proving the "media mutate = view" rule holds even for the most restricted role). No mobile
    overflow. All test data (the risk assessment and both media rows/files) cleaned up
    afterward.

## Currently being worked on

- Nothing in progress. Committing this batch (the Risk Register module) to git is the next
  action.

## Important decisions

See `docs/AI_MEMORY.md` for the reasoning behind each; summarized in `docs/PROJECT_PLAN.md` and
`docs/DATABASE.md §9`. Real gotchas discovered while writing the actual SQL (not previously
documented, worth knowing for any future script against this schema):

1. **Any statement that creates or writes to a table with a `PERSISTED` computed column
   (`RiskAssessments.RiskScore`) OR a filtered index (`Properties.NextInspectionDue`,
   `Properties.PropertyStatus`, `MaintenanceIssues.DueDate`) needs `SET ANSI_NULLS ON` and
   `SET QUOTED_IDENTIFIER ON` in that session first**, or SQL Server rejects it (`Msg 1934`) —
   this bit `13_SeedSampleData.sql` on a plain `Properties` INSERT, not just `RiskAssessments`.
   SQLAlchemy/pyodbc set these by default, so the application itself won't hit this — but any
   hand-written script will.
2. **Filtered index predicates don't support `NOT IN`** (`Msg 102`) — use
   `x <> a AND x <> b` instead of `x NOT IN (a, b)`.
3. **`SUM(CASE...)` over zero matching rows returns `NULL`, not `0`.** Caught by actually
   running `15_DashboardQueries.sql` against a company with no maintenance/risk/cleaning data
   yet — every dashboard aggregate is wrapped in `ISNULL(..., 0)` as a result. A dashboard card
   must never render `NULL` as if it were an empty state.
4. **`RETURN` inside a `.sql` script only exits the current batch, not the whole script.** An
   idempotency guard (`IF EXISTS (...) BEGIN ... RETURN; END`) must be in the *same batch* as
   the logic it's meant to skip — a `GO` between the guard and the inserts silently defeats it.
   Caught in `12_SeedInspectionTemplate.sql` before it caused a real duplicate-data bug.

## Known bugs

None currently open. One real bug was found and fixed this session (see Phase 5 entry above):
`User.company`'s string-referenced `"Company"` relationship wasn't resolvable at runtime because
nothing imported `Company` outside `TYPE_CHECKING` — fixed via `app/models/__init__.py`. Every
future model added must be imported there too, or the same class of bug will resurface silently
(and `pytest` alone may not catch it, the way it didn't here — always also check with a real
running server when adding a new model). One harmless warning worth knowing about (not a bug):
`pytest` shows a `StarletteDeprecationWarning` about `httpx` vs a future `httpx2` package, from
pairing a very new Starlette (1.6.0) with httpx 0.28.1. Doesn't affect anything now.

## Database structure

Fully implemented — see `docs/DATABASE.md` for the design, `database/` for the SQL, all applied
and verified against a real local `InspectIQDb`. Both structural requirements from the Phase 1
sign-off are live and trigger-enforced. `RiskAssessments.RiskScore` is a verified-working
`PERSISTED` computed column. The default inspection template (21 sections/102 questions) and
global risk matrix are seeded; 2 demo companies with realistic property/unit data exist locally,
now with 6 real, working demo logins (see Phase 5 above) — password `Password123!` for all.

## Coding standards

Established and followed through Phase 8: routes thin, business logic lives in `app/services/`
(reuse other services' already-authorized lookups instead of reimplementing isolation checks —
`inspection_service.start_inspection` calls `property_service.get_property`/
`inspection_template_service.get_template` rather than querying those tables directly),
repositories do DB access only (join through the right parent table when a tenant table has no
`CompanyId` of its own; use `CompanyId IS NULL OR CompanyId = @x` for global-default-plus-override
tables), `app/schemas/` owns response shapes and input validation, `app/core/exceptions.py` owns
error-to-HTTP-status mapping, `app/security/roles.py` centralizes role-name constants. Every new
SQLAlchemy model must be added to `app/models/__init__.py` **and sanity-queried against the real
DB before writing any route that depends on it**. Every new Pydantic enum field needs its enum
type imported under an alias if the field name matches the type name (Python 3.14 lazy-annotation
gotcha). Test cleanup for a soft-delete-only table must disable/delete/re-enable its trigger and
verify `is_disabled = 0` afterward. **Not every module gets the same authorization shape** —
Properties/Units/Templates are "any company member views, Admin/Manager mutates," but
Inspections is narrower ("assigned inspector or Admin/Manager mutates") because an in-progress
inspection is one person's active work, not shared reference data; check what a module actually
represents before copying the previous module's permission pattern wholesale. Python 3.14,
dependencies pinned with `>=` floors in `requirements.txt` — see `backend/README.md`.
**Any file object handed to a `StreamingResponse` (or returned from any storage abstraction)
must be explicitly closed — Starlette does not close it for you**, confirmed by a real Windows
`PermissionError` when Phase 9's first `/download` implementation leaked a handle; see
`app/api/media.py`'s `_iter_and_close`. `media_service.SUPPORTED_ENTITY_TYPES` now covers every
scope §20 entity type (MeterReading, Phase 14, was the last) — `test_media.py`'s "unsupported
EntityType" test had to switch to an obviously-fake string (`"NotARealEntityType"`) since no
real-but-unbuilt table name remains; if scope's own entity list ever grows, the same three-place
checklist applies again (`_VIEW_CHECKS`/`_MUTATE_CHECKS`, `ENTITY_TYPES` tuple, that test).
**A permission check reused from a DIFFERENT action on the same entity can be wrong even when it
looks like the "obvious" reuse** — confirmed by a real, caught-by-a-failing-test bug in Phase 14:
MeterReading's media-upload check first reused `meter_reading_service.ensure_can_edit_reading`
(the CONFIRM/update tier), which 403'd the very Inspector legitimately creating a brand-new
standalone reading, because a freshly-created record has no `AssignedUserId`/Inspection yet to
satisfy that narrower check. The photo is attached as an integral part of CREATE (a broader,
earlier moment, already gated by the route's own role check) - confirming the numeric value is a
separate, later action with its own narrower gate. When one entity has two distinct mutating
actions (create-with-attachment vs. confirm-or-correct), verify which action a media-mutate
check is actually supposed to gate before wiring it to whichever permission function is nearest
at hand - Property/Unit/RiskAssessment's "media mutate = view, not edit" precedent turned out to
be the right template here too, but only after checking, not by default.
**A "global default + per-company override" nullable-CompanyId pattern needs its exact lookup
semantics re-derived per table, not copied verbatim from `InspectionTemplates`** — confirmed by
`RiskMatrixLevels` in Phase 13 needing the OPPOSITE semantics from `InspectionTemplates`: a
template list is additive (global options plus a company's own, shown together), but a risk
matrix must be a coherent whole covering every score with no gaps, so a company's own bands need
to fully REPLACE the global default the instant any exist, not sit alongside a stale leftover
global band. Same nullable-`CompanyId` mechanism, different resolution logic
(`risk_repository.get_risk_matrix_for_company`) - check which behavior a new "global + override"
table actually needs before assuming it matches the first precedent.
**When two services each need to call the other, use a function-local import on (at least) one
side rather than restructuring the module boundary** — confirmed working, not just theoretical,
by `media_service`↔`maintenance_service` in Phase 10 (see either file for the exact pattern and
the comment explaining which side owns the local import and why). **But check each direction
independently before reaching for that workaround** — Phase 11's `property_service`→
`cleaning_service` call needed it (a real cycle, since `cleaning_service` imports
`property_service`), while `media_service`→`cleaning_service` and `media_service`→
`vacant_unit_service` (Phase 12) didn't (no cycle exists on either, since neither service ever
needs `media_service`) — a plain top-level import was correct both times, and using a local one
anyway would just be needless caution copied from Phase 10 without re-checking it actually
applies. **A service function with no permission check of its own (e.g.
`unit_service.update_unit_occupancy`, gated only at its own route's level) can be called
directly from another module's already-authorized service function to give that action a
different, narrower "own permission story"** — confirmed twice now: Phase 11's property-creation
auto-seed and Phase 12's inspector-triggered occupancy flip both do exactly this, each
anticipated years earlier (in comments, not just in hindsight) as the deliberate reason a
standalone API route's role gate doesn't need to be the ONLY way to reach that state change.

## Next tasks

1. Commit this batch (Inspection engine Sub-phase F) to git.
2. **The Inspection engine wizard (Prompt 17) is now fully DONE - all six sub-phases (A-F)
   built and verified live.** Planned in detail with the owner on 2026-08-25 (see
   `docs/AI_MEMORY.md`'s entries of that date for the full design discussion, including the
   "gateway sections" discovery that shaped this, and each sub-phase's own live-verification
   findings). Deliberately staged into sub-phases rather than built as one page, each
   independently committable and verifiable:
   - **Sub-phase A — DONE**, commit `fa3006e` - the core wizard: Inspection List, Start
     Inspection, the Sections screen, and the Question screen for the five plain answer types
     (`YesNo`/`PassFail`/`Condition`/`Text`/`Number`/`Date`), autosave (debounced while typing,
     not blur-only - a real robustness fix found during verification), and status badges
     (Answered/Unanswered/Failed, with Not-Applicable correctly taking display precedence over a
     stale Failed badge - another fix found during verification). See the "What has been
     completed" entry above for the full detail.
   - **Sub-phase B — DONE**, commit `9eb11c6` - Photo/Video per question, via the new generic
     `components/MediaAttachments.jsx` against `EntityType=InspectionResponse`. A real CSP bug
     (blob: URLs blocked for thumbnails) was found and fixed - see the "What has been completed"
     entry above and `docs/AI_MEMORY.md`'s 2026-08-25 entry for the full story.
   - **Sub-phase C — DONE**, commit `779a0b6` - Create Maintenance Issue / Create Risk
     quick-create modals, gated on a NEW `canRaiseIssues` check (deliberately not `editable` - a
     real authorization distinction from Photo/Video, see the "What has been completed" entry
     above). Minimal fields; `InspectionResponseId` supplied so the backend derives Property/
     Location itself, same as every other creation path into those two modules.
   - **Sub-phase D — DONE** (commit pending as of this writing) - the `MeterReading` answer
     type's own flow (photo → mock OCR → confirm/correct, wired to `/api/meter-readings`, not
     the generic response-update endpoint - though confirming DOES also call the generic
     endpoint once, to sync `AnswerNumber` for `CompletionPercentage`). A small, justified
     backend addition (`inspection_response_id` filter on `GET /api/meter-readings`) and a third
     distinct authorization shape (create vs. confirm) were both found by reading the service
     code first - see the "What has been completed" entry above.
   - **Sub-phase E — DONE** (commit pending as of this writing) - the two global "gateway"
     quick-actions confirmed necessary by the seed data's own design comment (`database/seed/
     12_SeedInspectionTemplate.sql`'s file header): "Add Empty Unit" and "Grade Cleaning Area",
     placed on the Sections screen rather than any one question. No backend changes needed - both
     already gated create on `ensure_can_edit`, confirmed by reading each service function
     first. Found and fixed a real CSS gap (`.dialog` had no `max-height`/scroll, which
     `AddEmptyUnitModal`'s ~15-field form would have overflowed) before it could surface as a
     live bug. See the "What has been completed" entry above for the full detail.
   - **Sub-phase F — DONE** (commit pending as of this writing) - Inspection Review
     (`OverallCondition`/`OverallRiskRating`/`GeneralNotes` via the `PATCH /api/inspections/{id}`
     added during Sub-phase A's planning) and Submit. "Inspection Report" (PDF) is explicitly
     OUT of scope for all of this - it depends on backend Phase 17 (`PROJECT_PLAN.md §11`'s
     phase table), which doesn't exist yet. See the "What has been completed" entry above for
     the full detail.

3. **Phase 16 itself is NOT yet done** - its own exit criteria (`PROJECT_PLAN.md §11`: "All
   pages navigable, auth-gated correctly") means every module needs its OWN standalone list/
   detail pages too, the same way Properties got `PropertiesListPage`/`PropertyDetailPage`/
   `PropertyFormPage`.
   - **Maintenance — DONE** (commit pending as of this writing) - list/detail/assign/status/
     notes/photos, plus a small justified `GET /api/users` backend addition for the Assign
     picker. See the "What has been completed" entry above for the full detail, including two
     real bugs found and fixed during live verification (a stale Timeline after photo upload,
     and a missing Edit-success toast).
   - **Risk Register — DONE** (commit pending as of this writing) - list/detail/create/edit,
     including a standalone create form (a deliberate difference from Maintenance - see the
     "What has been completed" entry above for why). No backend changes needed this time. Two
     tiers (`canManage` for Edit, unconditional `editable` for Photos - a genuinely different,
     independently-confirmed rule from Maintenance's).
   - **Remaining, per Prompt 16's own page list**: Cleaning (areas config, grading history),
     Vacant Units (list/detail), Meter Readings (list/detail), Admin Settings, and a Risk Matrix
     configuration screen (create/edit `RiskMatrixLevels` - scope §19's "the exact risk matrix
     should remain configurable," deliberately deferred from this pass as a secondary feature
     relative to the main Risk Register CRUD, not silently dropped). The wizard's quick-create
     modals (Sub-phases D/E) let an inspector CREATE a MeterReading/VacantUnitInspection/
     CleaningInspection from inside an inspection, the same gap Maintenance/Risk had - there's
     still no page anywhere in the app to browse, filter, or manage those records afterward. No
     order has been decided for these yet - an open decision for a future session, not something
     2026-08-25's planning session covered (it only approved the wizard's own six sub-phases).
   - A pattern worth reusing across all of these, confirmed multiple times now (Maintenance's
     `GET /api/users`, Sub-phase D's `inspection_response_id` filter, and Risk Register
     confirming the OPPOSITE - that sometimes the existing API surface already IS enough): read
     the relevant `_service.py` file's authorization logic BEFORE designing each module's
     frontend gating, and check whether the existing API surface actually supports what a
     management page needs (a picker, a filter) before assuming it does either way - don't
     assume a gap exists any more than assuming one doesn't.

## Files that require attention

- `docs/DATABASE.md §10.1` (denormalized `CompanyId` drift risk) and `§10.4` (plaintext
  alarm/access codes) are real, not-yet-mitigated risks — worth remembering when writing the
  actual repository code in later phases, not just the SQL.
- Several `CHECK` constraints in `09_Constraints.sql` are marked `INTERPRETIVE` in comments
  (`Properties.PropertyStatus`, `CleaningInspections.Status`, `MaintenanceUpdates.UpdateType`,
  `RiskAssessments.Status`) — the scope doc mentions these fields without enumerating exact
  values, so a reasonable default list was chosen. Worth a quick sanity check against real usage
  once the app exists, not treated as scope-mandated.
