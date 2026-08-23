# Database Prompts — Phases 2–4

Covers Prompts 2, 3, and 4 from `../docs/SCOPE.md`. Run in order; each phase should be committed
to git before starting the next.

## Prompt 2 — Database Design

```text
We are now starting the database phase of the Property Inspection & Compliance Management System
(InspectIQ).

Use Microsoft SQL Server and T-SQL.

Based on our agreed architecture, design the complete relational database.

Main entities include: Companies, Users, Roles, UserRoles, Properties, PropertyContacts,
PropertyAccess, Units, InspectionTemplates, InspectionSections, InspectionQuestions, Inspections,
InspectionResponses, MeterReadings, CleaningInspections, CleaningAreas, MaintenanceIssues,
MaintenanceUpdates, RiskAssessments, MediaFiles, Notes, Notifications, AuditLogs.

Requirements: proper primary keys, foreign keys, NOT NULL constraints, CHECK constraints, UNIQUE
constraints, useful indexes, CreatedAt/UpdatedAt where appropriate, CreatedBy where appropriate,
soft deletion where appropriate, consistent naming conventions, avoid duplicated data, proper
normalization, store file references instead of video/image binary data, preserve inspection
history even if templates later change.

Inspection questions need configurable answer types: YesNo, PassFail, Condition, Text, Number,
Date, MeterReading.

Maintenance issues must optionally reference: Property, Unit, Inspection, Inspection question.

Risk assessments must optionally reference an inspection and maintenance issue.

Before generating SQL: 1. List every table. 2. Explain its purpose. 3. List important
relationships. 4. Identify important design decisions. 5. Point out possible problems.

Then generate the SQL Server schema in logical files.
```

## Prompt 3 — SQL File Structure

```text
Create the SQL Server database scripts for InspectIQ using this structure:

database/
    00_CreateDatabase.sql
    tables/01_CoreTables.sql ... 08_NotificationAuditTables.sql
    constraints/09_Constraints.sql
    indexes/10_Indexes.sql
    seed/11_SeedRoles.sql, 12_SeedInspectionTemplate.sql, 13_SeedSampleData.sql
    views/14_InspectionViews.sql
    reports/15_DashboardQueries.sql
    scripts/00_RunAll.sql

Generate the scripts one file at a time. For every file: 1. Explain what it does. 2. Generate the
SQL. 3. Explain important constraints. 4. Give test queries. 5. Do not continue to the next file
until this file is logically complete.
```

## Prompt 4 — Default Inspection Template

```text
Create a default Monthly Property Inspection template for InspectIQ.

Sections: Property Access, General Property Condition, Electricity Meter, Fire Alarm, Smoke/Heat
Detectors, Emergency Lighting, Fire Doors, Front Garden, Back Garden, Entrance, Hallways,
Staircases, Communal Kitchen, Communal Bathrooms, Bin Area, Communal Cleaning, Units, Vacant
Units, Maintenance, Risk Assessment, General Notes.

For every section generate sensible professional inspection questions. Each question needs:
question text, answer type, sort order, whether notes are allowed, whether photo evidence is
allowed, whether photo evidence is required, whether maintenance can be raised, whether a risk can
be raised.

Do not make every question mandatory. Design the checklist so an inspector can realistically
complete it on a mobile phone.
```
