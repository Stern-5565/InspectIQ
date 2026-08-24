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
    MaintenanceIssue (Phase 10) and CleaningInspection (Phase 11, see below) have since been
    added — MeterReading/RiskAssessment are still deferred to Phases 13/14.
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

## Currently being worked on

- Nothing in progress. Committing this batch to git is the next action.

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
`app/api/media.py`'s `_iter_and_close`. When adding a new polymorphic-media entity type
(RiskAssessment/CleaningInspection/MeterReading remaining), add it to both `media_service.py`'s
`_VIEW_CHECKS` and `_MUTATE_CHECKS` dicts and to `app/schemas/media_file.py`'s `ENTITY_TYPES`
tuple — not just one of the three (MaintenanceIssue in Phase 10 is the reference example).
**When two services each need to call the other, use a function-local import on (at least) one
side rather than restructuring the module boundary** — confirmed working, not just theoretical,
by `media_service`↔`maintenance_service` in Phase 10 (see either file for the exact pattern and
the comment explaining which side owns the local import and why). **But check each direction
independently before reaching for that workaround** — Phase 11's `property_service`→
`cleaning_service` call needed it (a real cycle, since `cleaning_service` imports
`property_service`), while `media_service`→`cleaning_service` didn't (no cycle exists, since
`cleaning_service` never needs `media_service`) — a plain top-level import was correct there,
and using a local one anyway would just be needless caution copied from Phase 10 without
re-checking it actually applies.

## Next tasks

1. Commit this batch (Communal Cleaning Grading) to git.
2. Phase 12 — Vacant Unit Inspection (`prompts/backend_prompt.md`, Prompt 13):
   `VacantUnitInspections` model (table already exists, Phase 2 — its own table, not a generic
   `InspectionResponse`, since scope §13 needs history without overwriting the unit's current
   status and the field set — electricity/water/heating on/off etc. — doesn't fit the generic
   Yes/No/Text/Number shape, per `docs/DATABASE.md`). Likely follows the Phase 11 shape (tied to
   a real `Inspection`, graded/checked by the assigned inspector or Admin/Manager) more than
   Maintenance's three-tier one — check `docs/DATABASE.md`'s `VacantUnitInspections` entry and
   scope §13 in full before assuming, the same way each prior phase re-derived its own shape
   instead of copying the previous module's by default.

## Files that require attention

- `docs/DATABASE.md §10.1` (denormalized `CompanyId` drift risk) and `§10.4` (plaintext
  alarm/access codes) are real, not-yet-mitigated risks — worth remembering when writing the
  actual repository code in later phases, not just the SQL.
- Several `CHECK` constraints in `09_Constraints.sql` are marked `INTERPRETIVE` in comments
  (`Properties.PropertyStatus`, `CleaningInspections.Status`, `MaintenanceUpdates.UpdateType`,
  `RiskAssessments.Status`) — the scope doc mentions these fields without enumerating exact
  values, so a reasonable default list was chosen. Worth a quick sanity check against real usage
  once the app exists, not treated as scope-mandated.
