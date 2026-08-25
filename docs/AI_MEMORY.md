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
