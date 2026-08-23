# InspectIQ — Architecture (Phase 1)

Output of Prompt 1 (`prompts/master_prompt.md`). No application code exists yet — this is the
design that Phase 2 onward builds against. Full requirements: [`SCOPE.md`](SCOPE.md).

---

## 1. System Architecture

Three-tier, stateless-API architecture:

```
React SPA (mobile-first)  --Axios/JSON-->  FastAPI (stateless, JWT-secured)  -->  SQL Server
                                                     |
                                                     +--> Media storage abstraction
                                                     |      (local disk in dev, blob/object storage in prod)
                                                     |
                                                     +--> OCR/meter-reading abstraction
                                                     |      (mock in dev, real vision provider in prod)
                                                     |
                                                     +--> PDF report generator (renders from
                                                            frozen inspection data, not the live template)
```

Key properties:

- **Stateless backend.** All session state is the JWT; horizontally scalable later without sticky
  sessions.
- **SQL Server is the single source of truth** for all structured data. Media files never live in
  the database — only their metadata and a storage key/path do (scope §20).
- **Multi-tenant from day one.** Every tenant-owned row carries a `CompanyId`. This is the
  single most important architectural decision in the whole system — see §7 and §12.
- **Two swappable-provider boundaries, both required by the scope**: storage (§8) and OCR (§9's
  sibling, meter reading). Both are designed as interfaces with a dev-only concrete implementation
  now, so a real provider drops in later (Phase 14, Phase 20) without touching business logic.
- **Reports are immutable snapshots**, not live renders — scope §18 explicitly requires a
  submitted inspection's report to represent the system exactly as it was at submission time, even
  if the template changes afterward. This drives a real schema decision (§13).

---

## 2. Main Modules

Grouped to match the scope's own module numbering and the 20-phase build order:

| Module | Scope § | Phase |
|---|---|---|
| Companies | 4 | 2 (DB), woven through every phase |
| Users, Roles, Auth | 3 | 5 |
| Properties, Property Contacts, Property Access | 5, 10 | 6 |
| Units, Vacant Unit Inspections | 6, 7, 13 | 6, 12 |
| Inspection Templates / Sections / Questions | 9 | 7 |
| Inspections, Inspection Responses (the engine) | 8 | 7–8 |
| Media (photos/videos) | 20 | 9 |
| Electricity Meter + AI/OCR reading | 11 | 14 |
| Fire/Safety, Gardens, Communal Kitchen (checklist content, not code) | 12–15 | 4 (seeded via templates) |
| Communal Cleaning grading | 16 | 11 |
| Maintenance Issues + History | 17, 18 | 10 |
| Risk Assessments | 19 | 13 |
| Notes | 21 | woven into every entity's API (no separate phase) |
| Reports (PDF) | 22 | 17 |
| Dashboard | 23 | 15 |
| Inspection scheduling/due dates | 24 | part of Property module, Phase 6 |
| Notifications | 25 | deferred — Version 2 |
| Audit Log | 26 | woven into services from Phase 5 onward, not bolted on later |

Note on §12–15 (Fire Safety, Gardens, Communal Kitchen): per §9's explicit instruction, these are
**not** separate database tables or API modules — they're just section/question *content* inside
the generic Inspection Template engine (Phase 7). Treating them as bespoke modules would violate
the scope's central design rule and reintroduce exactly the hard-coded-field problem it warns
against.

---

## 3. Database Entities

~24 tables, matching scope §29:

**Core / tenancy**: `Companies`, `Users`, `Roles`, `UserRoles`

**Property structure**: `Properties`, `PropertyContacts`, `PropertyAccess`, `Units`

**Checklist engine (template side, mutable)**: `InspectionTemplates`, `InspectionSections`,
`InspectionQuestions`

**Inspection instance (frozen at start, immutable in spirit)**: `Inspections`,
`InspectionResponses`

**Specialized inspection outputs**: `MeterReadings`, `CleaningInspections`, `CleaningAreas`,
`VacantUnitInspections` (added — see §13, not in the original ~24 but required by scope §7/§13
having its own field set distinct from a generic `InspectionResponse`)

**Cross-cutting modules**: `MaintenanceIssues`, `MaintenanceUpdates`, `RiskAssessments`

**Shared infrastructure**: `MediaFiles`, `Notes`, `Notifications`, `AuditLogs`

Full column-level design is Phase 2's job (Prompt 2 explicitly asks for table-by-table purpose,
relationships, and design decisions *before* SQL) — not repeated here.

---

## 4. Relationships (high level)

```
Company 1──N User
Company 1──N Property
Property 1──N Unit
Property 1──N PropertyContact
Property 1──1 PropertyAccess

InspectionTemplate 1──N InspectionSection 1──N InspectionQuestion

Inspection N──1 Property
Inspection N──1 User (inspector)
Inspection N──1 InspectionTemplate (which template it was generated from)
Inspection 1──N InspectionResponse
InspectionResponse N──1 InspectionQuestion (reference, for reporting/analytics)
InspectionResponse 1──1 MeterReading (optional, when question type = MeterReading)

MaintenanceIssue N──1 Property
MaintenanceIssue N──0/1 Unit
MaintenanceIssue N──0/1 Inspection
MaintenanceIssue N──0/1 InspectionResponse
MaintenanceIssue N──0/1 RiskAssessment   (cleaning/vacant-unit-originated issues link back)
MaintenanceIssue 1──N MaintenanceUpdate

RiskAssessment N──0/1 Inspection
RiskAssessment N──0/1 InspectionResponse
RiskAssessment N──0/1 MaintenanceIssue

MediaFiles / Notes: polymorphic (EntityType, EntityId) — attach to almost anything (§20/§21)
```

---

## 5. Backend Architecture

Strict layering, enforced by convention (and spot-checked in code review, same as
PropertyManager's Phase 28 audit):

```
api/          FastAPI routers. Thin: parse request -> call one service method -> return schema.
              No business rules, no direct DB session use beyond what the service needs.
schemas/      Pydantic request/response models. Validation lives here (shape, types, ranges).
services/     ALL business logic. Company-isolation enforcement, risk-score calculation,
              mandatory-question checks, state-machine transitions (inspection status,
              maintenance status), audit-log writes.
repositories/ SQLAlchemy queries only. No business rules. Every query that touches a
              tenant-owned table takes CompanyId as a required parameter — not optional,
              not inferred implicitly — so it's structurally impossible to forget it.
models/       SQLAlchemy ORM models = 1:1 with database tables.
security/     Password hashing, JWT encode/decode, role/permission constants, FastAPI
              dependencies for "current user" and "require role X".
core/         Config (pydantic-settings + .env), logging setup, exception handlers.
database/     Session/engine setup, Base declarative class.
```

Same rule PropertyManager used successfully: **routes never contain conditionals about business
rules.** If a route has an `if`, it's almost always misplaced logic that belongs in a service.

Async FastAPI endpoints throughout (matches scope §5's "async where appropriate" — since every
endpoint does at least one DB round-trip, async is the default here, not the exception).

---

## 6. Frontend Architecture

```
api/ or services/   One file per resource (propertyService.js, inspectionService.js, ...),
                     wraps Axios. No component calls Axios directly.
contexts/            AuthContext (current user, token, login/logout).
routes/              ProtectedRoute, role-gated route trees (mirrors PropertyManager's
                     nested-ProtectedRoute pattern, proven across 7 modules there).
components/          Reusable, cross-page: badges (Status/Priority/Risk/CleaningGrade),
                     PhotoUploader, VideoUploader, NotesInput, InspectionQuestion,
                     SectionProgress, forms, LoadingSpinner, ConfirmationModal.
pages/               One folder per module, following PropertyManager's established
                     List/Detail/Form page-triad where a module fits that shape; the
                     Inspection module gets its own bespoke flow (§7 below) since it's a
                     wizard, not CRUD.
layouts/             Shell around desktop (management) vs mobile (field) experiences —
                     both React, not separate apps, but distinct layout components since
                     the primary nav/interaction pattern genuinely differs by device.
```

Mobile-first CSS from the start (not retrofitted, unlike PropertyManager's Prompt 33 finding where
responsive layout was a late add-on). Desktop remains a first-class target for
Dashboard/Reports/Admin, but every component is designed mobile-first and desktop is the
"also works at wider viewport" case, not the reverse.

---

## 7. Authentication Architecture

- Email/password login, JWT access + refresh tokens (same pattern as PropertyManager).
- Roles: `Administrator`, `Manager`, `Inspector`, `Maintenance`, `Viewer` — centralized permission
  constants (a `roles.py` equivalent), never role-name string comparisons scattered through route
  files.
- **Company isolation is resolved server-side per request from the authenticated user's DB row**,
  not trusted from the JWT claim or any client input. A JWT can carry `CompanyId` for convenience/
  display, but every service method re-derives the authoritative `CompanyId` from
  `current_user.CompanyId` loaded fresh from the DB — this avoids a stale-claim bug if a user's
  company ever changes mid-token-lifetime, and it's the same "recheck on every request" pattern
  PropertyManager used for `IsActive`, which caught a real deactivation-timing bug there.
- Disabled users cannot log in, and an existing valid token is invalidated the instant `IsActive`
  flips (`get_current_user` re-checks every request, exactly as PropertyManager does).
- CSP header for the frontend, **built in from Phase 5, not retrofitted at Phase 19.**
  PropertyManager deferred this and paid for it twice — once as a documented gap, once as a
  redeployment bug when it was finally added (a wrong `connect-src` silently blocked every API
  call, no console error). Doing it early avoids both failure modes.

---

## 8. Media/File Architecture

```python
class IMediaStorageService(Protocol):
    def save(self, file, entity_type: str, entity_id: int) -> str: ...  # returns storage key
    def get_url(self, storage_key: str) -> str: ...
    def delete(self, storage_key: str) -> None: ...
```

- Dev implementation: local filesystem under `backend/uploads/` (gitignored).
- Production implementation: object/blob storage (Azure Blob Storage, matching PropertyManager's
  existing Azure footprint, is the natural default — final choice deferred to Phase 20 deployment
  planning, no need to decide now).
- `MediaFiles` stores metadata + storage key only, never binary content, never in SQL Server
  (scope §20 is explicit about this for video especially).
- Upload validation: content-type allowlist, max file size, before the file ever reaches the
  storage layer.
- **File access authorization mirrors the parent entity's authorization** — a maintenance photo
  requires the same permission check as the maintenance issue itself. No "unguessable URL" as a
  substitute for a real permission check.

---

## 9. Reporting Architecture

- One `ReportService`, not one class per report type — same reuse lesson from PropertyManager's 10
  reports sharing one `ReportResponse` shape.
- Reads a *submitted* `Inspection` and its `InspectionResponses` — never re-reads the current
  `InspectionTemplate`. This is why `InspectionResponses` must snapshot enough of the question
  (text, section, answer-type) to render correctly even after the live template changes (§13).
- Backend-rendered PDF (library choice — e.g. WeasyPrint or ReportLab — decided at Phase 17, not
  now; both satisfy "backend-generated PDF" from scope §27 without a frontend rendering dependency).
- Report includes the summary counts scope §22 asks for (Passed/Failed/Needs Attention/Maintenance
  raised/Open risks) — computed once by the service, not duplicated in the PDF template and the
  API response separately.

---

## 10. Recommended Folder Structure

Already created in the repo — see [`SCOPE.md §28`](SCOPE.md#28-recommended-repository-structure).
No changes proposed.

---

## 11. Development Phases

Full 20-phase order preserved verbatim in `SCOPE.md §34`. Restated here with exit criteria:

| Phase | Goal | Exit criteria |
|---|---|---|
| 1 | Architecture | This document, reviewed |
| 2 | SQL database design | Table-by-table design doc + reasoning (Prompt 2 format) |
| 3 | SQL scripts + sample data | Scripts run clean against a real SQL Server instance |
| 4 | FastAPI foundation | Health-check endpoint live, basic tests pass |
| 5 | Authentication | Login/JWT/roles working, auth tests pass |
| 6 | Properties + Units | Full CRUD + tests |
| 7 | Inspection templates | Seeded default template queryable via API |
| 8 | Inspection engine | Start/answer/submit flow works end-to-end, tests pass |
| 9 | Photos/videos | Upload/retrieve/delete against local storage, tests pass |
| 10 | Maintenance | Full lifecycle + history, tests pass |
| 11 | Cleaning | Grading + dashboard queries, tests pass |
| 12 | Vacant units | Full flow, tests pass |
| 13 | Risk assessments | Server-calculated scoring, tests pass |
| 14 | Meter OCR/AI | Mock provider integrated, confirm/correct flow works |
| 15 | Dashboard | All scope §23 numbers correct against real data |
| 16 | React frontend | All pages navigable, auth-gated correctly |
| 17 | PDF reports | Report matches a real submitted inspection exactly |
| 18 | Testing | Full pass across every module + adversarial cases (scope §19) |
| 19 | Security | Cross-company isolation explicitly verified (scope §20) |
| 20 | Deployment | Live, verified end-to-end (same checklist discipline as PropertyManager) |

Each phase: build, test against a real SQL Server DB (no mocks — validated PropertyManager
convention), commit to git with an honest message, then stop for review before the next phase.

---

## 12. Security Considerations

1. **Cross-company data isolation is the top risk**, worse in kind than PropertyManager's
   cross-role leaks because it's cross-*customer* — a bug here could leak one paying company's
   inspection data (property access codes, tenant info, photos) to a competitor. Mitigation:
   `CompanyId` required (not optional) on every repository method touching tenant data; Phase 19
   explicitly re-tests this the way PropertyManager's Prompt 27 did for roles.
2. Password hashing (bcrypt/argon2, same as PropertyManager), JWT secret validated non-placeholder
   outside dev from day one (PropertyManager caught this as a *deployment-time* critical finding —
   build the guard in from Phase 5 this time).
3. File upload validation (content-type allowlist, size cap) — untrusted user-uploaded photos/
   videos are a real attack surface (scope §9 explicitly asks for this).
4. Risk score and meter-reading confirmation are **never trusted from the client** — both
   explicitly required by scope §11/§14 to be server-authoritative.
5. Audit log covers the actions scope §26 lists, written by the service layer (not reconstructed
   later from logs), same as PropertyManager's audit trail.
6. `APP_DEBUG` off by default (PropertyManager's Prompt 27 finding — this was a real bug there:
   `echo=True` on SQLAlchemy logs full SQL + bound params, including PII, to stdout).

---

## 13. Important Database Design Decisions

1. **InspectionResponse snapshot strategy — CONFIRMED 2026-08-23 after explicit owner review.**
   - `InspectionResponses` keeps a foreign key to `InspectionQuestion` (for analytics/reporting
     joins), **plus** frozen columns (`QuestionTextSnapshot`, `SectionNameSnapshot`,
     `AnswerTypeSnapshot`) captured at the moment the inspection starts.
   - Reports render from the snapshot columns, never from a live join to `InspectionQuestion` —
     satisfies scope §9/§18's explicit "preserve inspection history even if templates change."
   - Alternative considered and rejected: versioning the whole `InspectionTemplate` (a
     `TemplateVersion` table). More "correct" in a strict sense, but meaningfully more complex for
     a v1/MVP, and the scope's own emphasis is on getting the Template→Section→Question→
     Inspection→Response shape right, not on template version history as a feature.
   - **Two regret-mitigations added during review, both required from Phase 2 onward, not
     optional polish:**
     1. **`InspectionQuestions` (and Sections/Templates) are soft-delete only — never hard
        deleted.** A hard delete would silently break the FK that frozen columns deliberately
        keep around for analytics joins. This must be enforced at the repository layer (no
        `DELETE` statement against these tables, ever), not just documented as a convention.
     2. **A `Version` integer on `InspectionTemplate` (bumped on any edit to it or its
        Sections/Questions), stored on `Inspections.TemplateVersionUsed` at inspection-start
        time.** This is *not* full version history — it doesn't let you reconstruct exactly what
        version N looked like — but it cheaply answers "which inspections predate/postdate this
        checklist change," which is the one realistic compliance question frozen columns alone
        can't answer. If full template version history is ever needed later, this column is
        exactly the backfill data a `TemplateVersions` table would need — the migration path is
        additive, not a rewrite.
   - Net effect: historical reports are accurate (the core requirement), template-change auditing
     is cheap and present from v1, and nothing here blocks adding real versioning later if a
     concrete need for it shows up.
2. **Soft delete on tenant-owned reference data** (Properties, Units, Templates) rather than hard
   delete — hard-deleting a Property with historical Inspections would either cascade-delete real
   inspection history or orphan FKs; neither is acceptable given §18's audit-trail requirement.
3. **Polymorphic `MediaFiles`/`Notes`** via `(EntityType, EntityId)` rather than one nullable FK
   column per possible parent table (Property, Unit, Inspection, InspectionResponse,
   MaintenanceIssue, RiskAssessment, CleaningInspection, MeterReading — 8+ nullable FKs otherwise).
   Accepted tradeoff: loses a DB-enforced FK constraint on these two tables specifically,
   validated at the service layer instead. Documenting this now so it reads as a deliberate
   choice, not an oversight, if revisited later.
4. **Risk matrix thresholds stored as configuration, not hard-coded constants** — scope §19 is
   explicit that the 1–4/5–9/10–16/17–25 bands must remain configurable rather than assumed to
   replace a company's official methodology. Modeled as a small lookup table or company-level
   config row, decided at Phase 2 alongside the rest of the risk schema.
5. **`VacantUnitInspections` as its own table**, not reusing the generic `InspectionResponse` shape
   — its field set (electricity/water/heating on-off, leaks, damp, pests, etc., scope §7/§13) is
   materially different from a generic Yes/No/Pass/Fail/Text/Number question, and scope §13
   explicitly says "store historical vacant-unit inspections, do not simply overwrite the unit's
   current status" — a dedicated table with its own history makes that requirement direct rather
   than implied.

---

## 14. Future Scalability Considerations

- **Multi-company support is not a future retrofit — it's built into every tenant table from
  Phase 2.** This is the main reason the scope doc says this project has more SaaS potential than
  PropertyManager: PropertyManager is single-tenant with role-based views; InspectIQ is
  multi-tenant from day one.
- Notifications (§25), offline/PWA mode, contractor/client portals, and billing (§32/§33) are
  deliberately **not** designed against in v1 — over-designing for them now would violate the
  scope's own MVP discipline (§31) the same way PropertyManager avoided premature abstraction.
  When V2 work starts, the swappable-provider pattern already used for storage/OCR is the template
  to follow for a notification-delivery abstraction (in-app now, email/SMS later).
- The checklist engine (Template → Section → Question → Inspection → Response) is generic enough,
  by design, to eventually serve inspection types beyond property compliance (cleaning audits,
  fire-safety checks, snagging, handovers — scope's closing paragraph) without a schema change,
  only new seeded template data.

---

## Phase 1 sign-off

§13.1 (the InspectionResponse snapshot strategy) was reviewed and confirmed with the owner on
2026-08-23, including two regret-mitigations (soft-delete-only on `InspectionQuestions`, a
`Version`/`TemplateVersionUsed` counter) folded into the decision. No open questions remain —
everything else in this document is a reasonable default that can still flex during Phase 2's own
"list every table, explain design decisions, point out possible problems" step. **Phase 1 is
complete; Phase 2 (Database Design) starts next.**
