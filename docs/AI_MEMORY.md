# AI_MEMORY

Running log of architectural decisions and their reasoning, kept up to date every phase so a
future AI session (or the project owner) doesn't accidentally reverse a deliberate choice. Modeled
on PropertyManager's `documentation/progress-log.md`, which the owner found valuable for session
continuity on a long, multi-week build.

Do not delete entries here just because a phase is "done" — this file's value is historical
context, not a current-status board (see `AI_HANDOFF.md` for that).

---

## 2026-08-23 — Project started, Phase 1 (Architecture) in progress

- Project named **InspectIQ** (inspection + AI/OCR angle). Repo created at
  `C:\Users\shmil\Projects\InspectIQ`, deliberately outside OneDrive (owner's explicit instruction
  — avoids OneDrive file-lock/sync issues with `node_modules`, `.venv`, and SQLite/log files that
  change frequently during dev).
- Full scope document (22 numbered prompts + 20-phase build order) preserved verbatim in
  `docs/SCOPE.md`. Individual prompts split into `prompts/*.md` for quick reference, but
  `SCOPE.md` is the canonical source — if anything conflicts, `SCOPE.md` wins.
- Git identity set to match the PropertyManager repo (`Stern-5565` / `shmillystern@gmail.com`) for
  consistency across the owner's projects.
- Following the same working style validated on PropertyManager: real-DB testing (no mocks), one
  module = one commit with an honest message, verify before claiming done, phase-gate at natural
  checkpoints for owner review rather than running the entire 20-phase build unattended.

## 2026-08-23 — InspectionResponse snapshot strategy confirmed (PROJECT_PLAN.md §13.1)

Owner explicitly reviewed and confirmed the frozen-column snapshot approach over full
`InspectionTemplate` versioning, after asking specifically to be sure it wouldn't be regretted
later. Two mitigations were added as a direct result of that pushback, both **mandatory from
Phase 2, not optional**:

1. `InspectionQuestions`/Sections/Templates are soft-delete only — a hard delete would silently
   break the FK that the snapshot design deliberately keeps for analytics joins. Enforce at the
   repository layer (no `DELETE` statement against these tables), don't rely on convention alone.
2. `InspectionTemplate.Version` (bumped on any edit to it or its children) +
   `Inspections.TemplateVersionUsed` (captured at inspection-start). Not full version history —
   doesn't reconstruct what a past version looked like — but cheaply answers "which inspections
   predate/postdate this checklist change," which was the realistic gap in the frozen-column-only
   plan. If real template versioning is ever needed later, this column is exactly the backfill
   data a `TemplateVersions` table would need, so the migration path stays additive.

**Why this matters for future sessions**: if Phase 2's SQL ever ships without the soft-delete
enforcement or the `Version`/`TemplateVersionUsed` columns, that's a regression from an explicit,
reviewed decision — not a simplification to wave through in code review.

## 2026-08-23 — Phase 2 SQL written and verified against a real local SQL Server

All 25 tables, every deferred `CHECK` constraint, and 43 indexes now exist in a real local
`InspectIQDb` (`localhost\SQLEXPRESS`, Windows auth via `sqlcmd`) — not just designed on paper.
Verified with actual test inserts (valid/invalid data, FK violations, duplicate-unique
violations), not just "the script ran without error."

**The soft-delete-only requirement from the §13.1 sign-off is enforced by three
`INSTEAD OF DELETE` triggers**, not just a repository-layer convention as originally scoped —
upgraded during implementation to match the same "structural guarantee, not app convention"
principle already used for `RiskAssessments.RiskScore` (a `PERSISTED` computed column). Verified
live: a hard `DELETE` against `InspectionTemplates` is rejected and rolled back; `UPDATE ... SET
IsActive = 0` still works normally. If this ever needs undoing (e.g. a legitimate bulk-cleanup
tool), the correct approach is `DISABLE TRIGGER ... ON ...` for that one operation, not removing
the trigger.

**Two real SQL Server gotchas hit while writing the actual scripts** (not obvious from the design
doc, worth remembering for any future hand-written script against this schema — see
`AI_HANDOFF.md`'s "Important decisions" section for the fuller writeup):
1. `SET ANSI_NULLS ON` / `SET QUOTED_IDENTIFIER ON` are required in-session for any DDL or DML
   touching a table with a `PERSISTED` computed column or a filtered index — not just at table
   creation. The app's own DB driver (pyodbc/SQLAlchemy) sets these by default, but hand-written
   seed/fix scripts won't unless they say so explicitly.
2. Filtered index `WHERE` predicates don't support `NOT IN` — only `IN`, comparison operators,
   `IS NULL`/`IS NOT NULL`, and `AND`. Use `x <> a AND x <> b` instead of `x NOT IN (a, b)`.

**Interpretive design calls made while writing `09_Constraints.sql`**: the scope doc names a
"Status" field on `CleaningInspections`, `RiskAssessments`, and an "update type" on
`MaintenanceUpdates` without enumerating exact values (unlike `Inspections.Status` or
`MaintenanceIssues.Status`, which the scope spells out explicitly). Reasonable default enums were
chosen and marked `INTERPRETIVE` in the SQL comments — these are the one part of the Phase 2 SQL
that wasn't directly dictated by the scope doc, so worth a sanity check against real usage once
the app exists rather than treating them as immutable.

## 2026-08-23 — Phase 2 fully closed: seed data, views, dashboard queries, verified rebuild

Completed the rest of Phase 2 in the same session as the table/constraint/index work above:
5 roles, the full default "Monthly Property Inspection" template (21 sections, 102 questions,
built from scope's Prompt 4 - used the scope's own example questions verbatim where given, e.g.
Emergency Lighting's 5 questions, and wrote reasonable defaults for sections the scope only names
without detailing, e.g. General Property Condition, Entrance, Hallways).

**Deliberate design call on 4 "gateway" sections** (Communal Cleaning, Units, Vacant Units,
Maintenance, Risk Assessment): these carry only 1-2 checklist questions each rather than a full
question set, because their real substance already lives in dedicated tables/flows -
CleaningAreas/CleaningInspections for grading, VacantUnitInspections for vacant units,
MaintenanceIssues/RiskAssessments creatable from any question throughout the inspection.
Duplicating that detail as regular checklist questions would have fought the schema's own design
rather than complemented it. If a future session is tempted to "fill out" these sections with
more generic Yes/No questions, that's very likely a regression, not an improvement - check this
note first.

**`Users` was deliberately left unseeded.** A real `PasswordHash` needs Phase 5's actual hashing
algorithm; a fake placeholder hash would create rows that look like working demo logins but
aren't, which is worse than no demo users at all. Seed real demo users once Phase 5 exists.

**The global default risk matrix (`RiskMatrixLevels`, `CompanyId IS NULL`) was seeded as CORE
CONFIG, not demo data** - it lives in `13_SeedSampleData.sql` but in its own clearly-separated
Part A, because `RiskAssessments.RiskLevel` has nothing to snapshot from without it in ANY
environment, including production. Only Part B (the 2 demo companies) is local-dev-only. Don't
let a future "don't run seed data in production" instinct skip Part A too.

**`00_RunAll.sql` was tested for real, not just assembled**: dropped `InspectIQDb` completely
(`ALTER DATABASE ... SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE`) and rebuilt it from
nothing through the single script, then re-verified every count matched expectations. This is the
only way to actually know the file ordering and idempotency guards work together correctly - each
file having worked individually when run in sequence during development does NOT prove the
assembled `00_RunAll.sql` works, since e.g. the `RETURN`-only-exits-current-batch bug (below)
would have passed every individual-file test and only shown up on a true fresh run.

**Three more real bugs caught by actually running things, not just assumed**:
1. `SUM(CASE...)` returns `NULL` over zero rows, not `0` - every dashboard aggregate in
   `15_DashboardQueries.sql` needed `ISNULL(..., 0)`. Caught by running the queries against
   Northgate before any MaintenanceIssues/RiskAssessments/CleaningInspections existed.
2. `RETURN` in a `.sql` script only exits the current batch, not the whole script - a `GO`
   between an idempotency guard and the logic it's meant to skip silently defeats the guard.
   Caught in `12_SeedInspectionTemplate.sql` by testing re-run behavior explicitly, not assumed.
3. `Properties` has filtered indexes (`IX_Properties_NextInspectionDue`,
   `IX_Properties_PropertyStatus`), so it needs the same `ANSI_NULLS`/`QUOTED_IDENTIFIER ON`
   session settings as `RiskAssessments` does for its computed column - this wasn't obvious from
   the RiskAssessments-focused gotcha already documented above, and bit
   `13_SeedSampleData.sql`'s very first `Properties` INSERT.

## 2026-08-23 — Phase 4 (FastAPI foundation) built and verified two ways

Python 3.14.6 was already the only interpreter on this machine (via the `py` launcher) - checked
before assuming an older version was needed, since 3.14 is recent enough that some C-extension
packages could plausibly lack wheels yet. They didn't: fastapi, sqlalchemy, pyodbc, pydantic-core,
bcrypt, greenlet all installed clean with `cp314` wheels, no compatibility issues.

**The JWT-secret-placeholder guard and `APP_DEBUG=False` default (PROJECT_PLAN.md §12.2) were
built into `config.py` from the start**, not retrofitted after a security audit the way
PropertyManager's were - `Settings`'s `model_validator` refuses to construct if `APP_ENV` isn't
`"development"` and `JWT_SECRET_KEY` is still the `.env.example` placeholder or under 32 chars.
Verified with 4 real tests (`tests/test_config.py`), not just written and assumed correct -
placeholder/short secret rejected outside dev, both allowed in dev, real secret accepted outside
dev, CORS origin string parsing.

**Verified two independent ways, not just "pytest passed"**: `pytest` (6/6 passing, in-process via
`TestClient`) AND a real standalone `uvicorn` server started, hit with actual `curl` over HTTP
(`/api/health` returned the correct JSON, `/docs` returned 200), then stopped. The health check
genuinely executes `SELECT 1` against the real `InspectIQDb` on every call - it's not a stub that
always returns 200 regardless of DB state.

**Layering rules from PROJECT_PLAN.md §5 are already visible in the two files that exist**:
`app/api/health.py` is intentionally thin (parses nothing, one DB call via a dependency, returns
a schema); `app/core/exceptions.py` centralizes HTTP-status mapping so no future service will
need to construct `HTTPException` directly. No models/repositories/services exist yet - Phase 5
(Authentication) is what actually exercises those layers for the first time with `Users`/`Roles`.

**Note for later**: a `StarletteDeprecationWarning` appears during test runs (`httpx` vs a future
`httpx2` package) - a version-pairing artifact of very new Starlette (1.6.0) + httpx (0.28.1),
not a real problem today. If a future dependency bump turns this into a hard failure, that's the
first place to look, not a mystery regression.

## 2026-08-23 — Phase 5 (Authentication) built, and a real bug pytest alone couldn't catch

Built per scope Prompt 6: `Company`/`Role`/`User` models (`UserRoles` as a plain SQLAlchemy
`Table`, not a mapped class, since it's a pure M:N join with no extra columns), password hashing
(`bcrypt`), centralized role-name constants (`security/roles.py`), JWT access+refresh tokens,
`get_current_user`/`require_roles` dependencies, login/refresh/me routes, 12 new tests (18
total). Login's error message is deliberately identical whether the email doesn't exist, the
password is wrong, or the account is disabled - a standard OWASP-aligned tradeoff (never let a
login response reveal which one was wrong) accepted over the UX benefit of a clearer "your
account is disabled, contact IT" message. JWTs deliberately carry only `sub`/`type`, never
`CompanyId` - `get_current_user` reloads the full user from the DB on every single request
anyway (the same re-check-`IsActive`-every-request pattern that caught a real bug in
PropertyManager), so a token-embedded `CompanyId` would be extra surface area for zero benefit.

**The real finding this session**: `User.company: Mapped["Company"] = relationship(...)`
references `Company` by string (standard SQLAlchemy pattern to avoid circular imports), but
`app/models/user.py` only imports `Company` under `if TYPE_CHECKING` - which means nothing at
*runtime* ever caused `Company` to be registered with SQLAlchemy's declarative registry, unless
some other code happened to import it first. `pytest` never caught this: all 18 tests passed,
because `tests/test_auth.py` imports `from app.models.company import Company` directly (needed
for its own fixture, to look up the demo company's `CompanyId`), which incidentally registered
`Company` before any query ran - accidentally masking a real bug. It only surfaced when a genuine
standalone `uvicorn` server was started and hit with real `curl` requests: `POST /api/auth/login`
against a nonexistent email returned a raw `500` (`sqlalchemy.exc.InvalidRequestError: ...
failed to locate a name ('Company')`) instead of the expected `401`.

**Fixed with `app/models/__init__.py`** importing every model class together (not relying on
whatever happens to import them first), itself imported from `app/database/session.py` so it's
guaranteed to run before any session/query is created, regardless of entry point.

**Why this matters beyond this one bug**: it's concrete proof that "pytest passes" and "the
feature actually works" are not the same claim in this codebase, specifically because a test
file's own setup code can accidentally paper over a registration-order bug that real application
code paths never trigger. **Every future session adding a new SQLAlchemy model must add it to
`app/models/__init__.py`, and must verify with a real running server (not just pytest) before
calling a model "done."** This is now the standing verification bar for backend work, not a
one-off caution.

## 2026-08-23 — Phase 6 (Properties + Units) built, a real Python 3.14 gotcha found

Built per scope Prompt 7: `Property`/`Unit` models, enum-validated schemas, repositories,
services, routes, 14 new tests (32 total) - all against the real DB, all cleaned up per-test.

**Real, non-obvious bug found and fixed**: a Pydantic field named identically to its own enum
type - `PropertyType: PropertyType`, `PropertyStatus: PropertyStatus`, etc. - crashes under
Python 3.14 specifically, with `TypeError: unsupported operand type(s) for |: 'NoneType' and
'NoneType'` when evaluating `PropertyType | None`. Python 3.14's PEP 649 lazy annotation
evaluation resolves a class's own annotations in a namespace where the class's own attribute
name - even a bare, value-less annotation like `PropertyType: PropertyType` - shadows the
module-level import of the same name, unlike pre-3.14 Python's eager evaluation. This is a
genuine version-specific trap, not a hypothetical one - it was hit for real while writing
`app/schemas/property.py`. **Fixed by aliasing every enum import** (`from app.schemas.enums
import PropertyType as PropertyTypeEnum`) in both `schemas/property.py` and `schemas/unit.py`.
**Any future schema reusing a DB column name that matches an enum class name must do the same
aliasing** - this is now a standing rule for this project, not a one-off fix, and it's specific
to running on Python 3.14 (a pre-3.14 project might never have hit it).

**Cross-company access returns 404, not 403** - `property_service.get_property` and
`unit_service.get_unit` both raise `NotFoundError` (never `ForbiddenError`) when a resource
exists but belongs to another company, so a wrong-company lookup is indistinguishable from a
lookup of something that was never there at all. Verified for real: a live `curl` request as
the Bright Spaces admin for a Northgate `PropertyId` returned `404 {"detail":"Property not
found."}`, not a 403. This is the applied, tested version of the isolation principle
`docs/DATABASE.md §10.1` only described in the abstract - now there's a working example to
copy for every future module that needs the same protection (Maintenance, Risk, etc.).

**`Units` has no `CompanyId` column of its own** (by design, `docs/DATABASE.md §2`/`§9.5` - only
tables that needed *direct* isolation queries got a denormalized `CompanyId`; Units is reached
via a cheap single join to `Properties`). `unit_repository.py`'s every method joins through
`Properties` and filters on `Properties.CompanyId` - never trusts a bare `UnitId` to imply
company-scoping. Tested explicitly: creating a unit under another company's `PropertyId` (a
plausible ID-guessing attack, not just an accidental cross-company GET) correctly 404s.

**Interpretive design call, documented in `app/api/properties.py`'s own module docstring**:
scope Prompt 7 says "Inspectors can view properties they have permission to inspect," but no
per-property assignment table exists in the 25-table schema. Read as company membership: any
authenticated user in the property's company can view (Inspector/Maintenance/Viewer all
plausibly need to see property details to do their jobs), only Administrator/Manager can
create/update/deactivate. Unit occupancy-status changes were deliberately kept in that same
Administrator/Manager bracket for this phase too, even though realistically an Inspector doing
a walkthrough is the one who'd discover a vacancy - that flow is expected to arrive through the
Inspection engine (Phase 8) calling into unit updates via its own service, not through this
standalone API being opened up prematurely. Revisit if Phase 8 needs a different answer.

## 2026-08-23 — Phase 7 (Inspection Templates API) built read-only, on purpose

Scoped deliberately narrow: list + full-nested-detail, no create/edit. Scope §9 explicitly
calls template authoring an "eventually" feature, and the actual next scope phase (the
inspection engine, Prompt 8) needs a template to *read from* to start an inspection, not to
*write*. Building CRUD here would have been scope creep ahead of any real need - noted
explicitly in `app/api/inspection_templates.py`'s own module docstring so a future session
doesn't assume the missing CRUD was an oversight.

**Applied the Phase 5 lesson proactively this time**, rather than rediscovering it: added
`InspectionTemplate`/`InspectionSection`/`InspectionQuestion` to `app/models/__init__.py`
immediately, then ran a real query through the relationships (`template.sections[0].questions`)
against the live seeded data *before* writing a single route or repository function. Nothing was
broken this time - the point of doing the check isn't that it always finds a bug, it's that
skipping it is how the Phase 5 bug happened in the first place.

**`sections`/`questions` relationships carry `order_by=...SortOrder` at the model level**, not
left to query-time `.order_by()` calls scattered across repositories - every future code path
that walks a template (list, detail, and eventually the inspection-start logic in Phase 8) gets
correctly ordered sections/questions for free, with no way to forget it.

**New test-cleanup pattern needed and used for the first time**: the isolation test needed a
throwaway *company-specific* `InspectionTemplate` (no such row exists in seed data - only the
global default), and cleaning it up hit the real `INSTEAD OF DELETE` trigger from Phase 2 (working
exactly as designed). Fixed by disabling the trigger for one statement, deleting, re-enabling it,
and - importantly - the test also explicitly re-queries `sys.triggers.is_disabled` afterward to
prove the trigger is back on, not just assumed. **This disable/delete/re-enable pattern is for
test cleanup only and must never appear in application code** - anywhere it shows up outside
`tests/`, that's a bug, not a legitimate use of the escape hatch.

## 2026-08-23 — Phase 8 (Inspection Engine) built, the biggest phase so far

The core loop scope Prompt 8 describes: start an inspection from a template (snapshotting every
active question into a frozen `InspectionResponse`), answer/note/mark-NA, track completion, block
submission until mandatory questions are done, and lock everything once submitted. Deliberately
excluded the three sub-features Prompt 8 mentions whose own modules don't exist yet - photos/
videos (Phase 9), creating a maintenance issue or risk assessment from a response (Phases 10/13)
- with a comment in `app/api/inspections.py` explaining why, so a future session doesn't read
their absence as an oversight.

**`InspectionResponse` ordering deliberately does NOT use a live join to
`InspectionQuestion.SortOrder`.** Responses are batch-created in template `SortOrder` at
inspection-start time, and then ordered thereafter by `InspectionResponseId` (creation order) -
not re-sorted via the question's current `SortOrder` on every read. This matters: if a template
gets reordered later, an already-started inspection's response order must stay exactly as it was
when the inspector saw it, not silently reshuffle underneath them. `SortOrder` was deliberately
never added to the frozen snapshot columns (`docs/DATABASE.md §4`) because relying on creation
order achieves the same historical-stability property for free, without a new column.

**Mandatory-question validation at submit time uses the LIVE `InspectionQuestion.IsMandatory`,
not a snapshot** - the one deliberate, documented exception to "always render from the snapshot."
The reasoning: response *content* (what the inspector saw and answered) must stay historically
frozen for report accuracy, but a validation *rule* is different in kind - if an admin changes a
question from mandatory to optional while an inspection is still in progress, the inspector
submitting today should get today's rule, not a stale one from when they started. This is a
narrow, deliberate carve-out, not a general permission to join to the live template wherever
convenient - see `inspection_response_repository.list_unanswered_mandatory`'s own comment before
copying this pattern elsewhere.

**Authorization is narrower here than any prior module, and that's correct, not an
inconsistency.** Properties/Units/Templates all follow "any company member can view, only
Admin/Manager can mutate." Inspections adds a THIRD tier: only the inspection's own assigned
`InspectorUserId`, or an Administrator/Manager, can answer questions or submit - a different
Inspector at the same company is not enough, even though they share the exact same role. The
reasoning, documented in `inspection_service._ensure_can_edit`: a property is shared reference
data everyone in the company legitimately works with; an in-progress inspection is one specific
person's active work-in-progress, and letting any same-titled colleague silently edit it is a
real, not hypothetical, data-integrity risk. Verified with a genuine two-inspector test (the
non-owning inspector gets 403) and a manager-override test (200) - not just asserted from the
docstring.

**Immutability after submission is enforced at the service layer, not the database** - unlike
`InspectionTemplates`, `Inspections`/`InspectionResponses` have no `INSTEAD OF DELETE`-style
trigger. `update_response` and `submit_inspection` both check `Status == "Submitted"` and reject
with 409. This also directly satisfies one of scope Prompt 19's explicitly named dangerous edge
cases ("Duplicate submission") ten phases before Phase 18 (Testing) was scheduled to check for
it - worth remembering that some of Prompt 19's checklist gets covered incidentally by earlier
phases doing their job correctly, not only by a dedicated testing pass at the end.

**Verified live with a full realistic workflow**, not just individual endpoint pokes: a real
Inspector login, a real property, a real template, a real started inspection (21 sections, 102
responses), one real answered question, a completion percentage confirmed at exactly the expected
value (1.0%, i.e. 1/102), and a submit attempt that correctly listed 12 remaining mandatory
questions (13 total minus the one just answered) - proving the whole chain works together, not
just each piece in isolation.

**Demo users seeded** (`backend/scripts/seed_demo_users.py`, run via `python -m
scripts.seed_demo_users` from `backend/`, idempotent): one user per role at Northgate Property
Management (`admin@northgatepm.example`, `manager@`, `inspector@`, `maintenance@`, `viewer@`) +
one Administrator at Bright Spaces Estates (`admin@brightspaces.example`), all password
`Password123!`. Verified for real: logged in as the Northgate admin against a live server and
got back real, working tokens. This closes the gap flagged since the Phase 2 seed-data work
("`Users` deliberately NOT seeded... a fake placeholder hash would be worse than no demo users
at all") - now that Phase 5 exists, the hashes are real.

## 2026-08-24 — Phase 9 (Photo & Video Uploads) built, real Windows file-lock bug caught live

Built the `IMediaStorageService` abstraction and a generic, polymorphic `/api/media` router,
per scope §20 and `PROJECT_PLAN.md §8`. `MediaFiles` was already a real table since Phase 2
(`database/tables/07_MediaAndNotesTables.sql`), so this phase is entirely application code: no
new SQL.

**One refinement to the §8 sketch, made necessary by actually implementing it**: the original
`IMediaStorageService` had `save`/`get_url`/`delete` only. `get_url` implicitly assumed a
browser-redirectable URL, which only exists once real blob storage is added (Phase 20) - local
dev has no static file server exposing `backend/uploads/` (deliberately: that would bypass the
"authorization mirrors the parent entity" rule entirely, letting anyone with a guessed/leaked
URL bypass the permission check). Added `open_stream(storage_key) -> BinaryIO` to the Protocol
so the download endpoint reads bytes back through the already-authenticated API instead;
`get_url` stays on the interface for the future blob implementation and returns `None` for
`LocalFileStorageService`. `app/services/media_storage.py`'s docstring explains this in full -
worth reading before adding the production blob implementation in Phase 20, so its `get_url`
return value doesn't get treated as sufficient authorization on its own (it isn't - a signed URL
is only handed out AFTER our own permission check passes, same principle, different mechanism).

**`SUPPORTED_ENTITY_TYPES` is `("Property", "Unit", "Inspection", "InspectionResponse")` -
narrower than scope §20's full list**, which also names MeterReading, MaintenanceIssue,
RiskAssessment, CleaningInspection. Those tables exist (Phase 2), but their own services don't
(Phases 10/11/13/14), and §8's core rule - "file access authorization mirrors the parent
entity's authorization" - is impossible to enforce for a parent with no service to ask. Same
incremental-scoping pattern as Phase 7's read-only Templates API. Add each one to
`app/services/media_service.py`'s `_VIEW_CHECKS`/`_MUTATE_CHECKS` dicts as its own phase lands.

**Two authorization levels per entity type, not one - a real design decision, not boilerplate.**
View (list/download) reuses each parent module's own "get" (already "any company member" for
every supported type today). Mutate (upload; delete/caption-edit use a related but distinct
uploader-or-Admin/Manager check) is where it gets interesting: for Property/Unit, mutate is the
SAME as view - deliberately NOT the narrower Administrator/Manager-only bar those modules use
for editing the property/unit record itself, because scope's Inspector role description
explicitly lists "upload evidence" as its own standing capability, separate from editing a
property. For Inspection/InspectionResponse, mutate reuses `inspection_service.ensure_can_edit`
(renamed from `_ensure_can_edit` - made module-public specifically for this reuse), the same
assigned-inspector-or-Admin/Manager rule Phase 8 established: attaching a photo to an
in-progress inspection is part of doing that inspection, not shared company data.

**`InspectionResponse` media needed a new repository function that breaks the module's own
stated rule, deliberately and documented as such.**
`inspection_response_repository.py`'s header says "no company_id parameter on any function
here - by design," because every existing caller already has an authorized `InspectionId` in
hand before touching a response. Media upload only has the bare `response_id` from the client
(via the generic `EntityType`/`EntityId` pair), with no `InspectionId` yet - so
`get_response_by_id_for_company` joins out to `Inspections`/`Properties` itself to establish
isolation first, then the caller resolves and edit-checks the parent `Inspection` the normal
way. Documented in the file's own header as the one deliberate exception, not an oversight.

**A real bug found only by testing with an actual running server on Windows, not by pytest -
the same category of lesson as Phase 5's, different mechanism.** The first `StreamingResponse`
implementation for `/api/media/{id}/download` passed the raw file object returned by
`open_stream()` straight through as the response content. Starlette's `StreamingResponse`
iterates its content but never closes a plain file object - the handle leaked on every
download. `pytest` alone didn't obviously fail on this the way Phase 5's bug did; it surfaced as
a genuine `PermissionError: [WinError 32] The process cannot access the file` the moment a test
tried to delete the same file right after downloading it - Windows won't let you delete (or
sometimes even re-read) a file with an open handle, unlike POSIX. Fixed with a small
`_iter_and_close` generator in `app/api/media.py` that reads in 64KB chunks and closes the
stream in a `finally` block. Confirmed fixed by re-running the exact test that caught it, AND
by a live curl session: upload → download (byte-for-byte match) → list → cross-company 404 →
delete → confirm gone, then checking `backend/uploads/` afterward for orphaned files (none).
**Standing lesson for this project**: this is the second time a real running server (not pytest)
caught a bug pytest's own assertions didn't directly surface - keep testing against a live
server for every phase, not just when TestClient's in-process fake happens to miss something.

**Upload validation order is deliberate**: the mutate-permission check runs BEFORE the file is
ever written to disk (fail fast on authorization, no wasted I/O for a request that was going to
be rejected anyway), but content-size validation happens AFTER the file is saved (since
`UploadFile` doesn't expose a reliable size before reading it) - an oversized file is deleted
immediately if it exceeds `MEDIA_MAX_IMAGE_SIZE_BYTES`/`MEDIA_MAX_VIDEO_SIZE_BYTES`, never left
orphaned on disk. Content-type is checked against a fixed allowlist (`_ALLOWED_CONTENT_TYPES` in
`media_service.py`) before any disk I/O at all.

**Caption edits and deletes are gated narrower than upload/view**: uploader, or
Administrator/Manager - not "any company member who can view the parent entity." Someone else's
uploaded evidence shouldn't be silently editable or removable just by shared company membership,
the same reasoning Phase 8 applied to inspection responses (one person's work, not shared data)
applied here to one person's uploaded file.

8 new tests (59 total), all against the real DB with throwaway users/media rows/files cleaned up
per-test (including actually deleting the file written to `backend/uploads/`, not just the DB
row): upload+download+list round-trip with byte-for-byte content verification, cross-company
404 on upload, unsupported `EntityType` and unsupported content-type both 422, delete-by-uploader
removes both the row and the file (checked with `Path.exists()`, not just asserted), delete by a
non-uploader non-admin 403, upload to an `Inspection` by an unassigned Inspector 403 (reusing
`ensure_can_edit`, proving the reuse actually works end-to-end and not just at the import level),
caption update by the uploader.

## 2026-08-24 — Phase 10 (Maintenance Issue System) built, first real service-to-service cycle

Built the maintenance module per scope §17/§18. `MaintenanceIssues`/`MaintenanceUpdates` were
already real tables since Phase 2 (`database/tables/05_MaintenanceTables.sql`), so like Phase 9,
this is entirely application code - no new SQL.

**Three authorization tiers in one module - the third distinct shape this project has needed,
each for a different reason, and each documented as deliberate rather than copied by default.**
Properties/Units/Templates: any company member views, Admin/Manager mutates. Inspections
(Phase 8): any company member views, but mutate narrows to the assigned inspector or Admin/
Manager - one person's active work. MaintenanceIssues needed BOTH ideas at once, split by which
kind of action it is: general field edits (Title/Category/Priority/DueDate/Notes) and deciding
who's assigned are management decisions - Admin/Manager only, gated at the ROUTE level exactly
like Properties/Units. But actually DOING the work - changing status, adding a note, uploading a
photo - is the Inspections shape: the issue's own `AssignedUserId`, or Admin/Manager, reusing
`ensure_can_edit` almost verbatim from `inspection_service.py`. The one real wrinkle: unlike an
Inspection's `InspectorUserId` (always self-assigned, always one of the Inspector-tier roles),
`MaintenanceIssue.AssignedUserId` is set by an Admin/Manager and can point at ANY company user
regardless of role - scope doesn't restrict assignment to people with the "Maintenance" role
specifically. That's exactly why status/notes/photos are gated at the SERVICE level
(`ensure_can_edit`) rather than a route-level `require_roles` list the way general-edit/assign
are: a role-based gate can't express "whoever this issue happens to be assigned to," only
`ensure_can_edit`'s live lookup of `issue.AssignedUserId` can.

**`create_issue` deliberately handles two entry points through one endpoint, not two.** A manual
issue supplies `PropertyId` directly. An issue "created from any inspection question" (scope
§17's own phrasing) supplies `InspectionResponseId` instead, and the service resolves
Property/Inspection from the response itself - critically, a client-supplied `PropertyId`
alongside a response is ignored/overridden, never trusted, because a mismatched pair (this
photo is really from property 4, but claims to be about property 7's response) would be a real
cross-tenant data-integrity bug, not just sloppy input. `Location` auto-fills from the
response's `SectionNameSnapshot`/`QuestionTextSnapshot` (scope's "automatically copying...
Inspection section, Checklist item") as plain text rather than as new duplicate columns on
`MaintenanceIssues` - `InspectionResponseId` is already a stable FK back to the authoritative
snapshot for anything that needs it structurally (e.g. a future report), so duplicating those
two strings onto the issue itself would just be a second, driftable copy of data that already
has one true source.

**The first genuine two-service circular dependency this project has hit, and how it was
resolved.** `maintenance_service.upload_photo` wants to reuse `media_service.upload_media`
rather than duplicate its content-type/size validation and storage calls. But
`media_service`'s own entity-type dispatch table needs a resolver for
`EntityType="MaintenanceIssue"` that calls `maintenance_service.get_issue`/`ensure_can_edit` -
so each module needs to import the other. A top-level import on both sides would be a real
Python circular-import error, not a style nitpick. Resolved with function-local imports
(`from app.services import media_service` / `from app.services import maintenance_service`
written *inside* the specific functions that need them, not at module top level) on BOTH sides -
each file's relevant function has a comment pointing at its counterpart. This is a deliberate,
pragmatic choice for two modules that legitimately need each other for different reasons, not a
sign the architecture needs restructuring; confirmed it actually works (not just "should work
in theory") two ways - `app.main` importing cleanly at all (a real circular import would fail
at process startup, not silently), and a live curl photo upload that produced a real `MediaFile`
row end-to-end.

**`assign_issue` auto-advances `Open` → `Assigned` but never moves a further-along issue
backwards on reassignment** - handing an `InProgress` issue to someone else stays `InProgress`
and records a `Comment`-type timeline entry instead of a `StatusChange`. This is an interpretive
convenience (scope doesn't specify assignment's exact interaction with status), documented as
such in the service.

**`update_status` rejects a no-op transition to the issue's current status with a 422**, and
sets `CompletedDate` exactly once, the first time an issue enters `Completed` (never overwritten
by a later `Completed`→`Closed`→ back-to-`Completed` cycle, though scope's own status list
doesn't actually allow re-opening a Closed issue through this endpoint's semantics - Status is
deliberately unconstrained to a strict state machine, since scope names six values but never
specifies a transition graph, and inventing one would be unrequested complexity).

**`get_response_by_id_for_company` (added in Phase 9 for InspectionResponse media) got its
second real caller here** - `create_issue`'s from-response path uses the exact same function,
which is good evidence it was designed at the right level of generality rather than being a
one-off written just for media.

14 new tests (73 total), all against the real DB with issues/updates/media files cleaned up
per-test (including deleting the file written to `backend/uploads/`): manual create, role-gated
create (Maintenance role blocked, matching Inspections' Prompt-8-style tier), cross-company 404,
missing-Property-and-Inspection 422, create-from-response derives Property/Inspection/Location
correctly, an `AssignedUserId` at create time starts the issue `Assigned` not `Open`,
cross-company get 404, general-edit 403 for the assigned Maintenance worker (proving the
route-level Admin/Manager gate holds even for the person actually doing the work), assign moves
Open→Assigned with a timeline entry, status update 200 for the assigned user / 403 for an
unassigned one / 422 for a same-status no-op, `Completed` sets `CompletedDate`, note-adding
writes a `Comment` entry, photo upload writes both a `MediaFile` row and a `PhotoUploaded`
timeline entry - checked via the maintenance detail response AND the generic `/api/media` list,
proving the cross-service integration works end-to-end, not just at the import level.

**Verified live** with the full realistic workflow: real Inspector login created an issue on a
real property → real Admin assigned it to the Maintenance demo user (Open→Assigned) → the
now-unassigned Inspector got 403 attempting a status update, the assigned Maintenance worker got
200 (Assigned→InProgress) → a note was added → a real photo uploaded via curl showed up both in
the issue's own timeline (`PhotoUploaded`) and in a plain `GET /api/media?entity_type=
MaintenanceIssue...` call → a Bright Spaces admin got 404 on the issue → cleanup required the
same `SET ANSI_NULLS ON`/`SET QUOTED_IDENTIFIER ON` preamble documented since Phase 2
(`MaintenanceIssues` carries a filtered index), re-confirming that gotcha is still very much
alive for any hand-written script touching this table, three phases and one live-server session
after it was first documented.
