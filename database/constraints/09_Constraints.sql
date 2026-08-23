-- CHECK constraints for every enum-like column deferred from the tables/ files, plus the
-- real enforcement mechanism for the "soft-delete only" rule (PROJECT_PLAN.md section 13.1 sign-off).
--
-- Value lists come directly from the scope doc where it enumerates them explicitly (scope
-- section noted per constraint). Where the scope doc mentions a field ("Property status",
-- "Status" on RiskAssessments/CleaningInspections/MaintenanceUpdates) without giving exact
-- values, a reasonable default list is used and flagged as INTERPRETIVE below - worth a quick
-- sanity check against real usage once the app exists, not treated as scope-mandated.

USE InspectIQDb;
GO

-------------------------------------------------------------------------------------------
-- Properties (scope §5, §24)
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.Properties ADD CONSTRAINT CK_Properties_PropertyType
    CHECK (PropertyType IN ('HMO', 'BlockOfFlats', 'ResidentialHouse', 'CommercialBuilding', 'MixedUse', 'Office', 'Other'));

-- INTERPRETIVE: scope §5 lists "Property status" as a field but doesn't enumerate values
-- (separately from the "Active/inactive" boolean, which is IsActive). Default list below.
ALTER TABLE dbo.Properties ADD CONSTRAINT CK_Properties_PropertyStatus
    CHECK (PropertyStatus IN ('Active', 'UnderRefurbishment', 'ForSale', 'NotInUse', 'Other'));

ALTER TABLE dbo.Properties ADD CONSTRAINT CK_Properties_InspectionFrequency
    CHECK (InspectionFrequency IN ('Weekly', 'Fortnightly', 'Monthly', 'Quarterly', 'SemiAnnually', 'Annually', 'Custom'));
GO

-------------------------------------------------------------------------------------------
-- PropertyAccess
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.PropertyAccess ADD CONSTRAINT CK_PropertyAccess_AccessType
    CHECK (AccessType IN ('Key', 'Code', 'Fob', 'KeySafe', 'Agent', 'Other'));
GO

-------------------------------------------------------------------------------------------
-- Units (scope §6)
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.Units ADD CONSTRAINT CK_Units_OccupancyStatus
    CHECK (OccupancyStatus IN ('Occupied', 'Vacant', 'UnderRefurbishment', 'Unavailable', 'Unknown'));
GO

-------------------------------------------------------------------------------------------
-- InspectionQuestions (scope Prompt 2's answer-type list)
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.InspectionQuestions ADD CONSTRAINT CK_InspectionQuestions_AnswerType
    CHECK (AnswerType IN ('YesNo', 'PassFail', 'Condition', 'Text', 'Number', 'Date', 'MeterReading'));
GO

-------------------------------------------------------------------------------------------
-- Inspections (scope §8)
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.Inspections ADD CONSTRAINT CK_Inspections_Status
    CHECK (Status IN ('Scheduled', 'InProgress', 'Completed', 'Submitted', 'Cancelled'));

ALTER TABLE dbo.Inspections ADD CONSTRAINT CK_Inspections_OverallCondition
    CHECK (OverallCondition IS NULL OR OverallCondition IN ('Excellent', 'Good', 'Satisfactory', 'NeedsAttention', 'Poor', 'Critical'));
GO

-------------------------------------------------------------------------------------------
-- InspectionResponses (AnswerTypeSnapshot mirrors InspectionQuestions.AnswerType's domain)
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.InspectionResponses ADD CONSTRAINT CK_InspectionResponses_AnswerTypeSnapshot
    CHECK (AnswerTypeSnapshot IN ('YesNo', 'PassFail', 'Condition', 'Text', 'Number', 'Date', 'MeterReading'));
GO

-------------------------------------------------------------------------------------------
-- MeterReadings (scope §11)
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.MeterReadings ADD CONSTRAINT CK_MeterReadings_MeterType
    CHECK (MeterType IN ('Electricity', 'Gas', 'Water'));
GO

-------------------------------------------------------------------------------------------
-- CleaningAreas / CleaningInspections (scope §16)
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.CleaningAreas ADD CONSTRAINT CK_CleaningAreas_AreaType
    CHECK (AreaType IN ('Entrance', 'Hallway', 'Staircase', 'Landing', 'CommunalKitchen', 'CommunalBathroom', 'BinArea', 'Garden', 'LaundryArea', 'Lift', 'Other'));

ALTER TABLE dbo.CleaningInspections ADD CONSTRAINT CK_CleaningInspections_Grade
    CHECK (Grade IN ('A', 'B', 'C', 'D', 'E'));

-- INTERPRETIVE: scope §16 lists "Status" as a field without enumerating values.
ALTER TABLE dbo.CleaningInspections ADD CONSTRAINT CK_CleaningInspections_Status
    CHECK (Status IN ('Pending', 'Assigned', 'Completed'));
GO

-------------------------------------------------------------------------------------------
-- MaintenanceIssues / MaintenanceUpdates (scope §17, §18)
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.MaintenanceIssues ADD CONSTRAINT CK_MaintenanceIssues_Category
    CHECK (Category IN ('Electrical', 'Plumbing', 'Heating', 'FireSafety', 'EmergencyLighting', 'Cleaning', 'Garden', 'Structural', 'DoorsWindows', 'PestControl', 'Decoration', 'Appliance', 'Security', 'Other'));

ALTER TABLE dbo.MaintenanceIssues ADD CONSTRAINT CK_MaintenanceIssues_Priority
    CHECK (Priority IN ('Low', 'Medium', 'High', 'Urgent', 'Emergency'));

ALTER TABLE dbo.MaintenanceIssues ADD CONSTRAINT CK_MaintenanceIssues_Status
    CHECK (Status IN ('Open', 'Assigned', 'InProgress', 'Waiting', 'Completed', 'Closed'));

-- INTERPRETIVE: scope §18 describes a timeline of update "types" by example, not an
-- exhaustive enum.
ALTER TABLE dbo.MaintenanceUpdates ADD CONSTRAINT CK_MaintenanceUpdates_UpdateType
    CHECK (UpdateType IN ('StatusChange', 'Comment', 'PhotoUploaded'));
GO

-------------------------------------------------------------------------------------------
-- RiskAssessments (scope §19)
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.RiskAssessments ADD CONSTRAINT CK_RiskAssessments_Likelihood
    CHECK (Likelihood BETWEEN 1 AND 5);

ALTER TABLE dbo.RiskAssessments ADD CONSTRAINT CK_RiskAssessments_Severity
    CHECK (Severity BETWEEN 1 AND 5);

-- INTERPRETIVE: scope §19 lists "Status" as a field without enumerating values.
ALTER TABLE dbo.RiskAssessments ADD CONSTRAINT CK_RiskAssessments_Status
    CHECK (Status IN ('Open', 'ActionPlanned', 'Closed'));
GO

-------------------------------------------------------------------------------------------
-- Notifications (scope §25)
-------------------------------------------------------------------------------------------
ALTER TABLE dbo.Notifications ADD CONSTRAINT CK_Notifications_NotificationType
    CHECK (NotificationType IN ('InspectionDue', 'InspectionOverdue', 'MaintenanceDue', 'MaintenanceOverdue', 'CriticalRiskRaised', 'HighRiskOutstanding', 'CleaningIssueOverdue'));
GO

-------------------------------------------------------------------------------------------
-- Soft-delete-only enforcement (mandatory per the PROJECT_PLAN.md section 13.1 sign-off).
--
-- The repository layer must never issue DELETE against InspectionTemplates,
-- InspectionSections, or InspectionQuestions - but "the repository layer must never" is an
-- app-layer promise, and the whole point of the RiskScore computed column earlier was to
-- make guarantees structural rather than conventional wherever practical. These three
-- INSTEAD OF DELETE triggers do the same job here: a hard DELETE against any of these three
-- tables is rejected by the database itself, not just disallowed by code review.
-------------------------------------------------------------------------------------------
GO
CREATE TRIGGER dbo.trg_InspectionTemplates_PreventHardDelete
ON dbo.InspectionTemplates
INSTEAD OF DELETE
AS
BEGIN
    SET NOCOUNT ON;
    RAISERROR('InspectionTemplates is soft-delete only (UPDATE ... SET IsActive = 0). Hard deletes are blocked to protect InspectionResponses historical data - see docs/PROJECT_PLAN.md section 13.1.', 16, 1);
    ROLLBACK TRANSACTION;
END;
GO

CREATE TRIGGER dbo.trg_InspectionSections_PreventHardDelete
ON dbo.InspectionSections
INSTEAD OF DELETE
AS
BEGIN
    SET NOCOUNT ON;
    RAISERROR('InspectionSections is soft-delete only (UPDATE ... SET IsActive = 0). Hard deletes are blocked to protect InspectionResponses historical data - see docs/PROJECT_PLAN.md section 13.1.', 16, 1);
    ROLLBACK TRANSACTION;
END;
GO

CREATE TRIGGER dbo.trg_InspectionQuestions_PreventHardDelete
ON dbo.InspectionQuestions
INSTEAD OF DELETE
AS
BEGIN
    SET NOCOUNT ON;
    RAISERROR('InspectionQuestions is soft-delete only (UPDATE ... SET IsActive = 0). Hard deletes are blocked to protect InspectionResponses historical data - see docs/PROJECT_PLAN.md section 13.1.', 16, 1);
    ROLLBACK TRANSACTION;
END;
GO
