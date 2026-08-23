# InspectIQ — Original Scope Document

> Source of truth for the project's requirements and build order. Do not delete or silently
> reinterpret this file — if a later decision deviates from it, document the deviation in
> `AI_MEMORY.md` with the reason, the way PropertyManager's `progress-log.md` did.

This is the full scope and phased prompt sequence as provided by the project owner on 2026-08-23,
verbatim. The individual phase prompts are also split out under `prompts/` for convenience, but
this file is the canonical, complete version.

---

# Property Inspection & Compliance Software

## 1. Project Overview

Build a professional property inspection and compliance management system for:

* Contractors
* Property management companies
* Project managers
* Property inspectors
* Maintenance teams
* Cleaning teams
* Building managers

The application should allow a user to arrive at a property, open the property on their
phone/tablet, start an inspection and work through a structured checklist.

For every inspection item the user should be able to:

* Mark its condition/status
* Add notes
* Take/upload photos
* Upload videos
* Create maintenance issues
* Create risk assessment items
* Record readings
* Flag urgent problems
* Mark something as not applicable

At the end of the inspection the system generates a professional inspection report.

---

## 2. Main User Journey

Login → Dashboard → Select Property → Start Inspection → Property Details → Access Information →
Property Checklist → Units → Meters → Fire / Safety → Communal Areas → Gardens / Exterior →
Cleaning Inspection → Maintenance Issues → Risk Assessment → General Notes → Review Inspection →
Sign / Submit → Generate Report → Schedule Next Inspection

The system should automatically save progress while the inspection is taking place.

---

## 3. Main Modules

### Module 1 — Authentication & Users

Users must log in securely.

Information: First name, Last name, Email, Phone, Password, Company, Role, Active/inactive,
Date created, Last login.

#### Roles

**Administrator** — Full access.

**Manager** — Manage properties, view all inspections, assign inspections, manage maintenance,
view reports.

**Inspector** — View assigned properties, conduct inspections, upload evidence, raise maintenance
issues, complete risk assessments.

**Maintenance User** — View assigned maintenance problems, update status, upload completion
photos, add notes.

**Viewer** — Read-only access to properties, inspections and reports.

---

## 4. Company

Create a Company entity.

Fields: Company ID, Company name, Address, Telephone, Email, Logo, Active, Date created.

All users belong to a company. All properties should also belong to a company. This allows the
software to eventually support multiple management companies.

---

## 5. Properties

Each property should have: Property ID, Property name, Full address, Postcode, Number of units,
Main contact name, Main contact number, Contact email, Property type, Property status, Access
instructions, Key location, Alarm/access code field, General property notes, Last inspection date,
Next inspection due, Active/inactive.

Property type examples: HMO, Block of flats, Residential house, Commercial building, Mixed-use
property, Office, Other.

---

## 6. Units

Properties can contain multiple units.

Example: Property "15 High Road" → Units: Flat 1, Flat 2, Flat 3, Flat 4, Communal Area.

Each unit should have: Unit ID, Property ID, Unit name/number, Floor, Occupancy status,
Tenant/occupier name if required, Notes, Active/inactive.

Occupancy Status: Occupied, Vacant, Under refurbishment, Unavailable, Unknown.

---

## 7. Empty / Vacant Unit Inspection

During an inspection an inspector should be able to click "Add Empty Unit". The system should ask:
Unit, Date identified vacant, Condition, Electricity on/off, Water on/off, Heating working?,
Windows secure?, Doors secure?, Signs of leaks?, Signs of damp?, Signs of pests?, Cleaning
required?, Waste/items left behind?, Maintenance required?, Photos, Videos, Notes.

A maintenance issue should be creatable directly from any of these questions.

---

## 8. Inspections

The Inspection table should contain: Inspection ID, Property ID, Inspector ID, Inspection type,
Inspection date, Inspection started at, Inspection completed at, Next inspection due date, Status,
General notes, Overall condition, Overall risk rating, Inspector signature, Submitted date.

Inspection Status: Scheduled, In Progress, Completed, Submitted, Cancelled.

Overall Condition: Excellent, Good, Satisfactory, Needs Attention, Poor, Critical.

---

## 9. Inspection Checklist Engine

Do NOT hard-code every inspection question directly into the application. Build a reusable
checklist/template system.

Create **InspectionTemplate** (e.g. "Monthly Property Inspection") and **InspectionSections**
(e.g. Property Access, Electricity, Fire Safety, Emergency Lighting, Front Garden, Back Garden,
Communal Kitchen, Communal Areas, Cleaning, Units, Maintenance, Risk Assessment).

Each section contains checklist questions, e.g. under Emergency Lighting: Is emergency lighting
installed? Does it appear operational? Is there visible damage? When was it last tested? Is
maintenance required?

For every question allow: Yes, No, Pass, Fail, Good, Satisfactory, Poor, Not Applicable, Text
answer, Numeric reading, Notes, Photos, Videos.

The administrator should eventually be able to create and edit inspection templates.

---

## 10. Access to Property

Record: Was access available? How was access obtained? Key used? Key location, Access code, Door
condition, Lock condition, Intercom working?, Access problems, Notes, Photos.

If there is a problem: Create Maintenance Issue.

---

## 11. Electricity Meter

The inspector should take a photograph of the electricity meter.

Store: Meter type, Meter serial number, Meter reading, Reading date/time, Photograph, AI/OCR
detected reading, Confirmed reading, Inspector notes.

### AI Feature

When a meter photograph is uploaded:

1. Send image to an OCR/meter-reading service.
2. Attempt to identify the meter reading.
3. Display "AI detected reading: 018294.6".
4. Ask inspector to confirm or correct it.
5. Save both the AI detected value and the user-confirmed value.

Never automatically trust the AI reading without allowing human confirmation.

The same architecture can later support gas meters and water meters.

---

## 12. Alarm / Fire Safety

**Fire Alarm**: Alarm installed?, Alarm panel showing normal?, Fault showing?, Damage?, Test
completed?, Result, Notes, Photos.

**Smoke / Heat Detectors**: Present?, Damaged?, Test completed?, Result, Notes, Photos.

**Emergency Lighting**: Present?, Appears operational?, Damage?, Test required?, Last test date,
Notes, Photos.

**Fire Doors**: Door closes correctly?, Door damaged?, Closers working?, Seals present?, Signage
present?, Notes, Pictures.

Failures should allow the inspector to immediately create a Maintenance Issue and/or Risk
Assessment Item.

---

## 13. Front Garden

Overall condition, Rubbish present?, Overgrown vegetation?, Pathway safe?, Lighting working?,
Fence condition, Gate condition, Trip hazards?, Pest evidence?, Maintenance required?, Notes,
Photos, Videos.

---

## 14. Back Garden

Same structure: Overall condition, Rubbish, Vegetation, Pathways, Lighting, Fencing, Gates,
Drainage, Trip hazards, Pest evidence, Maintenance, Notes, Pictures/videos.

---

## 15. Communal Kitchen

Overall cleanliness, Floor condition, Worktops clean, Sink clean, Cooker clean, Fridge condition,
Food waste, Bins emptied, Lighting working, Electrical sockets visually safe, Fire safety
equipment present, Pest evidence, Leaks, Damage, Maintenance required, Notes, Pictures.

---

## 16. Communal Cleaning

Cleaning needs its own grading system. For every communal area allow a grade.

**Cleaning Grades**: A — Excellent (clean and well maintained); B — Good (minor cleaning required
but generally acceptable); C — Needs Attention (noticeable cleaning required); D — Poor
(significant cleaning required); E — Critical (unacceptable condition requiring urgent action).

Areas could include: Entrance, Hallway, Staircase, Landing, Communal kitchen, Communal bathroom,
Bin area, Garden, Laundry area, Lift, Other.

Each cleaning assessment should contain: Area, Grade, Notes, Pictures, Cleaning required?,
Urgent?, Assigned cleaner, Due date, Status.

---

## 17. Maintenance Issues

Maintenance must be a major standalone module. An inspector should be able to create a maintenance
issue from any inspection question, automatically copying Property, Inspection, Inspection
section, Checklist item, Photos, then asking Issue title, Description, Location, Unit, Category,
Priority, Assigned person, Due date, Notes.

**Maintenance Categories**: Electrical, Plumbing, Heating, Fire safety, Emergency lighting,
Cleaning, Garden, Structural, Doors/windows, Pest control, Decoration, Appliance, Security, Other.

**Priority**: Low, Medium, High, Urgent, Emergency.

**Status**: Open, Assigned, In Progress, Waiting, Completed, Closed.

Maintenance staff should be able to upload Before photos/videos and After completion photos/videos.

---

## 18. Maintenance History

Every maintenance issue should have a timeline (e.g. Issue Created → Assigned → In Progress →
Completed → Completion Photo Uploaded). This creates an audit trail.

---

## 19. Risk Assessments

Fields: Property, Inspection, Location, Hazard, Who may be affected, Existing controls,
Likelihood, Severity, Risk score, Risk level, Additional action required, Responsible person,
Target completion date, Status, Notes, Pictures.

### Risk Calculation

Likelihood × Severity = Risk Score.

Likelihood: 1 Rare, 2 Unlikely, 3 Possible, 4 Likely, 5 Very Likely.
Severity: 1 Insignificant, 2 Minor, 3 Moderate, 4 Major, 5 Severe.

Example: Likelihood 4 × Severity 5 = Risk Score 20.

Risk levels: 1–4 Low, 5–9 Medium, 10–16 High, 17–25 Critical.

The exact risk matrix should remain configurable rather than assuming it replaces a company's
official risk-assessment methodology.

---

## 20. Pictures and Videos

Photos/videos need to be attached to Property, Inspection, Inspection section, Checklist question,
Unit, Meter reading, Maintenance issue, Risk assessment, Cleaning inspection.

Store metadata: File ID, Original filename, Storage location, File type, File size, Uploaded by,
Uploaded date/time, Caption, Related entity type, Related entity ID.

Do not store large video files directly inside SQL Server. Store them in file/object storage and
keep their reference in the database.

---

## 21. Notes

Notes should be available almost everywhere.

Notes table: Note ID, Entity type, Entity ID, User ID, Note, Created date/time, Edited date/time.

Applies to: Properties, Units, Inspections, Maintenance, Risks, Cleaning, Checklist questions.

---

## 22. Reports

When an inspection is completed generate a professional report: header (company logo, property,
inspection date, inspector, next inspection), Property Summary, Overall Condition, Inspection
Checklist, Electricity Meter Reading (incl. photo), Fire Safety, Emergency Lighting, Front Garden,
Back Garden, Communal Kitchen, Communal Cleaning, Unit Inspections, Vacant Units, Maintenance
Issues, Risk Assessments, Photos, Inspector Notes, Inspector Signature, Date Submitted.

Include a summary such as "12 Passed, 3 Require Attention, 2 Maintenance Issues, 1 High Risk".

---

## 23. Dashboard

**Inspections**: Due today, Due this week, Overdue, Completed this month.
**Maintenance**: Open, High priority, Urgent, Overdue.
**Risks**: Critical risks, High risks, Outstanding actions.
**Cleaning**: Grade A/B, Grade C, Grade D/E.
**Properties**: Total active properties, Properties requiring attention.

---

## 24. Inspection Due Dates

Properties need recurring inspection scheduling (Last inspection → Frequency → Next inspection).

Frequency options: Weekly, Fortnightly, Monthly, Every 3 months, Every 6 months, Annually, Custom.

Show overdue inspections prominently.

---

## 25. Notifications

Later add: Inspection due, Inspection overdue, Maintenance due, Maintenance overdue, Critical risk
raised, High-risk issue outstanding, Cleaning issue overdue. Channels eventually: In-app, Email,
SMS/push notification.

---

## 26. Audit Log

Audit log: User, Action, Entity, Entity ID, Previous value, New value, Timestamp, IP/device where
appropriate.

Examples: Inspection submitted, Meter reading changed, Maintenance closed, Risk changed, Property
details edited.

---

## 27. Recommended Technology

**Database**: Microsoft SQL Server.

**Backend**: Python, FastAPI, SQLAlchemy, Pydantic, JWT Authentication, Pytest.

**Frontend**: React, JavaScript, HTML, CSS, React Router, Axios.

**Media**: Local development storage → production object/blob file storage.

**Reporting**: Backend-generated PDF reports.

**Deployment**: Backend API + React frontend + managed SQL Server database + file storage.

---

## 28. Recommended Repository Structure

```text
InspectIQ/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── security/
│   │   └── main.py
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── contexts/
│       ├── hooks/
│       ├── layouts/
│       ├── pages/
│       ├── routes/
│       └── services/
├── database/
│   ├── tables/
│   ├── constraints/
│   ├── indexes/
│   ├── seed/
│   ├── views/
│   ├── reports/
│   └── scripts/
├── docs/
│   ├── README.md
│   ├── PROJECT_PLAN.md
│   ├── AI_MEMORY.md
│   ├── AI_HANDOFF.md
│   ├── DATABASE.md
│   ├── API.md
│   ├── UI_GUIDELINES.md
│   └── CHANGELOG.md
└── prompts/
    ├── master_prompt.md
    ├── database_prompt.md
    ├── backend_prompt.md
    └── frontend_prompt.md
```

---

## 29. Main Database Tables (starting set)

```text
Companies, Users, Roles, UserRoles
Properties, PropertyContacts, PropertyAccess, Units
InspectionTemplates, InspectionSections, InspectionQuestions
Inspections, InspectionResponses
MeterReadings
CleaningInspections, CleaningAreas
MaintenanceIssues, MaintenanceUpdates
RiskAssessments
MediaFiles, Notes
Notifications, AuditLogs
```

Relationships should be designed properly with primary keys, foreign keys, indexes and
constraints.

---

## 30. Build Order

Do not ask AI "build this entire application." Build it in controlled phases — see the 22
numbered prompts under `prompts/` and the 20 phases below.

---

## 31. First Version / MVP

Login, Users, Roles, Properties, Units, Property access information, Inspection templates, Start
inspection, Inspection checklist, Notes, Pictures, Electricity meter (manual + OCR/AI), Fire
safety, Emergency lighting, Gardens, Communal kitchen, Cleaning grades, Vacant units, Maintenance
issues, Risk assessments, Inspection submission, Next inspection date, Inspection history, PDF
report, Dashboard.

---

## 32. Version 2 (future)

Offline inspection mode, PWA, Push notifications, Email notifications, Contractor portal, Client
portal, Digital signatures, QR codes per property/unit, Recurring inspection automation, Calendar,
Contractor quotations, Maintenance costs, Invoices, SLA tracking, Cleaning schedules, AI photo
analysis, AI defect identification, AI report summaries, Voice-to-notes, GPS check-in,
Before/after photo comparison, Custom inspection templates, Custom branding, Multiple companies,
Subscription/billing.

---

## 33. Version 3 — Commercial SaaS (future)

Management Company → Portfolio → Properties → Units → Inspections → Maintenance / Risks /
Cleaning → Contractors → Reports.

---

## 34. Most Important Development Rule

Do not build database + API + frontend + AI + reports all at the same time.

**Phase order**: 1 Architecture · 2 SQL database · 3 Sample data + SQL queries · 4 FastAPI
foundation · 5 Authentication · 6 Properties + units · 7 Inspection templates · 8 Inspection
engine · 9 Photos/videos · 10 Maintenance · 11 Cleaning · 12 Vacant units · 13 Risk assessments ·
14 Meter OCR/AI · 15 Dashboard · 16 React frontend · 17 PDF reports · 18 Testing · 19 Security ·
20 Deployment.

Get each phase working and committed to Git before moving to the next.

---

## Owner's design guidance (given alongside the scope)

- **Make the inspection checklist configurable from day one.** Template → Sections → Questions →
  Inspection → Responses, not hard-coded fields like `FrontGardenOK`/`KitchenClean`. This matters
  a lot if the project ever becomes commercial software.
- **Build the UI around the inspector's phone first.** Desktop is for management, reports,
  dashboards, and admin; mobile is where the actual job happens.
- **Start with Prompt 1, then Prompt 2.** Don't start React or AI meter recognition yet — get the
  database design right first.
- This project has more commercial potential than PropertyManager because the inspection engine
  can eventually serve property inspections, cleaning audits, fire-safety checks, maintenance
  inspections, void inspections, handovers, snagging, and compliance checks — without separate
  applications for each.
