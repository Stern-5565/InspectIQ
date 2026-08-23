-- Reusable read-only views. These are data-shaping only (joins, column selection) - no business
-- rules live here (e.g. inspection completion % is deliberately NOT computed in a view; per
-- PROJECT_PLAN.md §11 Phase 8, that's a service-layer calculation, not a SQL concern, matching
-- the "no business logic in the wrong layer" rule applied throughout this project).

USE InspectIQDb;
GO

-------------------------------------------------------------------------------------------
-- vw_InspectionSummary - one row per inspection with human-readable property/inspector
-- names, for list screens and reports. Joins only, no derived/business columns.
-------------------------------------------------------------------------------------------
CREATE OR ALTER VIEW dbo.vw_InspectionSummary AS
SELECT
    i.InspectionId,
    i.PropertyId,
    p.PropertyName,
    p.CompanyId,
    i.InspectorUserId,
    u.FirstName + ' ' + u.LastName AS InspectorName,
    i.InspectionType,
    i.InspectionDate,
    i.Status,
    i.OverallCondition,
    i.NextInspectionDueDate,
    i.SubmittedAt
FROM dbo.Inspections i
JOIN dbo.Properties p ON p.PropertyId = i.PropertyId
JOIN dbo.Users u ON u.UserId = i.InspectorUserId;
GO

-------------------------------------------------------------------------------------------
-- vw_OverdueInspections - active properties whose next inspection is due or overdue.
-- "Overdue" and "due soon" thresholds are report-time concerns (Dashboard buckets them into
-- today/this week/overdue), so this view exposes the raw date + days-overdue, not pre-bucketed
-- categories - reports/15_DashboardQueries.sql does the bucketing.
-------------------------------------------------------------------------------------------
CREATE OR ALTER VIEW dbo.vw_OverdueInspections AS
SELECT
    p.PropertyId,
    p.CompanyId,
    p.PropertyName,
    p.NextInspectionDue,
    DATEDIFF(DAY, p.NextInspectionDue, CAST(SYSUTCDATETIME() AS DATE)) AS DaysOverdue
FROM dbo.Properties p
WHERE p.IsActive = 1
  AND p.NextInspectionDue IS NOT NULL
  AND p.NextInspectionDue <= CAST(SYSUTCDATETIME() AS DATE);
GO

-------------------------------------------------------------------------------------------
-- vw_OpenMaintenanceIssues - open/in-progress issues with property/unit/assignee names.
-------------------------------------------------------------------------------------------
CREATE OR ALTER VIEW dbo.vw_OpenMaintenanceIssues AS
SELECT
    m.MaintenanceIssueId,
    m.CompanyId,
    m.PropertyId,
    p.PropertyName,
    m.UnitId,
    un.UnitNumber,
    m.Title,
    m.Category,
    m.Priority,
    m.Status,
    m.AssignedUserId,
    au.FirstName + ' ' + au.LastName AS AssignedUserName,
    m.ReportedDate,
    m.DueDate
FROM dbo.MaintenanceIssues m
JOIN dbo.Properties p ON p.PropertyId = m.PropertyId
LEFT JOIN dbo.Units un ON un.UnitId = m.UnitId
LEFT JOIN dbo.Users au ON au.UserId = m.AssignedUserId
WHERE m.Status NOT IN ('Completed', 'Closed');
GO

-------------------------------------------------------------------------------------------
-- vw_ActiveRiskAssessments - open/action-planned risks with property name, highest score
-- first. RiskScore/RiskLevel come straight from the table (computed column + write-time
-- snapshot respectively) - this view doesn't recalculate anything.
-------------------------------------------------------------------------------------------
CREATE OR ALTER VIEW dbo.vw_ActiveRiskAssessments AS
SELECT
    r.RiskAssessmentId,
    r.CompanyId,
    r.PropertyId,
    p.PropertyName,
    r.Hazard,
    r.Likelihood,
    r.Severity,
    r.RiskScore,
    r.RiskLevel,
    r.Status,
    r.ResponsiblePersonUserId,
    r.TargetCompletionDate
FROM dbo.RiskAssessments r
JOIN dbo.Properties p ON p.PropertyId = r.PropertyId
WHERE r.Status IN ('Open', 'ActionPlanned');
GO

-------------------------------------------------------------------------------------------
-- vw_PropertyUnitCounts - declared vs. actual unit counts, surfacing the drift documented
-- in docs/DATABASE.md §10.3 (Properties.NumberOfUnits is a declared count, not a live
-- COUNT(Units) - the two are allowed to diverge, but this view makes the gap queryable
-- rather than silently invisible).
-------------------------------------------------------------------------------------------
CREATE OR ALTER VIEW dbo.vw_PropertyUnitCounts AS
SELECT
    p.PropertyId,
    p.CompanyId,
    p.PropertyName,
    p.NumberOfUnits AS DeclaredUnitCount,
    COUNT(u.UnitId) AS ActualUnitCount
FROM dbo.Properties p
LEFT JOIN dbo.Units u ON u.PropertyId = p.PropertyId AND u.IsActive = 1
WHERE p.IsActive = 1
GROUP BY p.PropertyId, p.CompanyId, p.PropertyName, p.NumberOfUnits;
GO
