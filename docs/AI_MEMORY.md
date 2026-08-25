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

## 2026-08-24 — Phase 11 (Communal Cleaning Grading) built, closed a Phase-1-flagged gap

Built the cleaning module per scope §16. `CleaningAreas`/`CleaningInspections` were already real
tables since Phase 2 (`database/tables/04_InspectionTables.sql`), so like Phases 9 and 10, this
is entirely application code - no new SQL.

**Two authorization tiers, deliberately simpler than Maintenance's three - the fourth distinct
shape this project has needed, and the first time a module was consciously kept SIMPLER than an
available template rather than matching it.** `CleaningAreas` (a property's configurable area
list) mirrors Properties/Units exactly: any company member views, Administrator/Manager
mutates, gated at the route level - it's property configuration, not day-to-day work.
`CleaningInspections` (the actual grading records) mirrors the Inspection engine's own shape
instead: any company member views, the inspection's assigned inspector or Admin/Manager mutates,
reusing `inspection_service.ensure_can_edit` directly with no independent carve-out. That last
point is the interesting one: MaintenanceIssue's `AssignedUserId` gets its own "assignee can
edit" tier because assigning work to a person and then letting that person update their own
work is exactly what scope's Maintenance flow describes. `CleaningInspection.AssignedUserId`
looks identical at the schema level, but this system has no "Cleaner" role at all (scope's 5
roles - Administrator/Manager/Inspector/Maintenance/Viewer - don't include one), and §16 never
describes a cleaner logging in to update their own grading record the way §17 describes a
Maintenance User updating their own ticket. Copying Maintenance's three-tier shape here would
have been inventing a permission model scope never asked for; the two-tier Inspection-engine
shape is what the actual requirement supports. Worth remembering for Phase 12 (Vacant Unit
Inspection) and beyond: a new module resembling a previous one at the schema level does not
mean it should copy that module's authorization shape - re-derive it from what the module
actually represents, the same standing rule from Phase 8, applied here in the other direction
(simplifying down, not complicating up).

**Closed a real gap flagged all the way back at Phase 1, not a new one found this session.**
`docs/DATABASE.md §10`'s "Possible Problems" #5 said outright: "`CleaningAreas` is per-property,
so a new property has zero cleaning areas until someone configures them - a real onboarding gap
if not handled... Decide during Phase 6 (Properties + Units) - noting it here so it isn't
forgotten." Phase 6 shipped without deciding it. Phase 11 - the phase that actually makes
`CleaningAreas` functional for the first time - was the right moment to close it:
`property_service.create_property` now calls a new
`cleaning_service.seed_default_areas_for_property` immediately after creating a property,
seeding exactly the 3-area default (`Entrance`/`Hallway`/`BinArea`) `DATABASE.md` itself already
suggested - not a new invented list, the one that was proposed and shelved. This is the second
time in this project a flagged-but-deferred item got closed at the moment its dependency
finally existed (the first was MediaFiles waiting from Phase 2 to Phase 9) - worth treating
`docs/DATABASE.md §10`'s whole "Possible Problems" list as a standing punch list to revisit at
the start of any future phase, not just a one-time read.

**A second circular-import situation, resolved two different ways after checking each direction
separately - the useful lesson here is the checking, not a new technique.** `property_service`
needed to call `cleaning_service.seed_default_areas_for_property`, but `cleaning_service` already
imports `property_service` at the top level for its own `CleaningArea` authorization checks - a
real cycle, resolved with the exact same function-local-import pattern Phase 10 established for
`media_service`↔`maintenance_service`. But `media_service`'s new `CleaningInspection` entity-type
resolver (`_view_cleaning_inspection`/`_mutate_cleaning_inspection`) needed `cleaning_service`
too, and here a plain top-level import worked fine - `cleaning_service` has no reason to import
`media_service` back, since (unlike `maintenance_service.upload_photo`) nothing in the cleaning
module needs its own photo-upload convenience wrapper; the generic `/api/media` endpoint with
`EntityType="CleaningInspection"` is the only upload path, and that's sufficient for what scope
§16 actually asks for ("Pictures," no before/after distinction, no audit-trail requirement to
hook into). The mistake this avoided: reflexively adding a local import "just in case," copying
Phase 10's fix without re-verifying a cycle actually existed on this side. It didn't, so it
wasn't used.

**`create_cleaning_inspection` validates `CleaningAreaId` belongs to the inspection's own
`PropertyId`**, the same defensive pattern Phase 10's `create_issue` used for `UnitId` - a
`CleaningAreaId` from a different property in the same company would otherwise silently attach
a grading record to the wrong property's checklist, a real (if company-internal) data-integrity
bug, not just an inconsistency.

12 new tests (85 total), all against the real DB with areas/inspections/media cleaned up
per-test: the auto-seed-on-create behavior itself (3 areas, correct `AreaType` values, all
active), area create/update role gating and cross-company 404, grading as the assigned
inspector, an `AssignedUserId` supplied at create time starting the record at `Status="Assigned"`
instead of `"Pending"` (mirroring Phase 10's exact convention), a `CleaningAreaId` from a
different property rejected with 422, an unassigned inspector getting 403, grading a `Submitted`
inspection rejected with 409 (the same immutability rule `InspectionResponses` use, applied here
for the first time to a sibling table rather than the responses themselves), a partial `PATCH`
proven to leave untouched fields alone, and - the integration-proving test - a photo uploaded
through the *generic* `/api/media` endpoint with `EntityType="CleaningInspection"` that then
correctly appears in a plain `GET /api/media?entity_type=CleaningInspection...` call, confirming
the new dispatch entry actually works end-to-end and not just at the import level.

**A real test-fixture gap, not an app bug, caught before it ever reached CI.** An early version
of the `northgate_area_id` fixture assumed the demo property "15 High Road" would have an
`Entrance` `CleaningArea` to reuse. It doesn't - only "Elm Court" (a block of flats) got seeded
communal areas in Phase 2's original demo data; "15 High Road" is an HMO with none, and Phase
11's new auto-seed-on-create only applies to properties created from now on, not retroactively
to existing seeded ones. The fixture returned `None`, which then produced a cascade of confusing
422s in every dependent test rather than one clear failure. Fixed by having the fixture create
and tear down its own throwaway `CleaningArea` directly, removing the dependency on which demo
property happens to have pre-seeded ones - a more robust pattern worth preferring generally when
a fixture's needed data isn't guaranteed to exist in every environment the tests might run in.

**Verified live**: created a real property via curl and confirmed exactly 3 auto-seeded areas
with the right names/types → started a real inspection on that property → graded a communal area
(`Grade=D`, `CleaningRequired=true`, starting `Status="Pending"`) → a Bright Spaces admin got 404
listing that inspection's cleaning grades → an Administrator (not the assigned inspector) used
the Admin-override path to move the grade to `Completed` → a real photo uploaded via curl with
`EntityType=CleaningInspection` showed up in the generic media list → all of it (property,
auto-seeded areas, inspection, its 102 snapshot responses, the cleaning grade, the media row and
its file on disk) cleaned up afterward, using the same `SET ANSI_NULLS ON`/`SET QUOTED_IDENTIFIER
ON` preamble every hand-written script against this schema has needed since Phase 2.

## 2026-08-24 — Phase 12 (Vacant Unit Inspection) built, closed a Phase-6-flagged gap

Built the vacant-unit module per scope §7. `VacantUnitInspections` was already a real table
since Phase 2 (`database/tables/04_InspectionTables.sql`), so like every phase since 9, this is
entirely application code - no new SQL.

**A single authorization tier - the simplest of any module so far, and worth naming as its own
category rather than just "smaller Cleaning."** View: any company member. Mutate: the parent
`Inspection`'s own assigned inspector or Admin/Manager, reusing `inspection_service.
ensure_can_edit` directly, no independent carve-out - identical in shape to Phase 11's
`CleaningInspection`. What makes this simpler than even Cleaning, not just simpler than
Maintenance: there's no analogous "config table" the way `CleaningAreas` exists for Cleaning
(`Units` already exist as first-class entities from Phase 6, nothing new needed to enumerate
"what can be vacant"), and the record itself carries no `Status`/`AssignedUserId` at all - no
workflow columns exist on `VacantUnitInspections` in the schema, because it isn't its own
workflow. It's a one-time recorded finding; any follow-up work is scope's own explicit "creatable
directly from any of these questions," which routes into MaintenanceIssues/CleaningInspections as
their own separate records, not a status this table tracks itself.

**Closed a second gap flagged in an earlier phase's own comments, not found fresh this
session.** `app/api/units.py`'s docstring has said, since Phase 6: "realistically an Inspector
doing a walkthrough is often the one who discovers a unit is now vacant - that flow belongs to
the Inspection engine (Phase 8), which will call into unit occupancy updates through its own
service with its own permission story, not through this standalone API. Revisit if Phase 8
needs a different answer here." Phase 8 didn't touch it (it was scoped to the checklist engine,
not vacant units specifically) - Phase 12 is the actual right moment. The mechanism: `unit_
service.update_unit_occupancy` has NO permission check inside itself - Units' standalone API
gates occupancy changes to Administrator/Manager only entirely at the ROUTE level in
`app/api/units.py` (`_manage_units = require_roles(...)` wraps the endpoint, not the service
function). `vacant_unit_service.create_vacant_unit_inspection` calls that same service function
directly, AFTER its own `ensure_can_edit` check has already run - meaning an Inspector (who
could never hit `PATCH /api/units/{id}/occupancy` directly) can still flip a unit to `Vacant`
through this narrower, inspection-scoped path, exactly as the three-phases-old comment
anticipated. Confirmed for real, not just by re-reading the comment: a live Inspector login
(explicitly NOT Admin/Manager) recorded a vacant-unit finding on a real demo unit and its
`OccupancyStatus` genuinely flipped to `Vacant`, checked via a separate real `GET` call
afterward. This is the second time in two phases a service function with no permission check of
its own (the first was `cleaning_service.seed_default_areas_for_property`, called from
`property_service`, though that one needed no check at all rather than a narrower one) has been
deliberately reused by a different, better-scoped caller to give an action its own permission
story - worth treating as a recognized pattern in this codebase now, not a one-off trick.

**Every `BIT` column on `VacantUnitInspections` is nullable with no DB default - genuinely
tri-state, and this was deliberately preserved end-to-end rather than collapsed to a boolean.**
Unlike `MaintenanceIssues.CleaningRequired`/`Urgent` (which default to `0` at the DB layer, so
`False` there really does mean "confirmed no"), `NULL` here means "the inspector didn't check
this," a materially different fact than "checked and it's fine." The model
(`app/models/vacant_unit_inspection.py`), both Pydantic schemas, and the tests all keep this
distinction explicit - a test asserts a never-supplied field comes back `None` in the API
response, not silently coerced to `false`.

**Scope §7's "a maintenance issue should be creatable directly from any of these questions" has
no supporting FK on the actual schema** - `docs/DATABASE.md`'s ERD lists `MaintenanceIssue N──0/1
Unit, Inspection, InspectionResponse` only; no `VacantUnitInspectionId` column exists or was ever
designed. Rather than adding one now (a real schema change this late, for a linkage the existing
`PropertyId`/`UnitId`/`InspectionId` fields on `MaintenanceIssueCreate` already cover in
practice, since a vacant-unit finding has all three in hand), this is satisfied by the EXISTING
`POST /api/maintenance-issues` endpoint - documented as a deliberate interpretive call in
`vacant_unit_service.py`'s own module docstring, the same kind of explicit "here's what this
means and why" note the project has used for every ambiguous scope-vs-schema gap since Phase 6's
"permission to inspect" call. No automatic MaintenanceIssue/CleaningInspection gets created even
when `MaintenanceRequired`/`CleaningRequired` is flagged true on a vacant-unit record - scope
says "creatable," a client-triggered action, not "created," an automatic side effect, and
inventing that automation would be solving a problem scope didn't actually pose.

7 new tests (92 total), all against the real DB: create-as-assigned-inspector with the real
occupancy flip verified via a genuine `GET /api/units/{id}` call (not just asserted from the
create response) and the nullable fields checked to stay `None` rather than `False` when never
supplied, a `UnitId` from a different property rejected 422, an unassigned inspector 403, a
`Submitted` inspection 409, cross-company 404 on the list, a partial `PATCH` proven to leave
other fields untouched, and a photo uploaded through the generic `/api/media` endpoint with
`EntityType=VacantUnitInspection`. One fixture (`occupied_unit_id`) is unusual for this project:
it deliberately mutates real seeded demo data (flips "Flat 1" to `Vacant` so there's something
real for the create action to flip) and restores it to `Occupied` in its own teardown - called
out explicitly in its docstring as the only fixture in this test suite that mutates shared seed
data rather than only adding/removing its own throwaway rows, so a future session doesn't copy
this pattern by default for something that doesn't need it.

**Verified live**: a real Inspector (not Admin/Manager) recorded a vacant-unit finding on a real
demo unit that started `Occupied` → confirmed the response's never-supplied fields came back
genuinely `null` → confirmed the unit's `OccupancyStatus` had actually flipped to `Vacant` via a
separate `GET` → a Bright Spaces admin got 404 on the list → a real photo uploaded via
`EntityType=VacantUnitInspection` appeared in the generic media list → the record's `Notes` was
updated via `PATCH` → everything (the inspection and its 102 snapshot responses, the vacant-unit
record, the media row and file) cleaned up afterward, including manually restoring the demo
unit's `OccupancyStatus` back to `Occupied` so the shared seed data wasn't left mutated for the
next session.

## 2026-08-24 — Phase 13 (Risk Assessments) built, first real SQL Server computed column in the ORM

Built the risk module per scope §19. `RiskAssessments`/`RiskMatrixLevels` were already real
tables since Phase 2 (`database/tables/06_RiskTables.sql`), so like every phase since 9, this is
entirely application code - no new SQL. This phase was different in one specific way though:
it's the first time the ORM had to actually MAP a real DB-computed column, not just describe
plain data.

**`RiskAssessments.RiskScore` is mapped with SQLAlchemy's `Computed("Likelihood * Severity",
persisted=True)`, not a plain `mapped_column(Integer)` - and this was verified with a real
insert before anything else got built on top of it, not assumed to work from reading
SQLAlchemy's docs.** `Computed` tells the ORM to exclude the column from generated INSERT/UPDATE
statements automatically (SQL Server would reject an explicit value anyway - the column is
`AS (Likelihood * Severity) PERSISTED`, computed at the database layer, exactly the "structural
guarantee, not app convention" pattern `docs/DATABASE.md §9.6` calls for). The existing
`db.refresh()` call every other repository's `create_*` function already does (to pick up
server-side defaults like `CreatedAt`) is what actually populates `RiskScore` back onto the
Python object after insert - no new refresh logic was needed, just the right column mapping. A
throwaway script inserted a real `Likelihood=4, Severity=5` row directly against
`InspectIQDb` and confirmed `RiskScore` came back as `20` before `app/services/risk_service.py`
or any route existed - the same "verify the risky part in isolation before building the rest"
discipline this project has applied to every genuinely new mechanism since Phase 2's SQL
gotchas (ANSI_NULLS/QUOTED_IDENTIFIER, filtered index NOT IN, etc.).

**A third distinct authorization shape for this project - two tiers, but NOT the same two tiers
Cleaning uses, and the reasoning is worth keeping precise because the two modules could
otherwise look interchangeable at a glance.** View: any company member (unchanged, every module
so far). Create: Administrator/Manager/Inspector - raising a hazard is scope-equivalent to
Maintenance's "raise an issue" tier. Update: Administrator/Manager ONLY, covering every field
(including `Status` and `ResponsiblePersonUserId`) in one combined `PATCH` - no separate
assign/status endpoints the way MaintenanceIssues has, and critically, NO assigned-inspector
`ensure_can_edit` carve-out the way Cleaning/VacantUnit have. Two independent reasons converge
on the same answer here, either sufficient alone: scope §19 describes no audit-trail requirement
(unlike §18's explicit "Maintenance History" - nothing analogous exists for risk, so there's no
timeline table motivating split endpoints), AND, structurally, `RiskAssessment.InspectionId` is
NULLABLE - a standalone Property-level risk-register entry legitimately has no parent
`Inspection` at all, so `ensure_can_edit`'s whole mechanism (look up the Inspection, check its
assigned inspector) has nothing to run against for that case. Cleaning/VacantUnit could adopt the
Inspection-anchored shape uniformly because their own `InspectionId` is NOT NULL by schema
design - RiskAssessment structurally cannot make the same choice even if it wanted to. Worth
remembering as the concrete counterexample the next time a module superficially resembles an
earlier one: check the actual nullability of the parent-linking FK before assuming the same
authorization mechanism transfers.

**`RiskMatrixLevels` needed real "global default + per-company override" lookup semantics
worked out from scratch, not copied from `InspectionTemplates` despite using the identical
nullable-`CompanyId` mechanism.** `InspectionTemplates`' version is additive: `CompanyId IS NULL
OR CompanyId = @company_id` returns the global templates AND a company's own together, because a
template *list* is naturally a menu of independent options - more choices is strictly fine. A
risk matrix is different in kind: it must be a coherent whole covering the full score range with
no gaps or overlaps, so mixing two leftover global bands with two new company-specific ones
could easily produce nonsense (a score of 7 matching neither a global "Medium 5-9" band nor a
narrower custom one, or matching two bands at once). The correct semantics, once actually
reasoned through rather than pattern-matched from the nearest precedent: a company's own bands
FULLY REPLACE the global default the instant any exist at all (`risk_repository.
get_risk_matrix_for_company` - query the company's own rows first, only fall back to the global
`CompanyId IS NULL` rows if that came back empty). Confirmed with a real test that creates one
company-specific band spanning the whole 1-25 range, verifies a subsequent risk assessment for
that company resolves against it (not the global bands), AND verifies a *different* company's
matrix is completely unaffected - proving the override is scoped correctly, not just present.

**`RiskAssessment`'s media authorization deliberately reuses the SAME function for both view and
mutate - the Property/Unit shape, not the Maintenance/Cleaning/VacantUnit shape** - "any company
member" governs both, even though `risk_service.py`'s own `PATCH` endpoint is Admin/Manager-only.
This is the same "uploading evidence is not the same permission as editing the record" principle
already established for Property/Unit back in Phase 9, applied here for the first time since
then to a module whose own edit bar is narrower than its view bar (Property/Unit's edit bar was
already Admin/Manager-only too, so this wasn't previously a visible distinction from a module
where the parent's mutate check WAS just as broad as view). Confirmed live and in a dedicated
test: the same Inspector who got a genuine 403 trying to `PATCH` a risk assessment successfully
uploaded photographic evidence to that exact record moments later - not a coincidence of two
unrelated permission checks, but the deliberately-designed outcome of the module docstring's own
reasoning.

**`create_risk_assessment` accepts an optional `MaintenanceIssueId` link (the FK exists per
`docs/DATABASE.md`'s ERD, `RiskAssessment N──0/1 ... MaintenanceIssue`) but does NOT let it
independently derive `PropertyId` the way `InspectionId`/`InspectionResponseId` do** - scope
§19's own create-form field list only names Property and Inspection, not MaintenanceIssue, so
the FK is honored (isolation-checked via `maintenance_service.get_issue` if supplied) without
inventing a third priority-ordered derivation path scope never actually asked for. A deliberate,
proportionate stopping point, not an oversight.

16 new tests (108 total), all against the real DB: standalone create with `RiskScore`/
`RiskLevel` checked against two different real score bands (20→Critical, 6→Medium - not just one
example, to prove the matrix lookup itself, not a single lucky number), role-gated create
(Maintenance blocked, Inspector allowed - the create tier, not the narrower update tier),
missing-Property-and-Inspection 422, cross-company 404 on create AND on get, create-from-response
correctly deriving Property/Inspection, an Admin update that changes `Severity` and confirms
`RiskLevel` is genuinely RE-derived rather than left stale from create time, an Inspector getting
403 on update EVEN FOR A RECORD THEY THEMSELVES JUST CREATED (the clearest possible proof this
tier is role-based, not ownership-based - a subtlety worth testing explicitly rather than
assuming from the route gate alone), the global default matrix, the override-replaces-global
behavior (checked two ways: the resolved level on a new assessment, and a second company's
matrix staying untouched), `MinScore > MaxScore` rejected 422, and the Property/Unit-shaped media
test described above.

**Verified live**: real Inspector login created a risk assessment (`Likelihood=4, Severity=4` →
confirmed `RiskScore=16`, `RiskLevel="High"`, matching the global matrix's own bands exactly) →
the same Inspector got a real 403 attempting `PATCH` → a real Administrator update changed
`Severity` and confirmed `RiskLevel` recomputed to `"Low"` (not left at the create-time value) →
a Bright Spaces admin got 404 on the record → the Inspector who couldn't edit the record
successfully uploaded evidence to it → all test data (the assessment, the media row, and its
file on disk) cleaned up afterward, with a direct DB check confirming zero leftover
company-specific `RiskMatrixLevels` rows - the override test's own cleanup genuinely restored
global-default behavior for every company, not just asserted that it did.

## 2026-08-24 — Phase 14 (AI/OCR Meter Reading) built, a real bug caught by its own failing test

Built the meter-reading module per scope §11 - the last phase drawing on this project's real-
computed-column-and-snapshot family of patterns (Phases 2/13) before entering genuinely new
territory: a mock external service call. `MeterReadings` was already a real table since Phase 2
(`database/tables/04_InspectionTables.sql`), so like every phase since 9, no new SQL.

**`IMeterReadingOcrService` mirrors `IMediaStorageService`'s exact local-now/swappable-later
shape (Phase 9)** - a `Protocol` plus a `MockMeterReadingOcrService` that returns scope §11's own
illustrative example value (`18294.6`, confidence `0.87`) without ever inspecting the actual
image bytes, matching scope's explicit "mock provider first" instruction rather than building a
half-real OCR integration prematurely. The mock is wired through the SAME `open_media_stream`
every real caller would use (`media_service.open_media_stream`, then `.close()` in a `finally` -
the Phase 9 file-handle-leak lesson applied here too even though the mock never reads the
stream), so a future real implementation only needs to swap `MockMeterReadingOcrService` for a
genuine API-calling class - nothing about how the stream reaches it changes.

**`PhotoMediaFileId` is a direct 1:1 FK to a single `MediaFiles` row, the first module to depart
from the polymorphic many-photos pattern every prior media-carrying module used unmodified.**
The row still gets created through the exact same `EntityType="MeterReading"` polymorphic
mechanism as everywhere else (Property/Unit/Inspection/MaintenanceIssue/CleaningInspection/
VacantUnitInspection/RiskAssessment) - `PhotoMediaFileId` is just a denormalized "primary photo"
pointer kept in sync on top of that, not a parallel storage mechanism. This was a deliberate,
schema-driven choice, not laziness: a meter reading genuinely has exactly one confirmable photo
(the photo IS the evidence for the reading, scope §11's whole flow revolves around it), unlike
every other module's "attach as many supporting photos as you like" relationship.

**A genuinely hybrid authorization tier for confirm/update - synthesized from the specific
combination of two facts about this module, neither alone dictating the answer.**
`MeterReading.InspectionResponseId` is nullable, structurally identical to `RiskAssessment.
InspectionId` (a meter can legitimately be read standalone, not tied to one specific checklist
question) - that fact alone would point toward Risk's Admin/Manager-only shape. But scope §11's
flow text is explicit in a way Risk's never is: "ask inspector to confirm or correct" names the
inspector, not a manager, as the one who closes the loop on this exact record. `ensure_can_edit_
reading` honors both facts by branching on whether the reading has a parent Inspection to check:
if so, reuse `inspection_service.ensure_can_edit` (assigned inspector or Admin/Manager, Cleaning/
VacantUnit's shape); if not, fall back to Administrator/Manager only (Risk's shape). Neither
existing precedent fit the whole picture alone; this module needed both, conditionally.

**A real bug, caught by an actual failing test the first time this module's tests ran - not
found by re-reading the code afterward.** The first version of `MeterReading`'s media-upload
mutate check in `media_service.py` reused `meter_reading_service.ensure_can_edit_reading`
directly (the confirm/update tier described above), reasoning by analogy from CleaningInspection/
VacantUnitInspection, whose media mutate checks DO reuse their update tier. Running
`test_create_as_inspector_runs_mock_ocr` for the first time produced a genuine `403 Forbidden`
with the message "Only an Administrator or Manager can modify a meter reading not linked to an
inspection" - on a request an Inspector, gated in by the route's own
Administrator/Manager/Inspector role check, was making to CREATE a brand-new record. The cause:
`create_meter_reading` creates the `MeterReading` row, THEN calls `media_service.upload_media` to
attach its defining photo - and at that exact moment, the row is standalone (no
`InspectionResponseId` was supplied in this test) and has no `AssignedUserId`-equivalent, so
`ensure_can_edit_reading`'s fallback branch (Admin/Manager only) rejected the very Inspector who
was legitimately allowed to be here. The fix: the photo attached at CREATE time needs the CREATE
permission (broader, already satisfied by the route gate), not the record's own narrower
CONFIRM/update permission - these are two different actions at two different moments on the same
entity, and reusing one for the other was the actual mistake, not a phrasing detail. Changed
`MeterReading`'s media mutate check to equal its view check (any company member), the same
`RiskAssessment` "uploading evidence isn't the same as editing" shape - confirmed correct because
CleaningInspection/VacantUnitInspection genuinely don't have this problem (their photos are
supplementary evidence attached to an already-fully-created, already-Inspection-linked record,
never as part of an atomic create-and-upload sequence the way MeterReading's is). **Standing
lesson, stated precisely rather than as a vague "be careful": before wiring a media mutate check
to an existing permission function, identify which ACTION on the entity that function actually
gates, and confirm the media attachment is really the same action - not just the nearest
available function on the same service.**

11 new tests (119 total), all against the real DB with readings/media cleaned up per-test
(files actually deleted from `backend/uploads/`): create runs the mock OCR and returns exactly
the expected fixed values with `ConfirmedReading` still `None` (proving the AI value never
auto-becomes confirmed), role-gated create (Maintenance blocked), cross-company 404 on create, an
invalid `MeterType` rejected 422, create linked to a real `InspectionResponse` correctly stores
both the link and (implicitly, by not raising) the property-match validation, cross-company get
404, the photo visible through the *generic* `/api/media` endpoint with the same
`MediaFileId` the create response returned (proving the polymorphic integration end-to-end, not
just at the import level), confirm by the assigned inspector on an Inspection-linked reading
succeeding while confirm by a different, unassigned inspector 403s, confirm on a STANDALONE
reading 403ing for an Inspector but succeeding for an Administrator moments later (both branches
of the hybrid tier exercised in one test, back to back), and a basic list/filter check.

**Verified live**: a real Inspector uploaded a real meter photo via curl, and the mock OCR
returned `AIDetectedReading=18294.6000`/`AIConfidence=0.8700` - matching scope §11's own
illustrative example exactly, confirming the mock's deliberate choice to reuse that value rather
than an arbitrary placeholder pays off in a demo session too → that same Inspector got a real 403
trying to confirm their own just-created standalone reading (the fixed bug, re-confirmed live
after the fix, not just in pytest) → a real Administrator successfully confirmed it → a Bright
Spaces admin got 404 on the record → the photo appeared correctly via a plain `GET /api/media?
entity_type=MeterReading...` call → all test data (the reading, media row, and file) cleaned up
afterward - including, this time, remembering the FK direction (`MeterReadings.PhotoMediaFileId`
references `MediaFiles`, so the reading row must be deleted before its media row, not after - a
real `Msg 547` constraint violation the first cleanup attempt hit, fixed by reordering the two
DELETEs, not by skipping the reference check).

## 2026-08-24 — Phase 15 (Dashboard API) complete

Per scope §23. No new SQL, no new authorization design (view = any company member, the same
"a dashboard has no mutate action" reasoning applied everywhere else) - genuinely the thinnest
phase since Phase 7, exactly as `AI_HANDOFF.md`'s Phase 14 "Next tasks" entry predicted, because
`database/reports/15_DashboardQueries.sql` had already done the real design work back in Phase 2.

- `app/repositories/dashboard_repository.py` - nine functions, each mirroring one query block in
  `15_DashboardQueries.sql` 1:1 (that file's own header comment: "to be lifted directly into
  DashboardRepository methods in Phase 15" - taken literally, not reinterpreted). Built with
  SQLAlchemy Core (`select`/`case`/`func.sum`), not raw `text()` SQL - this project's standing
  convention (no repository anywhere else uses raw SQL) took priority over the header comment's
  literal wording; the *logic* was lifted directly, the *mechanism* stayed idiomatic to match
  every other repository in the codebase. `SUM()` over zero matching rows still returns `NULL` in
  SQL Server (the Phase 2 gotcha), so every aggregate is coalesced with `or 0` in Python -
  `ISNULL(...)`'s exact application-layer equivalent.
- **A real, caught-immediately bug**: the first version used `Property.IsActive.is_(True)`
  (SQLAlchemy's portable boolean-comparison method), which compiles to `WHERE [IsActive] IS 1` -
  valid on backends with a native boolean type, but a hard T-SQL syntax error on SQL Server
  (`Msg 102`, "Incorrect syntax near '1'"), since MSSQL's `IS` only accepts `NULL`/`NOT NULL`.
  Caught immediately by the Phase-5-established habit of sanity-querying a new repository against
  the real DB before writing any route - `app/repositories/property_repository.py` already had
  the fix as a standing pattern (`Property.IsActive == True  # noqa: E712`), just not one this
  session recalled from memory before writing the query fresh; worth remembering explicitly now
  so it doesn't cost a repeat lookup next time a `Boolean` column needs a `WHERE` filter on this
  project.
- The cleaning-grade query is the project's first ORM-mapped `ROW_NUMBER() OVER (PARTITION BY
  ...)` window function (`func.row_number().over(partition_by=..., order_by=...)` inside a
  `.subquery()`) - confirmed working by direct comparison against the raw SQL's own already-tested
  version, not assumed to translate correctly just because SQLAlchemy exposes the API.
- Recent-activity queries join `Property`/`User` directly for `PropertyName`/`InspectorName`
  rather than reusing the existing `vw_InspectionSummary`/`vw_OpenMaintenanceIssues`/
  `vw_ActiveRiskAssessments` views through raw SQL - deliberate, not an oversight: every other
  Response schema in this project returns bare `PropertyId`, not a joined `PropertyName` (the
  frontend is expected to resolve names itself elsewhere), but a dashboard's recent-activity feed
  is explicitly meant to be a human-readable list *without* N+1 follow-up calls (scope §23,
  and the views' own `14_InspectionViews.sql` header: "for list screens and reports"), so this is
  the one place in the API surface that intentionally departs from the ID-only convention.
  `User.FirstName.concat(" ").concat(User.LastName)` used for the joined name, not Python `+` on
  the columns - SQLAlchemy's `.concat()` is the portable, per-dialect-correct way to do this
  (mirrors `IsActive == True` as "the SQLAlchemy-idiomatic form matters, not just 'produces a
  working query on this one backend'").
- `app/schemas/dashboard.py` field names match the SQL column aliases from
  `15_DashboardQueries.sql` (`DueToday`, `OpenCount`, `GradeAOrB`, etc.) directly, same PascalCase-
  matches-source convention every other Response schema in this project already follows - but
  without `ConfigDict(from_attributes=True)`, since a dashboard metric isn't a row from any one
  ORM entity the way every other Response schema's source is.
- 5 new tests (124 total): auth required, a Maintenance-role user (the most restricted role
  everywhere else in this project) confirmed able to view the dashboard, creating a real Urgent
  maintenance issue moves `OpenCount`/`UrgentOrEmergency` by exactly +1 and appears in
  `RecentActivity`, creating a real Likelihood=5/Severity=5 risk assessment computes `Critical`
  and moves `CriticalCount`/`OutstandingCount` by +1, and a Bright Spaces admin's dashboard never
  shows a Northgate-created issue in `RecentActivity` (company isolation, exercised end-to-end
  through the real aggregate queries rather than asserted against a single row).
- **Verified live**: a real Administrator login → `GET /api/dashboard` over actual HTTP returned
  the correct shape and real seeded-data counts (`TotalActiveProperties=3`,
  `PropertiesRequiringAttention=1` matching the one demo property with an overdue
  `NextInspectionDue`) → confirmed `GET /api/dashboard` with no token returns a real 401 → server
  stopped cleanly.

## 2026-08-24 — Phase 16 started: React frontend scaffold + auth

Backend Phases 1-15 (the entire scope backend surface) were complete and pushed before this
started. The owner explicitly chose to push to GitHub and start Phase 16 immediately rather than
pause for review (`AskUserQuestion` offered both) - the "phase-gate at natural checkpoints"
convention from 2026-08-23 doesn't mean pausing by default, it means offering the choice at a
real checkpoint and following what the owner picks.

**Mirrored PropertyManager's frontend architecture directly**
(`C:\Users\shmil\Projects\property-management-system\frontend`), file-for-file where InspectIQ's
own schema/backend allows, rather than designing a new pattern from scratch - `PROJECT_PLAN.md
§6`'s folder structure (`api/`, `services/`, `contexts/`, `routes/`, `components/`, `layouts/`,
`pages/`) already named this as the plan, but reading PropertyManager's actual working code (not
just its own docs) surfaced concrete, validated implementation details worth reusing directly:
the memory-access-token / sessionStorage-refresh-token split with a documented XSS-exposure
tradeoff, the refresh-and-retry Axios interceptor with a shared in-flight-refresh promise (so N
parallel 401s trigger one refresh call, not N), `ProtectedRoute`'s nested-route + optional
`allowedRoles` shape, and the CSP-in-`index.html` pattern with its exact `%VITE_X%`
env-replacement mechanism.

**Two deliberate departures from the mirrored pattern, confirmed by reading InspectIQ's own
backend code rather than assumed identical**: (1) `app/schemas/auth.py`'s `LoginRequest` uses
lowercase `email`/`password` fields, unlike every other InspectIQ request body's PascalCase
(matching DB columns) AND unlike PropertyManager's own PascalCase `Email`/`Password` - the
frontend sends lowercase for login specifically, confirmed against the actual schema file, not
guessed from the other pattern. (2) `app/api/auth.py` has no logout endpoint at all (only login/
refresh/me) - `AuthContext.logout` is purely client-side, no wrapper call, documented in
`authService.js`.

**Real, reproduced CSP bug (not a hypothetical) found and fixed**: Vite's dev server injects
live CSS as an inline `<style>` tag for HMR - not a real external stylesheet the way `vite build`
emits (confirmed both ways: a strict `style-src 'self'` produced a genuine "Applying inline style
violates ... style-src" console error AND `getComputedStyle` on a real button showed the
browser's default UA styling, not anything from `global.css` - the page was functionally
unstyled, not just noisy in the console). Fixed with `frontend/.env.development` (`style-src
'self' 'unsafe-inline'`) vs. `.env.production` (`style-src 'self'`, unchanged) feeding a new
`%VITE_CSP_STYLE_SRC%` token in `index.html` - confirmed the production side needs no relaxation
by actually running `npm run build` and inspecting `dist/index.html`, which has a real `<link
rel="stylesheet">`. **A second, related but NOT fixable gap was found the same way and
documented rather than quietly worked around**: Vite's dev server also prepends an inline
React-Refresh-preamble `<script type="module">` at the literal top of `<head>`, unconditionally
ahead of this file's own authored tag order (confirmed by `fetch('/')`-ing the page's own served
HTML from within the browser) - a `<meta>`-delivered CSP cannot govern anything parsed before its
own position in the document, so `script-src 'self'` never actually covered this one script.
Confirmed this doesn't exist in a production build at all (`dist/index.html` has no such tag), so
it's Vite's own trusted dev-only tooling, accepted as a known limitation rather than something to
route around by reordering source tags (which wouldn't work anyway - Vite prepends
unconditionally regardless of authored order).

**A real CVE fixed proactively, not left for a future security-review phase to find**: `npm
audit` flagged `react-router-dom` 6.x (the version PropertyManager's own frontend still pins) for
a moderate open-redirect advisory. Bumped to `^7.18.2` before writing any more pages on top of
it - cheaper as the very first commit than after 18 more pages depend on the API. Confirmed the
classic component-routing API this scaffold actually uses (`BrowserRouter`/`Routes`/`Route`/
`Outlet`/`NavLink`/`useNavigate`) is unchanged between v6 and v7 by running the full login →
dashboard → reload-session-restore → logout → 404 flow afterward, not by trusting the changelog
alone. `npm audit` now reports 0 vulnerabilities.

**One responsive layout, not `PROJECT_PLAN.md §6`'s eventual separate desktop/mobile layout
components** - `MainLayout`/`Header`/`Sidebar` are already split into their own files
specifically so that split is a later two-file change when a real "field" vs. "management"
navigation difference actually exists to express; with only Dashboard built so far there's
nothing to differentiate yet, so building the split prematurely would be guessing at a shape
before there's a second page to inform it.

**A real preview-tooling gotcha, worth remembering for any future InspectIQ frontend session**:
the Browser-pane preview tooling reads `.claude/launch.json` from the *primary working
directory* (`KnowledgeWork` in this session), not from a `.claude/launch.json` inside the
InspectIQ repo itself - a first attempt at a repo-local launch config was silently ignored in
favor of KnowledgeWork's pre-existing `frontend` entry (which pointed at PropertyManager's
frontend, not InspectIQ's - confirmed by the served page's title reading "PropertyManager"
instead of "InspectIQ"). Fixed by adding a distinctly-named `inspectiq-frontend` entry to
KnowledgeWork's own `.claude/launch.json` instead, alongside the pre-existing `frontend` one, and
deleting the unused repo-local file.

**Verified live, through the real running UI** (real `uvicorn` backend + real `npm run dev`
frontend, not just component-level checks): login as a real Northgate Administrator rendered
real dashboard data matching the backend's own response exactly → a full page reload preserved
the session via a real `POST /api/auth/refresh` call, no re-login needed → logout redirected to
`/login` for real → direct navigation to `/` while logged out redirected to `/login` → an unknown
URL rendered the 404 page → a second login as an Inspector (a role Dashboard doesn't restrict)
also worked → both servers stopped cleanly. Mobile-viewport verification hit a real environment
limitation worth remembering, not an app bug: this session's Browser pane wasn't compositing
frames (confirmed by repeated screenshot/click-by-coordinate timeouts), which made
`getBoundingClientRect`/`getComputedStyle` reads on the off-canvas sidebar unreliable
*specifically right after* a click interaction while resized - the underlying CSS/React logic
was independently confirmed correct through facts that don't depend on compositing: the
`sidebar--open` class toggling correctly on click (checked via `className` and a real DOM
`.click()` dispatch), the CSS rule itself confirmed via direct CSSOM inspection (correct
selector, correct specificity, correct source order relative to the base rule), and the desktop
breakpoint confirmed correct on a *fresh* (non-post-interaction) load
(`position: sticky`/`left: 0`/hamburger hidden/roles shown, all matching `min-width: 768px`).
**Standing lesson for future sessions using this same Browser-pane tooling**: if
`getBoundingClientRect`/`getComputedStyle` produce a value that contradicts CSS you've already
confirmed correct via CSSOM inspection, check whether the pane is actually compositing
(screenshot/click-by-coordinate both timing out is the tell) before concluding it's a real app
bug - a fresh page load's measurements were reliable here even when post-interaction ones
weren't.

## 2026-08-24 — Properties + Units frontend module (Phase 16 continued)

The first full List/Detail/Form module - Dashboard had no create/edit shape to prove the
pattern against. Ported PropertyManager's shared component library into
`frontend/src/components/` (PageHeader, DataTable, Pagination, SearchInput, FilterPanel,
SelectField, FormField, FieldShell, DateField, ErrorMessage, EmptyState, ConfirmationDialog,
Toast, StatusBadge) rather than building bespoke UI for this one module - these are now real,
reusable infrastructure for every future module's frontend, not a one-off. Read PropertyManager's
actual component source (not just recalled its shape) to port it faithfully, the same "read the
real code, don't guess from memory" discipline as the earlier scaffold+auth session.

**A real design decision, not an oversight**: Units have no list/detail/form pages of their own.
Two independent signals pointed the same direction: scope's own named page list
(`prompts/frontend_prompt.md`, Prompt 16's verbatim text) names "Properties, Property Details"
but no separate Units page, and the backend's own routes are nested under a property
(`/api/properties/{id}/units`, `/api/units/{id}`), never a flat `/api/units` collection endpoint.
So unit management (add, inline-edit UnitNumber/Floor/TenantOccupierName/Notes, change
OccupancyStatus) lives entirely inside `PropertyDetailPage` as an embedded section with its own
small inline-edit-row and add-unit-form sub-components, matching the backend's own nesting
rather than inventing a flat frontend module the scope/API don't have.

**`AlarmAccessCode` handled with a bit more care than a plain text field, given
`docs/DATABASE.md §10.4` flags it as a real, documented, not-yet-mitigated plaintext-storage
risk**: `PropertyFormPage` uses `type="password"` with a show/hide toggle, and
`PropertyDetailPage` masks it behind a "Show" button by default rather than rendering it in the
open. This doesn't fix the backend's plaintext storage (out of scope for a frontend module) - it
just means the first UI to actually touch this field doesn't gratuitously make the exposure
worse by leaving it sitting in plain view on screen when it doesn't have to.

**Verified live, through the real running UI, as a real Administrator** (not just reading the
code and assuming it works): created a property through the full 17-field form → added a unit →
changed its occupancy status and confirmed the UI re-rendered from the real API response (not
just local optimistic state) → inline-edited the unit's tenant name, persisted → edited the
property itself (name + status) → deactivated it via the confirmation dialog → confirmed it
correctly disappeared from the default list and reappeared with "Include deactivated" → switched
to a real Bright Spaces Administrator and confirmed a real "Property not found." on the exact
same URL (cross-company isolation exercised through the actual UI navigation, not just curl
against the API directly) → confirmed no page-level horizontal scroll at a 375px mobile
viewport, the table scrolling within its own `.data-table-wrapper` instead (the mobile-first
"wide content scrolls in its own container, not the page" rule applied for the first time to
real tabular data, not just the dashboard's stat cards).

**A real cleanup gotcha, not a bug**: hard-deleting the manually-created test property hit
`FK_CleaningAreas_Properties` on the first attempt - `property_service.create_property` (Phase
11) auto-seeds 3 default `CleaningAreas` for every new property, which this session's own memory
of "Properties has no soft-delete-only trigger" didn't account for on the first try. Fixed by
deleting the `CleaningAreas` rows before the property, same FK-ordering discipline every backend
phase's own test cleanup already uses (e.g. MeterReadings→MediaFiles from the Phase 14 entry) -
confirmed the failed first attempt rolled back atomically (nothing was left half-deleted) before
retrying with the corrected order.

## 2026-08-25 — Inspection Templates frontend module (Phase 16 continued)

Read-only end to end, matching the backend's own scope exactly (`app/api/inspection_templates.py`'s
module docstring: template authoring is "eventually," Phase 8's inspection engine is what
actually needs these two endpoints to exist). No `CAN_MANAGE_INSPECTION_TEMPLATES` constant, no
form page, neither route nested under a role-narrowing `ProtectedRoute` - the simplest module
shape yet, correctly kept that simple rather than adding CRUD scaffolding nothing asked for.

The list page shows scope as "Global default" vs. "Company-specific" derived from
`CompanyId === null` - the exact same nullable-`CompanyId` signal the backend's own repository
uses for the "global default + per-company override" pattern (`docs/AI_MEMORY.md`'s Phase 7
entry), read directly off the response rather than the frontend inventing its own notion of
what makes a template "global."

**The detail page's real design decision**: 21 sections and 102 questions for the one seeded
template is a lot to render flat, but this is read-only reference data, not a workflow needing
custom interaction - native `<details>`/`<summary>` per section gets free, accessible collapse/
expand with zero JS state, correctly judged as the right tool here specifically because nothing
on this page needs to be more interactive than "let me collapse what I'm not looking at." (The
actual Inspection engine wizard, Prompt 17, is exactly the case where that judgment would flip -
noted for when that page gets built.)

**Verified live, through the real running UI**, not just assumed from reading the schema: real
Administrator login → the real "Monthly Property Inspection" template listed correctly → detail
page's own computed totals (21 sections, 102 questions, summed client-side from the nested
response) matched → expanded one real section (Electricity Meter) and confirmed all 3 of its
actual questions rendered with the correct `AnswerType` values (`METERREADING`/`YESNO`/
`CONDITION` - matching `09_Constraints.sql`'s CHECK list exactly, not a guessed enum) and the
correct boolean flags per question → every `/api/inspection-templates*` request in the network
log came back a real 200 → confirmed no horizontal overflow at 375px mobile width.

A frontend dev server left running from a prior session (started for the owner to log in and
explore locally) was still up on port 5173 outside the preview tool's own process tracking -
`preview_start` correctly refused to reuse it as a managed dev server (port already held by a
process it doesn't own), so verification connected to it directly via `preview_start` with a
plain `url`, the same way any already-running external server is used, rather than restarting
anything the owner might still have been using.

## 2026-08-25 — Inspection engine wizard planned (Phase 16 continued)

Before writing any code, the owner asked to talk through the design - the right call, since
Prompt 17 itself calls this "the most important screen in the application" and it's a
genuinely different shape from every module built so far (List/Detail/Form doesn't apply; it's
a stateful multi-step flow touching five backend modules at once).

**A real discovery that shaped the whole plan, not assumed**: reading
`database/seed/12_SeedInspectionTemplate.sql`'s own file header surfaced that five sections
(Communal Cleaning, Units, Vacant Units, Maintenance, Risk Assessment) were deliberately built
as "gateway" sections back in Phase 2 - they carry almost no real checklist questions because
their substance lives in dedicated tables/flows (`CleaningInspections`, `VacantUnitInspections`,
`MaintenanceIssues`/`RiskAssessments` "creatable from any question"). Confirmed by reading the
actual seeded question text: "All identified vacant units inspected using Add Empty Unit?" is
literally a confirmation prompt, not a real checklist item. This meant the wizard does NOT need
to loop through units/cleaning-areas as regular questions - it needs two GLOBAL quick-actions
("Add Empty Unit," "Grade Cleaning Area") available throughout the inspection, separate from the
per-question actions (Photo/Video/Create Maintenance/Create Risk) scope names for every
question. Finding this in the backend's own design comments, rather than guessing from the
scope text alone, is what let the sub-phase plan (see `AI_HANDOFF.md`'s "Next tasks") separate
"per-question actions" (C) from "global gateway actions" (E) as genuinely different kinds of
work instead of conflating them.

**A second real gap found while planning, not while building**: `GeneralNotes`/
`OverallCondition`/`OverallRiskRating` exist on `Inspection`/`InspectionDetailResponse` (Phase
8) but had no endpoint to ever set them - the Inspection Review screen (sub-phase F) would have
had nothing to actually do with those fields otherwise. The owner chose to fix this now (a small,
well-scoped `PATCH /api/inspections/{id}` addition, see the Phase 16 handoff entry above) rather
than defer it - the right call, since discovering it later mid-Review-page-build would mean
either a mid-task backend detour or shipping a Review screen that silently can't do what it's
for.

**Three concrete decisions confirmed with the owner, not decided unilaterally**: (1) add the
`PATCH /api/inspections/{id}` endpoint now; (2) `Condition`-type answers render as curated
preset buttons (Good/Fair/Poor) despite the backend leaving the field genuinely freeform -
optimizes for the "few taps as possible" requirement scope states explicitly, at the cost of a
frontend-only vocabulary the backend doesn't enforce (still just plain text once submitted, so
this doesn't foreclose a different value ever being sent); (3) the six-sub-phase build order
(A: core wizard → B: photos → C: maintenance/risk quick-create → D: meter reading → E: gateway
actions → F: review/submit), each independently committable, rather than attempting the whole
wizard as one page.

**Explicitly out of scope for this entire effort**: "Inspection Report" (PDF) - scope names it
as its own page, but it depends on backend Phase 17 ("PDF reports," `PROJECT_PLAN.md §11`),
which doesn't exist. Submit is as far as sub-phase F goes; report generation is a distinct,
later backend-then-frontend phase.

**"Failed" status badge design, decided while planning rather than left ambiguous for
implementation time**: only `PassFail` answers with `AnswerText === "Fail"` get the Failed
badge - the one answer type with a real, DB-enforced (well, service-enforced -
`_VALID_PASSFAIL` in `inspection_service.py`) failure value. `Condition`'s freeform values
(even the "Poor"/"Fair"/"Good" preset from decision #2 above) deliberately do NOT drive a
Failed badge - that would mean inventing a "Poor means failed" rule that exists only in this
frontend's own preset button labels, not anywhere the backend actually defines or enforces it.

## 2026-08-25 — Inspection engine Sub-phase A built and verified live

The core wizard (Inspection List, Start Inspection, Sections screen, Question screen) from the
plan discussed earlier the same day - see the entry above for the design. Two real problems
were found only by actually running it against a real inspection, not by reading the code back:

**Bug: "Failed" badge outlived the answer it was attached to.** The backend allows
`IsNotApplicable=true` and a stale `AnswerText="Fail"` to coexist on the same response (marking
something N/A doesn't clear a prior answer) - confirmed live by marking a real `PassFail="Fail"`
question Not Applicable and watching the Failed badge stay lit. Fixed by making the two states
mutually exclusive in the DISPLAY only (`!response.IsNotApplicable && isFailed(response)`) -
the backend's data model is unchanged and correct as-is; a stale Failed badge next to a
"Marked as Not Applicable" message would have actively misled whoever reads it next, not just
looked untidy.

**Robustness fix: blur-only autosave isn't good enough for a field on a phone.** The original
design saved Text/Number/Notes fields on blur, matching a common desktop-web pattern. Verifying
this live surfaced a hard blocker for testing it that way: this session's Browser-pane tooling
does not reliably deliver `blur`/`focusout` events for programmatic `.focus()`/`.blur()` calls,
confirmed by attaching temporary listeners that never fired despite `document.activeElement`
provably changing - a different manifestation of the same "pane not compositing" class of
limitation documented in the 2026-08-24 entry (CSS transform reads going stale after
interaction). Rather than treating this as purely a testing inconvenience to route around, it
raised the real question of whether blur is trustworthy for the ACTUAL target usage (an
inspector on a phone) - and it isn't: backgrounding the app mid-inspection or an OS keyboard
dismissal doesn't reliably fire blur either. Added `utilities/useDebouncedCallback.js` -
Text/Number/Notes now save 700ms after the last keystroke as the PRIMARY path, with an
immediate flush on blur as a fallback, not the only trigger. Confirmed this actually works (not
just "should work"): typing into the Notes field and waiting, with no blur ever triggered at
all, produced a real `PATCH` with the typed text roughly 700ms later.

**Standing lesson reinforced**: the same environment limitation that broke CSS-transform
verification on 2026-08-24 broke blur-event verification here too, in a different guise. Both
times, chasing the apparent test failure with alternative verification methods (CSSOM
inspection then; onChange-based fields that don't depend on blur, then a temporary listener
that proved blur genuinely never fires, now) - rather than either trusting a broken test result
or giving up on verifying - is what surfaced the real design improvement (the debounce fix) that
a blur-only implementation would have shipped without.

**Verified live, thoroughly, after both fixes**: every plain answer type exercised against a
real inspection with real data - `YesNo`/`PassFail` button taps saved instantly and flipped the
Answered badge; a `PassFail="Fail"` answer showed Failed, and marking it Not Applicable
correctly hid Failed (the fix, re-confirmed); `Condition="Poor"` showed Answered with NO Failed
badge (confirming the deliberate non-heuristic from the earlier planning session); a `Date`
question saved on change; `Notes` saved via the new debounced path with zero blur events
involved; a `MeterReading` question showed the honest "coming in a later update" placeholder
while N/A/Notes stayed fully usable; Previous/Next correctly crossed a section boundary in both
directions; the Sections screen's overall `3.9% complete (4/102)` exactly matched the real
answers given AND the backend's own `CompletionPercentage`; a Viewer got every control disabled
plus a "view only" notice and was blocked from `/inspections/new` entirely; a Bright Spaces
Administrator got a real "Inspection not found." on the same inspection ID; no page-level
horizontal overflow at 375px; all test data (the inspection and its 102 snapshot responses)
cleaned up from the real DB afterward.

## 2026-08-25 — Inspection engine Sub-phase B built, a real CSP bug caught by live verification

Photo/Video per question - the frontend's first file-upload UI, per the Sub-phase plan
(2026-08-25 entry above). `services/mediaService.js` wraps `/api/media` (list/upload/download-
as-blob/delete); `components/MediaAttachments.jsx` is a generic `entityType`/`entityId`/
`editable` component, deliberately NOT named or scoped to InspectionResponse - Sub-phases C/E's
Maintenance/Risk/Cleaning quick-creates will need the identical upload/view/delete UI against a
different entity, so this is built once as shared infrastructure, not re-ported per module (the
same reasoning that produced the shared component library in Phase 16's first frontend commit).
Wired into `InspectionQuestionPage.jsx` below Notes, using the page's existing `editable`
variable - no new authorization concept, since the backend's own `media_service.py` already
gates InspectionResponse uploads through `inspection_service.ensure_can_edit` (Phase 9).

**Deliberate scope call, not a gap**: no AllowsPhoto/RequiresPhoto gating. `InspectionResponseSchema`
doesn't carry those question-level flags in its frozen snapshot (only QuestionText/SectionName/
AnswerType are, per the Phase 1 §13.1 sign-off), and `inspection_service.py`'s submit gating never
checks them either - confirmed by grepping the service file before writing any frontend code, not
assumed. The backend treats "attach evidence" as available on every question uniformly, so the
component does too, rather than fetching the live template just to decide whether to render
itself.

**A real, reproduced CSP bug, caught only by live verification, not by reading the code back**:
`GET /api/media/{id}/download` requires the same Bearer token as every other request (Phase 9),
so a plain `<img src="https://...">` can't load a thumbnail directly - the design fetches each
photo as an authenticated blob and renders it via `URL.createObjectURL`. The original CSP
(`img-src 'self' data:`, no `media-src` at all, `frontend/index.html`) was written before any
component needed `blob:` URLs and simply didn't allow for them. Every thumbnail failed silently
in the DOM (no visible error banner - just a broken image) until the browser console was checked:
a genuine "Loading the image 'blob:...' violates ... img-src" CSP violation, and
`img.naturalWidth` staying `0` despite `img.complete` being `true`. Fixed by adding `blob:` to
`img-src` and adding a new `media-src 'self' blob:` directive (for the `<video>` tag videos will
use) - `connect-src` deliberately did NOT get `blob:` added, since loading an `<img>`/`<video>`
element's `src` isn't a fetch/XHR call `connect-src` gates at all; only this session's own ad-hoc
diagnostic `fetch(img.src)` calls needed that (and were discarded, not shipped).

**Verified live, end to end, against a real inspection** (question `InspectionResponseId`, not a
mock): uploaded two real photos (one hand-built PNG, one canvas-generated one, to rule out "my
test file was invalid" before concluding it was a CSP bug) - both initially failed to decode
(`naturalWidth: 0`) with the original CSP, both decoded correctly (`naturalWidth: 20` and `1`)
after the fix, confirmed via direct DOM inspection, not just "no error shown." Deleted one via the
confirmation dialog (correct filename shown, real `DELETE` returning `204`, thumbnail and its
object URL removed from the DOM). Confirmed session persistence: a full hard page reload (not
just client-side navigation) correctly restored the session via the stored refresh token and
right back to the same question, with the previously uploaded photo still attached and still
rendering. Confirmed the error path, not just the happy path: after the test inspection's
`InspectionResponses` were deleted from the DB (as part of test cleanup), a follow-up upload
attempt against the now-nonexistent response correctly surfaced "Inspection response not found."
inline, with no crash and no orphaned upload. Confirmed no page-level horizontal overflow at
375px with a photo attached. All test data (the inspection, its 102 snapshot responses, and both
media rows/files) cleaned up afterward - the media rows specifically confirmed clean via the
app's own delete flow first, with a DB-level check afterward for orphans.

## 2026-08-25 — Inspection engine Sub-phase C built, a real authorization distinction found by reading the service code first

Create Maintenance Issue / Create Risk quick-create modals, per the Sub-phase plan. New
`services/maintenanceService.js`/`riskService.js` (one function each, `createMaintenanceIssue`/
`createRiskAssessment` - the full Maintenance/Risk Register modules aren't built yet, so nothing
else was needed), `components/Modal.jsx` (a small shared backdrop/Escape shell reusing
ConfirmationDialog's CSS, so the two new forms don't duplicate that plumbing), and
`components/CreateMaintenanceIssueModal.jsx`/`CreateRiskAssessmentModal.jsx`. Genuinely minimal
fields (Title/Category/Priority/Description; Hazard/Likelihood/Severity/Notes) - only
`InspectionResponseId` is sent as linkage, since both backend services derive Property/
Inspection/Location themselves. `constants/riskOptions.js` uses `docs/SCOPE.md` §19's own exact
Likelihood/Severity scale text (1 Rare/2 Unlikely/.../1 Insignificant/2 Minor/...), not an
invented one - checked the scope document for this before writing a labeling scheme from
scratch.

**A real authorization distinction, caught by reading the two service functions BEFORE wiring
the frontend gate, not by copying Sub-phase B's `editable` precedent**: it would have been
natural to gate these two new buttons the same way Photo/Video is gated (`editable` - the
assigned-inspector-or-Admin/Manager rule). But `maintenance_service.create_issue`/
`risk_service.create_risk_assessment` resolve the inspection via `inspection_service.
get_inspection` - a VIEW-level lookup, confirmed by reading both functions line by line, never
`ensure_can_edit`. So any Administrator/Manager/Inspector at the company can raise an issue or a
risk against ANY response, not just the inspector assigned to that specific inspection - a
Manager reviewing someone else's in-progress inspection, or another qualified person who
happens to notice something, can legitimately flag a hazard even though they can't touch the
response's own answer. This produced a new `canRaiseIssues` computed once in
`InspectionWizardLayout.jsx` (any `CAN_CONDUCT_INSPECTIONS` role, unconditioned on
"assigned to this inspection"), separate from `canEdit`. **Standing lesson reinforced** (same
shape as Phase 11's "a new module resembling a previous one doesn't mean copying its
authorization shape" and Phase 14's "verify which action a permission check actually gates"):
the fact that two features sit on the same page and touch the same InspectionResponseId does not
mean they share an authorization boundary - each backend service call needed independent
verification.

**Verified live, end to end, against a real inspection**: created a real Maintenance Issue
(Title pre-filled from the question text as a small "few taps" nicety, Category required) -
confirmed via direct DB query that PropertyId/InspectionId were correctly derived server-side
and Location auto-filled to `"{SectionName} - {QuestionText}"` exactly as
`maintenance_service.py` documents. Created a real Risk Assessment using scope §19's own worked
example (Likelihood=4, Severity=5) - confirmed `RiskScore=20`/`RiskLevel=Critical` both in the
success toast and via a direct DB query, matching the scope document's own stated 17-25=Critical
band. Confirmed native HTML5 `required` validation blocks an empty Category/Likelihood/Severity
selection before the form's own JS validation even runs (an empty-string placeholder `<option>`
correctly fails `checkValidity()`) - matching every other required `SelectField` in this
codebase, not something this sub-phase needed to add. Confirmed a Viewer (not in
`CAN_CONDUCT_INSPECTIONS`) sees neither button. All test data (the inspection, its 102 snapshot
responses, the maintenance issue, and the risk assessment) cleaned up from the real DB
afterward.

**A testing-tooling note, not an app bug, worth remembering for future live-verification
sessions**: `computer.left_click` by coordinate/ref intermittently failed to actually trigger a
button's click handler in this session (silently - no error, just no state change), while
`element.click()` via `javascript_tool` worked reliably every time on the same elements.
Suspected cause: a mismatch between the tool's reported coordinate frame and the page's actual
layout after `resize_window` calls earlier in the session. Switched to JS-based `.click()` for
the remainder of this session's verification once this was noticed, and confirmed a "no visible
change after clicking" result should be checked with a coordinate-independent method before
concluding the underlying app feature is broken - it wasn't, twice, before this was diagnosed
correctly.

## 2026-08-25 — Inspection engine Sub-phase D built: MeterReading's photo → mock OCR → confirm flow, a third authorization shape found in one control

The `MeterReading` answer type's own flow (scope §11), wired to `/api/meter-readings` - the last
of the five deferred answer-type placeholders from Sub-phase A. `services/
meterReadingService.js` (list/create/update) and `components/MeterReadingControl.jsx`, a real
state machine (no reading yet → capture form; unconfirmed → AI value + Confirm form; confirmed →
value + "Correct this reading" reopen), not three separate always-visible sections.

**A small, deliberate backend addition, found necessary while designing the frontend, not
scope creep**: the Question screen needs to know whether a `MeterReading` already exists for
THIS specific `InspectionResponseId` (to decide which of the three states above to render), but
`GET /api/meter-readings` had no way to filter by it, and `InspectionResponseSchema` carries no
pointer back to a `MeterReadingId` at all (`docs/DATABASE.md`'s ERD only points the other way).
Added `inspection_response_id` as an optional query param, threaded through
`app/api/meter_readings.py` → `meter_reading_service.list_meter_readings` →
`meter_reading_repository.list_meter_readings` (one more `.where()` clause). One new backend
test (`test_list_filtered_by_inspection_response_id`, mirroring `test_create_linked_to_
inspection_response`'s fixture setup), full suite re-run (130 tests) clean before touching the
frontend. Same shape as the `PATCH /api/inspections/{id}` addition during Sub-phase A's own
planning - a real frontend need surfacing a genuine, narrowly-scoped backend gap mid-Sub-phase,
not a sign of poor upfront planning.

**A THIRD distinct authorization shape inside a single control, confirmed by reading
`meter_reading_service.py` line by line before wiring either half** (the same discipline Sub-
phase C's two modals used, now proven out a second time on a harder case): CREATE (taking and
uploading the photo) uses `canRaiseIssues` - `create_meter_reading` has no `ensure_can_edit`-
style check at all, so any Administrator/Manager/Inspector can do it. CONFIRM (accepting or
correcting the AI value) uses `editable` - `update_meter_reading` calls
`ensure_can_edit_reading`, which for an Inspection-linked reading is exactly the same
assigned-inspector-or-Admin/Manager rule Photo/Video uses. Both gates live in the same
component, on the same record, and genuinely differ - `MeterReadingControl.jsx` takes both
`canCreate` and `canConfirm` as separate props rather than collapsing them into one, and its own
header comment documents which backend function each maps to. **Standing lesson, now confirmed
three times this session** (Sub-phase C's two modals, this): never assume a new create-adjacent
action shares its authorization boundary with the answer-editing action already on the same
page, even when they visually sit right next to each other - read the specific service function.

**Closed a real, previously-open gap, not something scope explicitly asked for but a clear
consequence of the existing design**: before this Sub-phase, a `MeterReading` question could
never contribute to `CompletionPercentage` at all - `_is_answered` (Phase 8) only checks
`AnswerText`, and nothing ever set it for this answer type. Confirming a reading now ALSO calls
the existing generic `PATCH .../responses/{id}` with `AnswerNumber` - `_normalize_answer`
(Phase 8) already auto-derives `AnswerText = str(AnswerNumber)` for exactly this situation (the
same mechanism the plain `Number` answer type already relies on), so no backend change was
needed, only the frontend wiring the two calls together (`onConfirmed` → the parent's existing
`save()`). Deliberately wired at CONFIRM time only, not at photo-upload/create time - an
unconfirmed AI-detected value isn't "the answer" yet, the UI-level extension of Phase 14's own
principle that the AI value must never silently become the confirmed one.

**Verified live, end to end, against a real inspection navigated to the seeded "Electricity
Meter" section**: the section-name-based MeterType guess correctly pre-selected `Electricity`
with no manual selection needed. Uploaded a real photo → the mock OCR returned its own fixed
example value (`AIDetectedReading=18294.6000`, `AIConfidence=0.87`, matching scope §11's text
exactly) → the question's badge correctly stayed "Unanswered" (not yet confirmed) → confirmed a
DELIBERATELY DIFFERENT corrected value (`18300.5`, not just accepting the AI value verbatim, to
prove the correction path and not just the happy-path accept) → badge flipped to "Answered" →
the Sections screen's completion moved to `1/102` overall and `1/3` for Electricity Meter →
confirmed via a direct DB query that `InspectionResponses.AnswerText`/`AnswerNumber` were both
correctly synced to `18300.5000`. Confirmed a Viewer sees the photo and both AI/confirmed values
(view has no role restriction) but neither the initial capture button nor "Correct this
reading". No horizontal overflow at 375px. All test data (the inspection, its 102 snapshot
responses, the meter reading, its media row, and the actual file on disk) cleaned up afterward -
the cleanup order itself surfaced a real (expected) FK: `MeterReadings.PhotoMediaFileId`
references `MediaFiles`, so the reading row must be deleted before its media row, not after.

## 2026-08-25 — Inspection engine Sub-phase E built: the two "gateway" quick-actions, no backend changes needed this time

"Add Empty Unit" and "Grade Cleaning Area" - the two global quick-actions the "gateway sections"
discovery (this date's earlier planning entry) identified as necessary, since the seeded
template's "Vacant Units"/"Communal Cleaning" sections only ask the inspector to CONFIRM these
were recorded elsewhere, not answer regular checklist questions. Placed on
`InspectionSectionsPage.jsx`, not any one question screen - the first sub-phase to add UI outside
`InspectionQuestionPage.jsx` itself. Unlike every other sub-phase this session, no backend
addition was needed - both `POST /api/inspections/{id}/vacant-unit-inspections` and
`POST /api/inspections/{id}/cleaning` already existed exactly as needed from Phases 11/12.

**`AddEmptyUnitModal.jsx` uses scope §7's FULL field list, not a trimmed "minimal fields" set
like Sub-phase C's modals** - a deliberate, considered departure from that precedent, not an
inconsistency: Sub-phase C's Maintenance/Risk fields were incidental detail-capture with a
whole dedicated module still to come; this modal IS the actual, only planned creation surface for
a vacant-unit record inside this wizard (the eventual standalone "Vacant Units" page, per Phase
16's own remaining-pages list, is a management/list view of existing records, not a second
creation path) - so the real checklist content (11 Yes/No/Not-checked tri-state fields, per
scope's own text) belongs here now, not deferred to a page that will never itself be the primary
way one gets created. A small local `TriStateRow` renders each check as three buttons, reusing
the `.answer-button`/`.answer-buttons` CSS the plain-question YesNo/PassFail answer types already
use - visual consistency for free, not new styling invented for this one form.

**Confirmed independently, not assumed from precedent**: both `vacant_unit_service.
create_vacant_unit_inspection` and `cleaning_service.create_cleaning_inspection` call
`inspection_service.ensure_can_edit` - so both gateway create buttons are gated on `editable`,
the SAME tier Photo/Video uses, unlike every "create" action from Sub-phases C/D (Maintenance/
Risk/MeterReading-photo), which had no such check. This is genuinely a fourth data point on the
same standing lesson (never assume a create-adjacent action's authorization boundary from a
different create action, even on the same page) - it just happened to land on `editable` this
time rather than `canRaiseIssues`, confirmed by reading both service functions rather than
guessing from the fact that they're both "create" actions like Sub-phase C/D's were.

**A real CSS gap, found by reasoning about the new form's size BEFORE it ever ran, then confirmed
with an actual measurement, not left as a hunch**: `.dialog` (shared by ConfirmationDialog and
every quick-create modal since Sub-phase C) had no `max-height` or `overflow-y` - unnoticed until
now because every prior modal's content was short enough to fit any real viewport. Anticipated
that `AddEmptyUnitModal`'s ~15 fields (11 tri-state rows alone) would not fit, especially at
375px, added `max-height: 90vh; overflow-y: auto` to `.dialog` globally (helps any future
longer-content modal too, not just this one) BEFORE live-verifying - then confirmed the fix was
actually necessary, not speculative caution: measured the real dialog at 375px width,
`scrollHeight` was `2267px` against a `731px` constrained `clientHeight`, with `overflowY: auto`
and `isScrollable: true` both confirmed via `getComputedStyle`/direct DOM measurement.

**A testing-tooling false alarm, caught and correctly diagnosed rather than reported as an app
bug**: the first attempt to check "Cleaning required" via the native-property-setter pattern
(the same one used successfully throughout this session for `<select>`/`<input type="text">`)
silently didn't stick for a `<input type="checkbox">` - the created record came back
`CleaningRequired: false` despite the DOM showing `checked: true` moments before submit. Rather
than concluding the checkbox wiring was broken, re-ran the exact same flow using a plain
`element.click()` instead, confirmed `checked` stayed `true` on a delayed re-read (ruling out a
momentary flicker), and got a real `CleaningRequired: true` row in the database on the second
attempt - the component was correct all along; the descriptor-based setter approach specifically
doesn't reliably drive a checkbox's React `onChange` in this environment, `.click()` does. Worth
remembering for any future live-verification session involving a checkbox: prefer `.click()`
over the native-setter dance, which this session already knew works for text/select inputs but
had not yet tried on a checkbox.

**Verified live, end to end**: started a real inspection on "Elm Court" specifically (the one
demo property with actual seeded `CleaningAreas` - "15 High Road" has none, an HMO by design per
Phase 11's seed data) - both gateway buttons appeared on the Sections screen. Add Empty Unit:
real units loaded, two tri-state checks toggled to real values, saved - confirmed via direct DB
query that `ElectricityOn=false`/`SignsOfDamp=true` were stored correctly and `WaterOn` stayed
genuinely `NULL` (untouched, not defaulted), AND that the unit's `OccupancyStatus` flipped
`Occupied` → `Vacant` - the Phase 12 side effect, reachable from the actual wizard UI for the
first time (previously only exercised via direct API tests). Grade Cleaning Area: real areas
loaded, graded "E" with `CleaningRequired=true` on the corrected second attempt - confirmed via
direct DB query. Confirmed a Viewer sees neither button on the Sections screen. Confirmed the
375px scroll fix with real measurements (above). All test data (the inspection, its 102 snapshot
responses, the vacant-unit record, the cleaning record) cleaned up afterward, including manually
restoring the demo unit's `OccupancyStatus` back to `Occupied`.

## 2026-08-25 — Inspection engine Sub-phase F built: Review and Submit, closing out the whole wizard

Inspection Review - the last of the six sub-phases planned earlier this date. New
`InspectionReviewPage.jsx`, a third page nested under `InspectionWizardLayout` alongside
Sections and Question, reached via a "Review & Submit" link (relabelling to "View Review
Summary" post-submit) added to the Sections screen. Sets `GeneralNotes`/`OverallCondition`/
`OverallRiskRating` via the `PATCH /api/inspections/{id}` endpoint added specifically for this
during Sub-phase A's own planning session - the first thing to actually use it.

**`OverallRiskRating`'s options come from the company's own live risk matrix, not a hardcoded
list** - a new `riskService.getRiskMatrix()` wraps `GET /api/risk-matrix-levels`, and the
select's options are that response's `LevelName`s. This isn't an invented nicety - it's
literally what `app/schemas/inspection.py`'s own existing comment already said should happen
("an inspector's overall rating should be free to use the same vocabulary their company's matrix
does"), just never implemented until a frontend consumer needed it.

**Deliberately did NOT attempt to compute "which mandatory questions remain unanswered"
client-side**, even though it would make for a richer pre-submit summary. `InspectionResponseSchema`'s
frozen snapshot doesn't carry the live `IsMandatory` flag - reconstructing that logic here
(e.g. by cross-referencing the live template) would duplicate, and risk silently disagreeing
with, `submit_inspection`'s own authoritative count-and-preview computation. Chose to surface
that backend message verbatim via `getErrorMessage()` on a 422 instead - matching the "let the
backend be the source of truth" principle `MediaAttachments.jsx`'s AllowsPhoto/RequiresPhoto
decision already established earlier this session, now applied to a second, harder case.

**A small but real component gap, found and closed rather than routed around**: `SelectField`/
`FormField`/`FieldShell` had never needed a `disabled` prop before - every other disabled
control in this app (Sections/Question screens) disables a plain `<button>`/`<input>` directly,
never through these shared field components. Added `disabled` to `FieldShell`'s `fieldProps`
(one place, benefits `FormField` too, not just `SelectField`) rather than hand-rolling a
one-off `<select>` outside the shared component just for this page.

**Verified live, thoroughly, closing the loop on the whole wizard**: on a fresh 0%-complete
inspection, attempting Submit surfaced the backend's own exact message ("Cannot submit: 13
mandatory question(s)...", with real question text) - confirmed byte-for-byte, not a
paraphrase, proving the "don't duplicate this logic" decision above actually holds up. Set
`OverallCondition=Good` and `OverallRiskRating=Low` (a REAL seeded matrix `LevelName`, not a
placeholder) - both saved instantly, confirmed surviving a full page reload. Typed
`GeneralNotes`, confirmed the debounced/blur-flush save fired exactly like the Question screen's
own Notes field. Rather than clicking through all 102 questions by hand to reach a submittable
state (impractical for a verification pass), answered every response directly via the API
(`IsNotApplicable: true` on all of them - a type-agnostic way to satisfy `_is_answered`
regardless of `AnswerTypeSnapshot`, so it works uniformly including the `MeterReading` question
without needing a real photo/OCR round-trip for this particular check), then performed the
actual SUBMIT through the real UI - confirmed via a direct DB query that `Status`/`SubmittedAt`/
`CompletedAt` and all three summary fields persisted exactly as entered. Confirmed every control
on the Review page, and every answer control on a real Question page, became disabled once
`Submitted` - the wizard's post-submission immutability (Phase 8's own rule) now visibly
enforced in the actual UI, not just at the API layer. Confirmed a direct `POST .../submit`
against the same already-submitted inspection correctly 409s - double-submit protection,
exercised through this page's own real flow for the first time this session (previously only
ever hit via a backend test). Confirmed a Viewer sees the same confirmed values read-only with
no Submit button. No horizontal overflow at 375px. All test data cleaned up from the real DB
afterward.

**This closes the entire Inspection Engine Wizard (Prompt 17), scope's own "most important
screen in the application," across all six sub-phases planned earlier this date.** Phase 16
itself is NOT done, though - its exit criteria needs every module's own standalone list/detail
pages too (Maintenance, Risk Register, Cleaning, Vacant Units, Meter Readings, Admin Settings),
which the wizard's quick-create paths only ever fed records INTO, never gave a way to browse or
manage afterward. No sub-phase order has been chosen for those yet - an open decision for
whenever that work starts, not something today's planning session covered.

## 2026-08-25 — Maintenance module built: the first of Phase 16's remaining standalone pages, two real bugs found live

Asked what to build next (the wizard being fully done left an open choice among the ~6 remaining
Phase 16 modules), recommended Maintenance specifically because scope calls it "a major
standalone module," it already had real records flowing in from the wizard's own quick-create
(Sub-phase C), and there was genuinely no way to see, assign, or update any of them - the
backend's `PATCH /{id}/assign`/`PATCH /{id}/status` endpoints existed and worked (proven by
Phase 10's own tests) but were completely unreachable from the UI. Owner agreed; built list/
detail/edit (`pages/maintenance/`).

**A real, necessary backend gap found while designing the Assign control, not before**: nothing
in the entire backend could enumerate a company's users - `user_repository.py`'s two existing
functions (`get_user_by_email`/`get_user_by_id`) are both single-user lookups for auth, and its
own module docstring had already flagged, back in Phase 5, that "a future 'admin looks up a user
by ID in their own company' endpoint... WOULD need CompanyId scoping, don't copy this pattern
for that case" - that anticipated need finally arrived. Added `list_users_for_company` (properly
scoped, per that warning) and a new `GET /api/users` (`app/api/users.py`) - view-only, no role
restriction, matching every other view endpoint's "any company member can see this" shape. 3 new
tests, full backend suite (132 total) re-run clean before touching the frontend.

**Three authorization tiers, matching `maintenance_service.py`'s own documented shape exactly,
not a single blanket "can edit" flag** - the same discipline every prior sub-phase this session
established, now applied to a full CRUD-ish module rather than one quick-create action:
`canManage` (Administrator/Manager) gates Edit and Assign; `canWork` (the issue's own
`AssignedUserId`, OR `canManage` - computed per-record, mirroring `InspectionWizardLayout`'s
`canEdit` exactly) gates status/notes/photos; plain view has no gate. A new
`CAN_MANAGE_MAINTENANCE` constant covers the first tier; the second is per-record and can't be a
static role list, the same reasoning `constants/roles.js`'s own `CAN_CONDUCT_INSPECTIONS`
comment already documented for Inspections.

**`MediaAttachments.jsx`'s first real extension point used for something other than its default
behavior**: added an optional `onUpload(file)` override, since `maintenance_service.upload_photo`
writes a `PhotoUploaded` timeline entry the generic `/api/media` upload has no way to know about.
Every other caller (InspectionResponse photos, Sub-phase B) omits the prop and is unaffected -
confirmed by rebuilding and re-verifying those still work identically after the change.

**Two real bugs found only by live verification, both fixed before considering the module done**:

1. The Timeline went stale after uploading a photo - the backend correctly wrote the
   `PhotoUploaded` row (confirmed via a page reload showing it), but the live page kept showing
   the pre-upload `Updates` array until manually refreshed. The natural-looking fix (`onUpload`
   calling the same `loadIssue()` used on mount) would have been WRONG - `loadIssue()` flips
   `loading`, whose early-return would unmount the entire detail page, `MediaAttachments`
   included, mid-upload. Added a separate `refreshTimeline()` - a quiet re-fetch with no loading
   gate - chained onto the `onUpload` promise instead. Confirmed working: uploaded a second
   photo, the Timeline's new "uploaded a photo" entry appeared immediately, no reload needed.

2. The Edit form's success toast never appeared. `MaintenanceIssueFormPage` correctly navigated
   back with `state: { toast: "..." }` (the same convention `PropertyFormPage`/
   `PropertiesListPage` already use), but `MaintenanceIssueDetailPage`'s own toast state was
   plain `useState(null)` - the `location.state?.toast` initialization + clear-on-mount effect
   every other page using this exact pattern already has had been left out. A straightforward
   omission, not a design problem - fixed by copying the established pattern in full this time,
   confirmed live (the toast now shows after a real edit).

**Verified live, end to end, as four different users in sequence** (Administrator, a
cross-company Administrator, the assigned Maintenance-role worker, a Viewer) against one real
issue created via the API: assigned it as Administrator (Status auto-advanced Open→Assigned,
confirmed in the Timeline, matching Phase 10's own documented auto-advance rule), updated status
to InProgress with a comment, added a note, uploaded two photos (Timeline updated live both
times, post-fix), edited the Title and Due date (toast confirmed, post-fix). The assigned
Maintenance worker (not Admin/Manager) saw status/notes/photos controls but neither Edit nor
Assign - `canWork` without `canManage`, the one tier combination not otherwise exercised by the
Administrator pass. A cross-company Administrator got a real "Maintenance issue not found." on
the same URL. A Viewer saw a fully read-only page, including both real photos (view has no role
restriction). No horizontal overflow at 375px on either List or Detail. All test data (the
issue, its full timeline, both media rows, and both files on disk) cleaned up afterward - the
cleanup order needed `MediaFiles` deleted before `MaintenanceUpdates`/`MaintenanceIssue`, no FK
surprise this time since the media rows don't reference the issue back the way `MeterReadings.
PhotoMediaFileId` did in Sub-phase D.

**A pattern worth carrying into the next remaining module (Risk Register/Cleaning/Vacant Units/
Meter Readings/Admin Settings), confirmed twice now this session** (this module's `GET /api/
users`, Sub-phase D's `inspection_response_id` filter): read the relevant `_service.py` file's
authorization logic AND check whether the existing API surface actually supports what a new
management page needs (a lookup, a filter, a picker) BEFORE designing that page's frontend - both
times this session, the answer was "not quite," and the gap was small and worth closing properly
rather than working around client-side.

## 2026-08-25 — Risk Register module built: simpler than Maintenance, and correctly so, not by accident

Asked to continue with the next standalone Phase 16 module after Maintenance; picked Risk
Register. Built list/detail/create/edit (`pages/risk/`) - genuinely simpler than Maintenance
(two static role tiers, no timeline table, no per-record assignee carve-out), confirmed by
reading `risk_service.py` in full before assuming either Maintenance's three-tier shape or its
own prior two-tier precedent (Cleaning/VacantUnit) applied here unmodified - it doesn't; this
module's own docstring re-derives its shape from first principles, the same discipline every
prior module in this project has used.

**No backend addition needed this time** - a genuine, useful data point, not just "nothing to
report": the existing `/api/risk-assessments` and `/api/risk-matrix-levels` surface already
covered everything the frontend needed (list filters, a matrix reference for RiskLevel options).
Confirms the standing lesson cuts both ways - checking whether a gap exists is real work
regardless of which answer it turns up, not a formality that always finds something to add.

**A deliberate, considered difference from Maintenance's precedent, not an inconsistency**:
`/risk-assessments/new` is a real standalone route (unlike Maintenance, which has none).
Re-checked scope §19's actual wording rather than assuming Maintenance's "creation is
wizard-only" pattern generalizes - §19 lists "Property, Inspection" as fields without ever
saying risk assessments can ONLY be raised from an inspection question the way §17 explicitly
says for Maintenance ("An inspector should be able to create a maintenance issue from any
inspection question"), and the backend's own `RiskAssessmentCreate` already supports a
standalone, non-inspection-linked entry with no code changes needed to enable it - a genuine
Risk Register use case (a manager logging a hazard noticed on a site visit, not during a formal
inspection), not scope creep invented to have something to build. `createRiskAssessment` in
`riskService.js` was generalized from Sub-phase C's five-field quick-create shape to the full
`RiskAssessmentCreate` field set - confirmed the original quick-create modal (Sub-phase C) still
works unchanged, since every new parameter is optional and the original five keep their names.

**A THIRD distinct authorization tier, confirmed by reading `media_service.py` rather than
copying Maintenance's Photos gating** (`canWork`-style, `ensure_can_edit`-based): RiskAssessment's
media mutate check is the SAME function as its view check - any company member, full stop, no
role or per-record gate at all. This was already documented from Phase 13 (memory:
"RiskAssessment's media mutate check is the SAME as its view check") but re-verified against the
actual `media_service.py` source rather than trusted from memory alone, then proven with a real
end-to-end test: a Viewer login - the single most restricted role in this entire project -
successfully uploaded a real photo to a risk assessment they have no other access to modify at
all (no Edit link, 403 on any hypothetical PATCH). `MediaAttachments` on this page gets
`editable={true}` unconditionally, not wired to `canManage` the way it would be if this module's
shape had been assumed rather than checked.

**Verified live, across three different real users, on one real risk assessment**: created as an
Inspector using scope §19's own worked example (Likelihood=4, Severity=5) - confirmed
`RiskScore=20`/`RiskLevel=Critical` matched exactly, no Edit link shown (correct - Inspector
isn't in `CAN_MANAGE_RISK`), successfully uploaded a photo anyway (the third-tier rule, exercised
by the actual creator this time, not just a Viewer). An Administrator then edited it - changed
Severity to 2 and Status to "ActionPlanned," assigned a Responsible person - confirmed
`RiskLevel` was RE-derived server-side to "Medium" (4×2=8, correctly landing in the 5-9 band,
not left stale at "Critical"), the resolved Responsible-person name appeared correctly, and the
edit-success toast worked (this module built the `location.state?.toast` pattern correctly from
the start, unlike Maintenance's initial miss - the lesson from that bug was already internalized
by the time this page was written, not just recorded). A cross-company Administrator got a real
404. A Viewer saw a fully read-only page except the still-functional photo upload (the third
tier, confirmed a second way). No horizontal overflow at 375px. All test data (the risk
assessment and both media rows/files) cleaned up afterward.

**A pattern now confirmed to cut both ways, worth carrying forward explicitly**: this session's
standing lesson about checking the backend before designing a frontend isn't just "expect to
find a gap and add an endpoint" (Maintenance's `GET /api/users`, Sub-phase D's `inspection_
response_id` filter) - sometimes the honest answer, arrived at by the same checking process, is
that nothing needs to be added at all (this module). The value is in doing the check every time,
not in the check always producing the same kind of result.

## 2026-08-25 — Cleaning module built: closes two real gaps at once, needed two new backend endpoints and a fourth authorization tier

Chose Cleaning next (own recommendation, not asked): `CleaningInspection` grading records
already existed from the wizard's own "Grade Cleaning Area" gateway action (Sub-phase E) with
nowhere to browse them, AND `CleaningAreas` had genuinely NO management UI at all - every
property still only ever had the 3 auto-seeded areas from Phase 11, with no way to add any of
scope §16's other named area types (Staircase, Landing, Communal Kitchen, Communal Bathroom,
Garden, Laundry Area, Lift, Other). Two real gaps, closed together, not one feature stretched to
look like two.

**A genuinely deeper backend gap than either Maintenance or Sub-phase D's**, found by reading
`cleaning_repository.py` before assuming a company-wide list would be trivial to add: every
single CleaningInspection query in the entire codebase before this was scoped to one already-
authorized Inspection (`list_cleaning_inspections_for_inspection` takes an `inspection_id`, no
`company_id` at all) - there was no query ANYWHERE that could answer "show me this company's
cleaning grades" the way Maintenance/Risk's flat list endpoints already could from day one.
Added a real joined query (`list_cleaning_inspections_for_company`, CleaningInspection→
Inspection→CleaningArea→Property) for the list, but deliberately did NOT reuse a joined query
for the single-detail lookup - `get_cleaning_inspection_detail` composes three already-existing,
already-authorized single-object fetchers instead (`get_cleaning_inspection`, `inspection_
service.get_inspection`, `get_area`), since a single lookup doesn't need the efficiency a real
JOIN buys for a paginated list, and reusing existing isolation-checked functions means no
isolation logic gets written twice. `CleaningInspectionSummaryResponse` extends
`CleaningInspectionResponse` with `PropertyId`/`AreaName` (neither a real column on the ORM
model) via an explicit `from_row` classmethod, the SAME "never `.model_validate()` an object
that doesn't have the attribute" pattern `MaintenanceIssueDetailResponse.from_issue` already
established in Phase 10 - confirmed as a real, repeatable project convention now, not a one-off.

**A FOURTH distinct Photos authorization tier this session, confirmed by reading
`media_service.py` again rather than assuming either Maintenance's or Risk's shape carried
over**: `CleaningInspection`'s media mutate check calls `inspection_service.ensure_can_edit` on
the PARENT Inspection - narrow, like Maintenance's `canWork`, NOT RiskAssessment's unconditional
"any company member" rule. This means `CleaningInspectionDetailPage` needs the parent
Inspection's own `InspectorUserId`/`Status` to compute its own `canEdit` - no shortcut around
fetching it, confirmed by reading `update_cleaning_inspection`'s exact isolation chain before
writing the page. Four modules, four independently-verified tiers so far this session
(Maintenance's `canWork`, Risk's unconditional, MeterReading's hybrid, now Cleaning's
Inspection-anchored `canWork`) - the standing lesson isn't "there are two shapes to pick from,"
it's "there is no default, check every time."

**`PropertyDetailPage.jsx`'s new "Cleaning Areas" section mirrors the Units section's exact
shape** (`CleaningAreaRow`/`AddCleaningAreaForm`, inline edit + add-form + `canManage`-gated
mutation) - a deliberate copy of a proven pattern, not a new one invented for this. One real
difference worth noting: `CleaningAreaUpdate.IsActive` is genuinely bidirectional (unlike
Property's own one-way "Deactivate, no Reactivate" - the backend simply has no reactivate
endpoint for Properties), so this toggle button correctly reads "Deactivate"/"Reactivate"
depending on current state, not a fixed label the way Property's own button is.

**Verified live, closing the full loop for real, not just each half in isolation**: as
Administrator, added a genuinely new area ("Laundry Room," `AreaType=LaundryArea`, scope's own
named type "15 High Road" never had) via the new PropertyDetailPage section - deactivated it
(disappeared immediately from the default view), reactivated it, renamed it inline, all via real
PATCH/GET round-trips. Started a real inspection on that same property and opened the EXISTING
"Grade Cleaning Area" gateway action (Sub-phase E, unmodified) - confirmed the just-created area
appeared as a real selectable option, proving the two new pieces are actually wired together,
not two parallel UIs that happen to share a database table. Graded it (Grade D, Cleaning
Required) - confirmed it appeared correctly on the NEW company-wide list with the right resolved
Property/Area names (the join actually works, not just compiles). Edited it on the detail page
(Status→Completed, assigned a real user) - confirmed via toast and re-render. Uploaded a real
photo. Logged in as an Inspector NOT assigned to that specific inspection - confirmed neither
Edit nor the photo-upload control appeared (the narrow tier, correctly enforced), while the
photo itself still rendered (view stays open to any company member, unaffected by the narrower
mutate tier). A cross-company Administrator got a real 404 on the new detail endpoint. No
horizontal overflow at 375px on any of the three surfaces touched (Areas section, List, Detail).
All test data (the area, the inspection and its 102 responses, the cleaning grade, its media row
and file) cleaned up afterward.

## 2026-08-25 — Vacant Units module built: same gap as Cleaning, confirmed by the exact same read-the-repository-first check

Fourth (and, per `AI_HANDOFF.md`'s own remaining list, second-to-last) Phase 16 standalone
module. Same starting gap as Cleaning: `VacantUnitInspection` records already existed from the
wizard's "Add Empty Unit" gateway action (Sub-phase E) with nowhere to browse them afterward.
Confirmed by reading `vacant_unit_inspection_repository.py` first, exactly the same check that
found Cleaning's gap - every query in the file was scoped to one already-authorized Inspection
(`list_for_inspection`), nothing queried across a whole company. Added
`list_vacant_unit_inspections_for_company` (VacantUnitInspection→Inspection→Unit→Property, for
pagination) and `get_vacant_unit_inspection_detail` (composes three existing fetchers -
`get_vacant_unit_inspection`, `inspection_service.get_inspection`,
`unit_service.get_unit` - the same "compose for a single lookup, real JOIN only for the
paginated list" split Cleaning established). `VacantUnitInspectionSummaryResponse` extends the
base response with `PropertyId`/`UnitNumber` via an explicit `from_row` classmethod, the same
`CleaningInspectionSummaryResponse`/`MaintenanceIssueDetailResponse.from_issue` convention, now
confirmed a fourth time.

**No new authorization tier this time - confirmed, not assumed.** Read
`vacant_unit_service.py`'s own module docstring first: the SAME single tier Phase 12 already
established (the parent Inspection's assigned inspector, or Administrator/Manager, via
`ensure_can_edit`) governs both the wizard's create action and this module's update, and
`media_service.py` was already confirmed (Phase 12's own verification) to gate
`VacantUnitInspection` photos on that identical check. So `VacantUnitInspectionDetailPage.jsx`'s
`canEdit`/`MediaAttachments` wiring is a straight port of `CleaningInspectionDetailPage.jsx`'s
shape, not a new one derived from scratch - the fifth data point on the standing "there's no
default, check every time" lesson landed on "actually the same as last time," which is itself
useful information, not a wasted check.

2 new backend tests (136 total): the standalone list includes `PropertyId`/`UnitNumber` and
correctly filters/excludes by `property_id`, and the standalone detail 404s for a different
company. Full suite reruns clean.

**Verified live, full loop**: as Administrator, started a real inspection on "15 High Road" and
used the EXISTING "Add Empty Unit" gateway action (Sub-phase E, unmodified) to record a finding
on "Flat 1" (Condition=Fair, ElectricityOn=No) - confirmed it appeared on the NEW company-wide
list with the correct resolved Property/Unit names, and on the NEW detail page with every
tri-state field rendered correctly (`No`/`Yes`/`Not checked`, not silently collapsed to a
boolean). Edited it (WaterOn→Yes, added Notes) - confirmed via toast, re-render, and that
untouched fields (Condition, ElectricityOn) survived the partial `PATCH`. A Bright Spaces
Administrator got a real 404 on the same detail URL and saw zero rows on their own list - full
cross-company isolation confirmed on both new endpoints, not just one. All test data (the
inspection and its 102 responses, the vacant-unit record) cleaned up afterward, including
manually restoring "Flat 1"'s `OccupancyStatus` back to `Occupied` (the same real side effect
Phase 12's own test fixture has to account for).

**Remaining Phase 16 pages, per `AI_HANDOFF.md`'s own list**: Meter Readings (list/detail),
Admin Settings, and a Risk Matrix configuration screen. No order decided yet for a future
session.
