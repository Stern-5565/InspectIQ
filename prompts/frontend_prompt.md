# Frontend Prompts — Phase 16 (+17 mobile screen)

Covers Prompts 16 and 17 from `../docs/SCOPE.md` (full text there verbatim).

## Prompt 16 — React Frontend

```text
Build the React frontend for InspectIQ. The UI must be mobile-first.

Primary use case: an inspector walks around a property using a smartphone.

Main pages: Login, Dashboard, Properties, Property Details, Inspection List, Start Inspection,
Inspection Sections, Inspection Question, Photo/Video Upload, Meter Reading, Maintenance Issue,
Risk Assessment, Cleaning Assessment, Vacant Unit, Inspection Review, Submit Inspection,
Inspection Report, Maintenance Dashboard, Risk Dashboard, Admin Settings.

Use: React, React Router, Axios, reusable components, authentication context, protected routes.

Reusable components: StatusBadge, PriorityBadge, RiskBadge, CleaningGradeBadge, PhotoUploader,
VideoUploader, NotesInput, InspectionQuestion, SectionProgress, MaintenanceIssueForm,
RiskAssessmentForm, LoadingSpinner, ConfirmationModal.

Keep API logic out of page components — use an API/service layer. Clean professional
property-management style. Functionality and usability first, animations later.
```

## Prompt 17 — Mobile Inspection Screen

```text
Design and implement the most important screen in the application: the mobile inspection screen.

Top: property name, address, inspection date, completion percentage. Then inspection sections
each with a completion percentage. Inside each question: question text, answer controls, notes,
Add Photo, Add Video, Create Maintenance Issue, Create Risk, Previous/Next.

Automatically save responses after changes. Clearly show: Answered, Unanswered, Failed,
Maintenance raised, Risk raised.

Require as few taps as possible — an inspector may be holding the phone in one hand while walking
around the property.
```
