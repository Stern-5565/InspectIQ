-- Dashboard queries (scope §23). Each block is a standalone, company-scoped query meant to be
-- lifted directly into DashboardRepository methods in Phase 15 - one query per metric rather
-- than one giant query, so each can be tested and indexed independently (indexes/10_Indexes.sql
-- already covers the Status/Priority/RiskLevel/Grade columns these filter on).
--
-- All queries take @CompanyId as a parameter - never return cross-company data. This file uses
-- a DECLARE for local testing; the real repository code binds @CompanyId from the authenticated
-- user, never from client input (docs/DATABASE.md §10.1).

USE InspectIQDb;
GO

DECLARE @CompanyId INT = (SELECT CompanyId FROM dbo.Companies WHERE CompanyName = 'Northgate Property Management');
DECLARE @Today DATE = CAST(SYSUTCDATETIME() AS DATE);
DECLARE @WeekEnd DATE = DATEADD(DAY, 7, @Today);
DECLARE @MonthStart DATE = DATEFROMPARTS(YEAR(@Today), MONTH(@Today), 1);

-------------------------------------------------------------------------------------------
-- INSPECTIONS
-------------------------------------------------------------------------------------------
-- ISNULL(...,0) throughout this file: SUM() over zero matching rows returns NULL, not 0 - a
-- dashboard card must never render NULL as "no data", it needs a real zero. This was caught
-- by actually running the query against a company with no maintenance/risk/cleaning rows yet,
-- not assumed.
SELECT
    ISNULL(SUM(CASE WHEN p.NextInspectionDue = @Today THEN 1 ELSE 0 END), 0) AS DueToday,
    ISNULL(SUM(CASE WHEN p.NextInspectionDue > @Today AND p.NextInspectionDue <= @WeekEnd THEN 1 ELSE 0 END), 0) AS DueThisWeek,
    ISNULL(SUM(CASE WHEN p.NextInspectionDue < @Today THEN 1 ELSE 0 END), 0) AS Overdue
FROM dbo.Properties p
WHERE p.CompanyId = @CompanyId AND p.IsActive = 1 AND p.NextInspectionDue IS NOT NULL;

SELECT COUNT(*) AS CompletedThisMonth
FROM dbo.Inspections i
JOIN dbo.Properties p ON p.PropertyId = i.PropertyId
WHERE p.CompanyId = @CompanyId
  AND i.Status IN ('Completed', 'Submitted')
  AND i.CompletedAt >= @MonthStart;

-------------------------------------------------------------------------------------------
-- MAINTENANCE
-------------------------------------------------------------------------------------------
SELECT
    ISNULL(SUM(CASE WHEN Status NOT IN ('Completed', 'Closed') THEN 1 ELSE 0 END), 0) AS OpenCount,
    ISNULL(SUM(CASE WHEN Priority = 'High' AND Status NOT IN ('Completed', 'Closed') THEN 1 ELSE 0 END), 0) AS HighPriority,
    ISNULL(SUM(CASE WHEN Priority IN ('Urgent', 'Emergency') AND Status NOT IN ('Completed', 'Closed') THEN 1 ELSE 0 END), 0) AS UrgentOrEmergency,
    ISNULL(SUM(CASE WHEN DueDate < @Today AND Status NOT IN ('Completed', 'Closed') THEN 1 ELSE 0 END), 0) AS OverdueCount
FROM dbo.MaintenanceIssues
WHERE CompanyId = @CompanyId;

-------------------------------------------------------------------------------------------
-- RISKS
-------------------------------------------------------------------------------------------
SELECT
    ISNULL(SUM(CASE WHEN RiskLevel = 'Critical' AND Status IN ('Open', 'ActionPlanned') THEN 1 ELSE 0 END), 0) AS CriticalCount,
    ISNULL(SUM(CASE WHEN RiskLevel = 'High' AND Status IN ('Open', 'ActionPlanned') THEN 1 ELSE 0 END), 0) AS HighCount,
    ISNULL(SUM(CASE WHEN Status IN ('Open', 'ActionPlanned') THEN 1 ELSE 0 END), 0) AS OutstandingCount
FROM dbo.RiskAssessments
WHERE CompanyId = @CompanyId;

-------------------------------------------------------------------------------------------
-- CLEANING - "current" grade per area is its most recent CleaningInspection (a
-- point-in-time assessment tied to a specific Inspection, not a stored current-state
-- column - see docs/DATABASE.md §5). ROW_NUMBER() picks the latest one per area.
-------------------------------------------------------------------------------------------
;WITH LatestGradePerArea AS (
    SELECT
        ca.PropertyId,
        ci.CleaningAreaId,
        ci.Grade,
        ROW_NUMBER() OVER (PARTITION BY ci.CleaningAreaId ORDER BY i.InspectionDate DESC, ci.CleaningInspectionId DESC) AS rn
    FROM dbo.CleaningInspections ci
    JOIN dbo.CleaningAreas ca ON ca.CleaningAreaId = ci.CleaningAreaId
    JOIN dbo.Inspections i ON i.InspectionId = ci.InspectionId
    JOIN dbo.Properties p ON p.PropertyId = ca.PropertyId
    WHERE p.CompanyId = @CompanyId
)
SELECT
    ISNULL(SUM(CASE WHEN Grade IN ('A', 'B') THEN 1 ELSE 0 END), 0) AS GradeAOrB,
    ISNULL(SUM(CASE WHEN Grade = 'C' THEN 1 ELSE 0 END), 0) AS GradeC,
    ISNULL(SUM(CASE WHEN Grade IN ('D', 'E') THEN 1 ELSE 0 END), 0) AS GradeDOrE
FROM LatestGradePerArea
WHERE rn = 1;

-------------------------------------------------------------------------------------------
-- PROPERTIES - "requiring attention" is a rollup, not a stored flag: an active property
-- with an overdue inspection, an open Urgent/Emergency maintenance issue, or an open
-- Critical risk. Deliberately not evaluating cleaning grade here - a single poor grade on
-- one communal area is already visible via the Cleaning card above, doesn't need to also
-- flag the whole property as "requiring attention" and risk over-alerting.
-------------------------------------------------------------------------------------------
SELECT
    (SELECT COUNT(*) FROM dbo.Properties WHERE CompanyId = @CompanyId AND IsActive = 1) AS TotalActiveProperties,
    (SELECT COUNT(DISTINCT p.PropertyId)
     FROM dbo.Properties p
     WHERE p.CompanyId = @CompanyId AND p.IsActive = 1
       AND (
            (p.NextInspectionDue IS NOT NULL AND p.NextInspectionDue < @Today)
            OR EXISTS (SELECT 1 FROM dbo.MaintenanceIssues m WHERE m.PropertyId = p.PropertyId AND m.Priority IN ('Urgent', 'Emergency') AND m.Status NOT IN ('Completed', 'Closed'))
            OR EXISTS (SELECT 1 FROM dbo.RiskAssessments r WHERE r.PropertyId = p.PropertyId AND r.RiskLevel = 'Critical' AND r.Status IN ('Open', 'ActionPlanned'))
           )
    ) AS PropertiesRequiringAttention;

-------------------------------------------------------------------------------------------
-- RECENT ACTIVITY (scope §23's dashboard also lists this) - most recent 10 inspections,
-- maintenance issues, and high-risk items, for an activity feed.
-------------------------------------------------------------------------------------------
SELECT TOP 10 InspectionId, PropertyName, InspectorName, Status, InspectionDate
FROM dbo.vw_InspectionSummary
WHERE CompanyId = @CompanyId
ORDER BY InspectionDate DESC;

SELECT TOP 10 MaintenanceIssueId, PropertyName, Title, Priority, Status, ReportedDate
FROM dbo.vw_OpenMaintenanceIssues
WHERE CompanyId = @CompanyId
ORDER BY ReportedDate DESC;

SELECT TOP 10 RiskAssessmentId, PropertyName, Hazard, RiskLevel, RiskScore
FROM dbo.vw_ActiveRiskAssessments
WHERE CompanyId = @CompanyId AND RiskLevel IN ('High', 'Critical')
ORDER BY RiskScore DESC;
GO
