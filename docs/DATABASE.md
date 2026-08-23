# InspectIQ — Database Design (Phase 2)

Output of Prompt 2 (`prompts/database_prompt.md`). This is the design step — table list, purpose,
relationships, decisions, and problems — required before any SQL is written (Prompt 2's own rule).
SQL generation (Prompt 3) is the next step, file by file, once this is reviewed.

25 tables. Grouped the same way as `PROJECT_PLAN.md §3`, with concrete columns this time (not
exhaustive — types/constraints get finalized when the actual `CREATE TABLE` statements are
written, but every FK and every column that drives a design decision is here).

---

## 1. Core / Tenancy

### Companies
Top-level tenant — every user, property, and audit row is scoped to exactly one.
`CompanyId PK, CompanyName, Address, Telephone, Email, LogoPath, IsActive, CreatedAt`

### Roles
Fixed lookup of the 5 roles (Administrator, Manager, Inspector, Maintenance, Viewer). Global, not
per-company — role *behavior* is fixed by application permission code, not user-editable in v1
(custom roles per company is a plausible V2 ask, not in scope now).
`RoleId PK, RoleName UNIQUE, Description`

### Users
`UserId PK, CompanyId FK, FirstName, LastName, Email UNIQUE, Phone, PasswordHash, IsActive,
CreatedAt, LastLoginAt`

### UserRoles
Join table, Users↔Roles. A join table (not a single `RoleId` on `Users`) even though v1 UI likely
assigns one role per user — avoids a schema change if a user ever needs two roles (e.g. Inspector
+ Maintenance) without redesigning auth.
`UserId FK, RoleId FK` — composite PK.

---

## 2. Property Structure

### Properties
`PropertyId PK, CompanyId FK, PropertyName, AddressLine1, AddressLine2, City, Postcode,
PropertyType (CHECK enum), PropertyStatus (CHECK enum), NumberOfUnits (declared, see §4.3),
MainContactName, MainContactPhone, MainContactEmail, AccessInstructions, KeyLocation,
AlarmAccessCode, GeneralNotes, InspectionFrequency (CHECK enum), LastInspectionDate,
NextInspectionDue, IsActive, CreatedAt, CreatedBy FK Users`

### PropertyContacts
**Additional** contacts beyond the property's own main-contact fields (out-of-hours, secondary,
contractor liaison) — not a duplicate of the primary contact. See §4.1 for why this split exists.
`PropertyContactId PK, PropertyId FK, ContactName, ContactType, Phone, Email, Notes, IsActive`

### PropertyAccess
**Additional** access methods beyond `Properties.AccessInstructions/KeyLocation` — for properties
with more than one entry point (multi-unit blocks, HMOs). Same "main field + supplementary table"
pattern as PropertyContacts.
`PropertyAccessId PK, PropertyId FK, AccessType (Key/Code/Fob/KeySafe/Agent/Other), Location,
AccessCode, Notes, IsActive`

### Units
`UnitId PK, PropertyId FK, UnitNumber, Floor, OccupancyStatus (CHECK enum), TenantOccupierName,
Notes, IsActive, CreatedAt`

---

## 3. Checklist Engine (template side — mutable, edited by admins)

### InspectionTemplates
`InspectionTemplateId PK, CompanyId FK NULLABLE (NULL = global default template usable by every
company; non-null = a company's own customized template — see §4.2), TemplateName, Description,
IsActive, Version INT (bumped on any edit to this template or its Sections/Questions — required by
the PROJECT_PLAN.md §13.1 sign-off), CreatedAt, CreatedBy FK Users`

### InspectionSections
`InspectionSectionId PK, InspectionTemplateId FK, SectionName, SortOrder, IsActive`

### InspectionQuestions
`InspectionQuestionId PK, InspectionSectionId FK, QuestionText, AnswerType (CHECK enum: YesNo,
PassFail, Condition, Text, Number, Date, MeterReading), SortOrder, AllowNotes BIT, AllowPhoto BIT,
RequirePhoto BIT, AllowMaintenanceFlag BIT, AllowRiskFlag BIT, IsMandatory BIT, IsActive`

**Soft-delete only, enforced at the repository layer — no `DELETE` statement ever targets this
table** (or `InspectionSections`/`InspectionTemplates`). Mandatory per the §13.1 sign-off, since a
hard delete would break the FK `InspectionResponses` keeps for analytics joins.

---

## 4. Inspection Instance (frozen at start — the actual record of what happened)

### Inspections
`InspectionId PK, PropertyId FK, InspectorUserId FK Users, InspectionTemplateId FK,
TemplateVersionUsed INT (captured from InspectionTemplates.Version at start time — the §13.1
sign-off's other required addition), InspectionType, InspectionDate, StartedAt, CompletedAt,
NextInspectionDueDate, Status (CHECK enum: Scheduled/InProgress/Completed/Submitted/Cancelled),
GeneralNotes, OverallCondition (CHECK enum), OverallRiskRating, InspectorSignaturePath,
SubmittedAt, CreatedAt`

### InspectionResponses
| Column | Notes |
|---|---|
| `InspectionResponseId` | PK |
| `InspectionId` | FK |
| `InspectionQuestionId` | FK — kept for analytics/reporting joins, never used for report rendering |
| `QuestionTextSnapshot`, `SectionNameSnapshot`, `AnswerTypeSnapshot` | frozen at inspection-start; reports render from these, never from a live join (§13.1) |
| `AnswerText` | canonical human-readable value, always populated (`"Yes"`, `"Fail"`, `"42.5"`, `"2026-08-21"`) |
| `AnswerNumber` | nullable decimal, populated when `AnswerTypeSnapshot` is `Number`/`MeterReading` — enables numeric queries without parsing text |
| `AnswerDate` | nullable date, populated when `AnswerTypeSnapshot` is `Date` |
| `IsNotApplicable` | BIT |
| `Notes` | |
| `CreatedAt`, `UpdatedAt` | |

Hybrid typing (one canonical text column + two typed columns for the answer types that actually
benefit from typed comparison) rather than one fully polymorphic value or one column per answer
type — see §4.4.

---

## 5. Specialized Inspection Outputs

### MeterReadings
`MeterReadingId PK, InspectionResponseId FK NULLABLE, PropertyId FK (denormalized — enables
"latest reading for this property" without joining through Inspection), MeterType (CHECK enum:
Electricity/Gas/Water — future-proofed per scope §11), MeterSerialNumber, PhotoMediaFileId FK
MediaFiles, AIDetectedReading DECIMAL NULLABLE, AIConfidence DECIMAL NULLABLE, ConfirmedReading
DECIMAL NULLABLE, ReadingDateTime, InspectorNotes`

`AIDetectedReading` and `ConfirmedReading` are always separate columns — scope §11 is explicit
that the AI value must never silently become the confirmed one.

### CleaningAreas
Per-property configurable list, not a fixed global enum — a block with a lift and bin store needs
different areas than an HMO without either.
`CleaningAreaId PK, PropertyId FK, AreaName, AreaType (CHECK enum matching scope §16's list, incl.
Other), IsActive`

### CleaningInspections
`CleaningInspectionId PK, InspectionId FK, CleaningAreaId FK, Grade (CHECK enum A–E), Notes,
CleaningRequired BIT, Urgent BIT, AssignedUserId FK Users NULLABLE, DueDate NULLABLE, Status
(CHECK enum: Pending/Assigned/Completed)`

### VacantUnitInspections
Its own table, not a generic `InspectionResponse` — scope §13 explicitly requires storing history
without overwriting the unit's current status, and the field set (electricity/water/heating on-off
etc.) doesn't fit the generic Yes/No/Text/Number shape.
`VacantUnitInspectionId PK, InspectionId FK, UnitId FK, DateIdentifiedVacant, Condition,
ElectricityOn BIT, WaterOn BIT, HeatingWorking BIT, WindowsSecure BIT, DoorsSecure BIT,
SignsOfLeaks BIT, SignsOfDamp BIT, SignsOfPests BIT, CleaningRequired BIT, WasteItemsLeftBehind
BIT, MaintenanceRequired BIT, Notes, CreatedAt`

---

## 6. Cross-Cutting Modules

### MaintenanceIssues
| Column | Notes |
|---|---|
| `MaintenanceIssueId` | PK |
| `CompanyId` | FK, **denormalized** — see §4.5 |
| `PropertyId` | FK |
| `UnitId`, `InspectionId`, `InspectionResponseId` | all FK, all nullable — an issue can originate manually or from any of these |
| `Title`, `Description`, `Location` | |
| `Category` | CHECK enum (14 values per scope §17) |
| `Priority` | CHECK enum: Low/Medium/High/Urgent/Emergency |
| `Status` | CHECK enum: Open/Assigned/InProgress/Waiting/Completed/Closed |
| `AssignedUserId`, `ReportedByUserId` | FK Users |
| `ReportedDate`, `DueDate`, `CompletedDate` | |
| `Notes` | |

### MaintenanceUpdates
Every status change recorded here — the timeline scope §18 asks for.
`MaintenanceUpdateId PK, MaintenanceIssueId FK, UpdateType (StatusChange/Comment/PhotoUploaded),
OldStatus NULLABLE, NewStatus NULLABLE, Comment, UserId FK, CreatedAt`

### RiskAssessments
| Column | Notes |
|---|---|
| `RiskAssessmentId` | PK |
| `CompanyId` | FK, denormalized — see §4.5 |
| `PropertyId` | FK |
| `InspectionId`, `InspectionResponseId`, `MaintenanceIssueId` | FK, all nullable |
| `Location`, `Hazard`, `WhoMayBeAffected`, `ExistingControls` | |
| `Likelihood`, `Severity` | TINYINT, CHECK 1–5 |
| `RiskScore` | **`AS (Likelihood * Severity) PERSISTED` — a SQL Server computed column.** Cannot be inserted or updated directly; structurally impossible for a client-supplied score to be trusted, not just an app-layer convention (scope §14 says "do not trust a risk score supplied by the frontend" — this makes that a database guarantee) |
| `RiskLevel` | snapshotted at write time from `RiskMatrixLevels`, same historical-accuracy principle as §13.1 — thresholds can change later without reclassifying old assessments |
| `AdditionalActionRequired`, `ResponsiblePersonUserId`, `TargetCompletionDate` | |
| `Status` | CHECK enum: Open/ActionPlanned/Closed |
| `Notes` | |

### RiskMatrixLevels
Configurable risk-level bands (scope §19: "keep the risk-level thresholds configurable").
`RiskMatrixLevelId PK, CompanyId FK NULLABLE (NULL = global default matrix, same nullable-CompanyId
pattern as InspectionTemplates), MinScore, MaxScore, LevelName, SortOrder, ColorHint NULLABLE`

---

## 7. Shared Infrastructure

### MediaFiles
`MediaFileId PK, CompanyId FK, FileName, OriginalFileName, ContentType, FileSizeBytes,
StorageKey, EntityType, EntityId, Caption, UploadedByUserId FK, UploadedAt`

`(EntityType, EntityId)` polymorphic — attaches to Property, Unit, Inspection,
InspectionResponse, MeterReading, MaintenanceIssue, RiskAssessment, CleaningInspection (scope §20).

### Notes
`NoteId PK, CompanyId FK, EntityType, EntityId, UserId FK, NoteText, CreatedAt, EditedAt NULLABLE`

Same polymorphic pattern as MediaFiles, for the same reason (scope §21).

### Notifications
`NotificationId PK, CompanyId FK, UserId FK (recipient), NotificationType (CHECK enum per scope
§25), EntityType, EntityId, Message, IsRead BIT, CreatedAt`

Table exists now so the schema doesn't need to change when V2 wires up delivery — no
sending/scheduling logic built yet (scope explicitly defers this to "later").

### AuditLogs
`AuditLogId PK, CompanyId FK, UserId FK NULLABLE (system actions), Action, EntityType, EntityId,
PreviousValue, NewValue, Timestamp, IPAddress NULLABLE, DeviceInfo NULLABLE`

---

## 8. Relationships (ERD-style)

```
Company 1──N User, Property, InspectionTemplate*, RiskMatrixLevel*, MediaFile, Note,
                    Notification, AuditLog, MaintenanceIssue, RiskAssessment
                    (* nullable CompanyId — see §4.2)

User N──N Role (via UserRole)

Property 1──N Unit, PropertyContact, PropertyAccess, CleaningArea, MaintenanceIssue,
              RiskAssessment, MeterReading, Inspection

InspectionTemplate 1──N InspectionSection 1──N InspectionQuestion

Inspection N──1 Property, User (inspector), InspectionTemplate
Inspection 1──N InspectionResponse, CleaningInspection, VacantUnitInspection

InspectionResponse N──1 InspectionQuestion (reference only, not for rendering)
InspectionResponse 1──0/1 MeterReading

MaintenanceIssue N──0/1 Unit, Inspection, InspectionResponse
MaintenanceIssue 1──N MaintenanceUpdate

RiskAssessment N──0/1 Inspection, InspectionResponse, MaintenanceIssue

CleaningInspection N──1 CleaningArea, Inspection

MediaFiles / Notes: polymorphic via (EntityType, EntityId) — no formal FK constraint,
                     validated at the service layer (accepted tradeoff, §4.5-adjacent)
```

---

## 9. Design Decisions

1. **Fixed short enums are `CHECK`-constrained `VARCHAR` columns, not lookup tables**
   (`PropertyType`, `OccupancyStatus`, `InspectionStatus`, `OverallCondition`, `AnswerType`,
   `MaintenanceCategory`, `Priority`, `MaintenanceStatus`, `CleaningGrade`, etc.). These values are
   fixed by application code, not user-configurable — a join table would add query cost for no
   real flexibility benefit.
2. **`Roles` and `RiskMatrixLevels` get real tables**, unlike the enums above, because they carry
   actual behavior/configuration: Roles needs an M:N join for auth, RiskMatrixLevels needs to be
   genuinely editable per scope §19's explicit requirement.
3. **Nullable `CompanyId` as one consistent "global default + optional per-company override"
   pattern**, used identically by `InspectionTemplates` and `RiskMatrixLevels` — one mechanism for
   this need, not two different ones invented independently.
4. **`InspectionResponses` uses hybrid typing** (one canonical `AnswerText` + typed
   `AnswerNumber`/`AnswerDate`) rather than a single polymorphic value column or one column per
   answer type. Slightly more columns than the minimal option, but keeps numeric/date queries
   type-safe without parsing text, and keeps the display path (`AnswerText`) uniform across every
   answer type.
5. **Denormalized `CompanyId` on `MaintenanceIssues`, `RiskAssessments`, `MediaFiles`, `Notes`,
   `Notifications`, `AuditLogs`** — instead of always deriving company via a join to `Property`/
   `Inspection`. Makes the company-isolation rule from `PROJECT_PLAN.md §12.1` mechanically direct
   (`WHERE CompanyId = @CompanyId` on the table itself, not a multi-hop join) — see §10.1 for the
   real risk this introduces and how it's mitigated.
6. **`RiskAssessments.RiskScore` as a SQL Server computed column** (`PERSISTED`) — the same
   "structural guarantee, not app convention" pattern the security considerations ask for.
   `RiskLevel`, by contrast, is a snapshot column (not computed), because its source
   (`RiskMatrixLevels`) is itself editable — same historical-accuracy principle as §13.1, applied
   consistently rather than as a one-off.
7. **Soft delete (`IsActive` bit only, no `DeletedAt` timestamp)** on tenant-owned reference data.
   No business requirement yet needs "when was this deactivated," so the timestamp is left out
   rather than spec'd speculatively — trivially addable later without a breaking change.

---

## 10. Possible Problems

1. **Denormalized `CompanyId` (design decision §9.5) can drift from its parent's `CompanyId`.**
   If a service ever inserts a `MaintenanceIssue` with a `CompanyId` that doesn't match its
   `Property.CompanyId`, that's a structural cross-tenant leak — and SQL Server can't express
   "this FK's CompanyId must equal that other FK's CompanyId" as a plain `CHECK` constraint
   (would need a trigger). **Mitigation for v1**: `CompanyId` on these tables must always be
   derived server-side from the parent entity, never accepted from client input — a
   repository-layer discipline, verified explicitly in Phase 19's security review (the same way
   PropertyManager's Prompt 27 re-tested role isolation). A trigger-based guard is worth
   revisiting if this becomes real commercial SaaS, where the blast radius of a mistake is a
   paying customer's data, not just a demo bug.
2. **`Users.Email` is globally unique, not unique-per-company.** Simpler for login (no "which
   company" step), but means one person can't hold separate accounts at two different companies
   under the same email. Realistic edge case is rare; flagged so it's a known tradeoff, not a
   surprise later.
3. **`Properties.NumberOfUnits` (a declared count) can diverge from `COUNT(Units)` (actual
   modeled units)** — intentional, since a property might be onboarded with a known unit count
   before every unit is individually entered. Worth a UI warning if the two numbers disagree by
   the time a property is marked fully set up, but not a data-integrity bug.
4. **`AlarmAccessCode` (Properties) and `AccessCode` (PropertyAccess) are sensitive, effectively
   physical-security-relevant data** (door codes, alarm codes) stored as plain columns. Same
   category of "fine in dev, dangerous in prod" issue PropertyManager hit with its JWT secret —
   flagging now so encryption-at-rest or field-level encryption is a deliberate Phase 19/20
   decision, not an oversight discovered after deployment.
5. **`CleaningAreas` is per-property, so a new property has zero cleaning areas until someone
   configures them** — a real onboarding gap if not handled. Worth auto-seeding a sensible default
   set (Entrance, Hallway, Bin Area) on property creation, refined by the user afterward, rather
   than requiring manual setup before the first cleaning inspection is possible. Decide during
   Phase 6 (Properties + Units) — noting it here so it isn't forgotten.
6. **`PropertyContacts`/`PropertyAccess` are explicitly "additional" records, not duplicates of
   `Properties`' own main-contact/access fields** — worth restating in code comments at
   implementation time, since the natural instinct (mine included, initially) is to treat a
   `PropertyContacts` row as *the* primary contact and end up with two sources of truth for the
   same data. This document is the record of the resolved intent if that confusion resurfaces.

---

## Next: Phase 2 SQL Generation (Prompt 3)

This document is the "list every table" step. Prompt 3 generates the actual T-SQL, file by file,
under `database/`, per the structure already scaffolded:

```
00_CreateDatabase.sql
tables/01_CoreTables.sql        Companies, Roles, Users, UserRoles
tables/02_PropertyTables.sql    Properties, PropertyContacts, PropertyAccess, Units
tables/03_InspectionTemplateTables.sql   InspectionTemplates, InspectionSections, InspectionQuestions
tables/04_InspectionTables.sql  Inspections, InspectionResponses, MeterReadings,
                                 CleaningAreas, CleaningInspections, VacantUnitInspections
tables/05_MaintenanceTables.sql MaintenanceIssues, MaintenanceUpdates
tables/06_RiskTables.sql        RiskAssessments, RiskMatrixLevels
tables/07_MediaAndNotesTables.sql   MediaFiles, Notes
tables/08_NotificationAuditTables.sql   Notifications, AuditLogs
constraints/09_Constraints.sql
indexes/10_Indexes.sql
seed/11_SeedRoles.sql, 12_SeedInspectionTemplate.sql, 13_SeedSampleData.sql
views/14_InspectionViews.sql
reports/15_DashboardQueries.sql
scripts/00_RunAll.sql
```

One file at a time, each with its own explanation, constraints, and test queries — per Prompt 3's
own pacing rule.
