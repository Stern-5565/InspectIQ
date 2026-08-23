# Master Prompt — Project Architecture

Use this to (re-)establish the project's architecture with a fresh AI session. Full detail lives
in `../docs/SCOPE.md` and `../docs/PROJECT_PLAN.md`.

```text
I am building a professional Property Inspection & Compliance Management System (InspectIQ).

The software will be used by contractors, property management companies, project managers and
property inspectors.

Technology stack:

Database: Microsoft SQL Server
Backend: Python, FastAPI, SQLAlchemy, Pydantic, JWT authentication, Pytest
Frontend: React, JavaScript, React Router, Axios, HTML/CSS

The system needs to support: Companies, Users and role-based permissions, Properties, Property
contacts, Property access information, Units, Vacant units, Inspection templates, Inspection
sections, Inspection questions, Inspections, Inspection responses, Photos, Videos, Electricity
meter readings, AI/OCR meter reading detection with human confirmation, Fire alarms, Emergency
lighting, Gardens, Communal kitchens, Communal areas, Communal cleaning grading, Maintenance
issues, Maintenance history, Risk assessments, Notes, Inspection scheduling, Reports,
Notifications, Audit logs.

The application must be mobile-first because inspectors will use it while walking around
properties.

Do not write the application yet. First design the complete architecture.

Give me: system architecture, main modules, database entities, relationships, backend
architecture, frontend architecture, authentication architecture, media/file architecture,
reporting architecture, recommended folder structure, development phases, important security
considerations, important database design decisions, future scalability considerations.

Keep business logic out of API route/controller files. Use services and repositories where
appropriate.

The architecture should be professional enough to use as a portfolio project and eventually
develop into a commercial SaaS product.
```
