-- Non-clustered indexes. SQL Server does NOT auto-index FK columns (only PK/UNIQUE get one) -
-- PropertyManager's Prompt 30 review found exactly this gap after the fact (a filtered-on FK
-- with no index). Indexing FK/filter columns proactively here instead of waiting for a
-- performance-review phase to catch it.
--
-- Covers: every FK column that's realistically filtered or joined on, plus the columns behind
-- the Dashboard module's queries (scope §23 - due/overdue/open/priority/grade counts) and the
-- two polymorphic (EntityType, EntityId) lookup patterns (MediaFiles, Notes).

USE InspectIQDb;
GO

-- Required for the filtered indexes below (WHERE clauses) - same SET-option requirement as
-- computed columns.
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- Users
CREATE INDEX IX_Users_CompanyId ON dbo.Users (CompanyId);
GO

-- Properties
CREATE INDEX IX_Properties_CompanyId ON dbo.Properties (CompanyId);
CREATE INDEX IX_Properties_NextInspectionDue ON dbo.Properties (NextInspectionDue) WHERE IsActive = 1;
CREATE INDEX IX_Properties_PropertyStatus ON dbo.Properties (PropertyStatus) WHERE IsActive = 1;
GO

-- PropertyContacts / PropertyAccess / Units
CREATE INDEX IX_PropertyContacts_PropertyId ON dbo.PropertyContacts (PropertyId);
CREATE INDEX IX_PropertyAccess_PropertyId ON dbo.PropertyAccess (PropertyId);
CREATE INDEX IX_Units_PropertyId ON dbo.Units (PropertyId);
GO

-- Checklist engine
CREATE INDEX IX_InspectionTemplates_CompanyId ON dbo.InspectionTemplates (CompanyId);
CREATE INDEX IX_InspectionSections_TemplateId ON dbo.InspectionSections (InspectionTemplateId);
CREATE INDEX IX_InspectionQuestions_SectionId ON dbo.InspectionQuestions (InspectionSectionId);
GO

-- Inspections - Status/NextInspectionDueDate back the Dashboard's due/overdue counts directly.
CREATE INDEX IX_Inspections_PropertyId ON dbo.Inspections (PropertyId);
CREATE INDEX IX_Inspections_InspectorUserId ON dbo.Inspections (InspectorUserId);
CREATE INDEX IX_Inspections_Status ON dbo.Inspections (Status);
CREATE INDEX IX_Inspections_NextInspectionDueDate ON dbo.Inspections (NextInspectionDueDate);
GO

-- InspectionResponses
CREATE INDEX IX_InspectionResponses_InspectionId ON dbo.InspectionResponses (InspectionId);
CREATE INDEX IX_InspectionResponses_QuestionId ON dbo.InspectionResponses (InspectionQuestionId);
GO

-- MeterReadings
CREATE INDEX IX_MeterReadings_PropertyId ON dbo.MeterReadings (PropertyId);
CREATE INDEX IX_MeterReadings_InspectionResponseId ON dbo.MeterReadings (InspectionResponseId);
GO

-- Cleaning
CREATE INDEX IX_CleaningAreas_PropertyId ON dbo.CleaningAreas (PropertyId);
CREATE INDEX IX_CleaningInspections_InspectionId ON dbo.CleaningInspections (InspectionId);
CREATE INDEX IX_CleaningInspections_CleaningAreaId ON dbo.CleaningInspections (CleaningAreaId);
CREATE INDEX IX_CleaningInspections_Grade ON dbo.CleaningInspections (Grade);
GO

-- Vacant units
CREATE INDEX IX_VacantUnitInspections_InspectionId ON dbo.VacantUnitInspections (InspectionId);
CREATE INDEX IX_VacantUnitInspections_UnitId ON dbo.VacantUnitInspections (UnitId);
GO

-- MaintenanceIssues - Status/Priority/DueDate back the Dashboard's open/high-priority/
-- urgent/overdue counts directly; CompanyId backs the isolation queries this table's
-- denormalized CompanyId exists for (docs/DATABASE.md §9.5).
CREATE INDEX IX_MaintenanceIssues_CompanyId ON dbo.MaintenanceIssues (CompanyId);
CREATE INDEX IX_MaintenanceIssues_PropertyId ON dbo.MaintenanceIssues (PropertyId);
CREATE INDEX IX_MaintenanceIssues_Status ON dbo.MaintenanceIssues (Status);
CREATE INDEX IX_MaintenanceIssues_Priority ON dbo.MaintenanceIssues (Priority);
-- Filtered index predicates don't support NOT IN (SQL Server parser rejects it) - two <>
-- comparisons ANDed together is the supported equivalent.
CREATE INDEX IX_MaintenanceIssues_DueDate ON dbo.MaintenanceIssues (DueDate) WHERE Status <> 'Completed' AND Status <> 'Closed';
CREATE INDEX IX_MaintenanceIssues_AssignedUserId ON dbo.MaintenanceIssues (AssignedUserId);
GO

CREATE INDEX IX_MaintenanceUpdates_MaintenanceIssueId ON dbo.MaintenanceUpdates (MaintenanceIssueId);
GO

-- RiskAssessments - RiskLevel/Status back the Dashboard's critical/high/outstanding counts.
CREATE INDEX IX_RiskAssessments_CompanyId ON dbo.RiskAssessments (CompanyId);
CREATE INDEX IX_RiskAssessments_PropertyId ON dbo.RiskAssessments (PropertyId);
CREATE INDEX IX_RiskAssessments_RiskLevel ON dbo.RiskAssessments (RiskLevel);
CREATE INDEX IX_RiskAssessments_Status ON dbo.RiskAssessments (Status);
GO

CREATE INDEX IX_RiskMatrixLevels_CompanyId ON dbo.RiskMatrixLevels (CompanyId);
GO

-- MediaFiles / Notes - the (EntityType, EntityId) pair is the primary lookup pattern for both
-- polymorphic tables ("all photos for this maintenance issue"), so it's a composite index,
-- not two separate single-column ones.
CREATE INDEX IX_MediaFiles_CompanyId ON dbo.MediaFiles (CompanyId);
CREATE INDEX IX_MediaFiles_Entity ON dbo.MediaFiles (EntityType, EntityId);
GO

CREATE INDEX IX_Notes_CompanyId ON dbo.Notes (CompanyId);
CREATE INDEX IX_Notes_Entity ON dbo.Notes (EntityType, EntityId);
GO

-- Notifications - "unread notifications for this user" is the main query.
CREATE INDEX IX_Notifications_UserId_IsRead ON dbo.Notifications (UserId, IsRead);
GO

-- AuditLogs - lookups by entity or by company+time range.
CREATE INDEX IX_AuditLogs_CompanyId_Timestamp ON dbo.AuditLogs (CompanyId, Timestamp);
CREATE INDEX IX_AuditLogs_Entity ON dbo.AuditLogs (EntityType, EntityId);
GO
