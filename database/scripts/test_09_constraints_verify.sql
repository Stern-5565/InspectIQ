-- Throwaway verification for constraints/09_Constraints.sql: CHECK constraints and the
-- soft-delete-only triggers. Not part of the run-all sequence.
USE InspectIQDb;
GO

-- RiskAssessments has a PERSISTED computed column - any DML against it (not just CREATE
-- TABLE) needs these ON for this session. Real gotcha for hand-written scripts; SQLAlchemy/
-- pyodbc set this by default so the app itself won't hit it, but seed scripts will.
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- 1. CHECK constraint: invalid PropertyType must fail.
BEGIN TRY
    INSERT INTO dbo.Companies (CompanyName) VALUES ('TMP Check Co');
    DECLARE @CompanyId INT = SCOPE_IDENTITY();
    INSERT INTO dbo.Properties (CompanyId, PropertyName, AddressLine1, Postcode, PropertyType, PropertyStatus, InspectionFrequency)
    VALUES (@CompanyId, 'TMP Bad Type', '1 St', 'PC1', 'NotARealType', 'Active', 'Monthly');
    PRINT '--- FAIL: invalid PropertyType was allowed ---';
END TRY
BEGIN CATCH
    PRINT '--- PASS: invalid PropertyType correctly rejected: ' + ERROR_MESSAGE() + ' ---';
END CATCH

-- 2. CHECK constraint: valid PropertyType must succeed.
BEGIN TRY
    INSERT INTO dbo.Properties (CompanyId, PropertyName, AddressLine1, Postcode, PropertyType, PropertyStatus, InspectionFrequency)
    VALUES (@CompanyId, 'TMP Good Type', '1 St', 'PC1', 'HMO', 'Active', 'Monthly');
    PRINT '--- PASS: valid PropertyType accepted ---';
END TRY
BEGIN CATCH
    PRINT '--- FAIL: valid PropertyType was rejected: ' + ERROR_MESSAGE() + ' ---';
END CATCH

-- 3. RiskAssessments.Likelihood CHECK (1-5).
BEGIN TRY
    INSERT INTO dbo.RiskAssessments (CompanyId, PropertyId, Hazard, Likelihood, Severity, RiskLevel)
    SELECT @CompanyId, PropertyId, 'TMP hazard', 9, 3, 'High' FROM dbo.Properties WHERE PropertyName = 'TMP Good Type';
    PRINT '--- FAIL: Likelihood=9 was allowed ---';
END TRY
BEGIN CATCH
    PRINT '--- PASS: Likelihood=9 correctly rejected: ' + ERROR_MESSAGE() + ' ---';
END CATCH

-- 4. RiskScore computed column actually computes (and can't be targeted by INSERT column list).
DECLARE @PropId INT = (SELECT PropertyId FROM dbo.Properties WHERE PropertyName = 'TMP Good Type');
INSERT INTO dbo.RiskAssessments (CompanyId, PropertyId, Hazard, Likelihood, Severity, RiskLevel)
VALUES (@CompanyId, @PropId, 'TMP hazard 2', 4, 5, 'Critical');
SELECT RiskAssessmentId, Likelihood, Severity, RiskScore, RiskLevel
FROM dbo.RiskAssessments WHERE PropertyId = @PropId;

-- 5. Soft-delete-only trigger: hard DELETE against InspectionTemplates must be rejected.
INSERT INTO dbo.InspectionTemplates (TemplateName) VALUES ('TMP Delete Test Template');
DECLARE @TemplateId INT = SCOPE_IDENTITY();
BEGIN TRY
    DELETE FROM dbo.InspectionTemplates WHERE InspectionTemplateId = @TemplateId;
    PRINT '--- FAIL: hard DELETE on InspectionTemplates was allowed ---';
END TRY
BEGIN CATCH
    PRINT '--- PASS: hard DELETE on InspectionTemplates correctly blocked: ' + ERROR_MESSAGE() + ' ---';
END CATCH

-- Confirm the row is still there (trigger rolled back the delete, not just raised a warning).
SELECT COUNT(*) AS StillExists FROM dbo.InspectionTemplates WHERE InspectionTemplateId = @TemplateId;

-- Soft-delete (the correct path) must still work fine.
UPDATE dbo.InspectionTemplates SET IsActive = 0 WHERE InspectionTemplateId = @TemplateId;
SELECT IsActive FROM dbo.InspectionTemplates WHERE InspectionTemplateId = @TemplateId;

-- Cleanup.
DELETE FROM dbo.RiskAssessments WHERE PropertyId = @PropId;
-- InspectionTemplates row can't be hard-deleted by design - remove it via the trigger's own
-- documented escape hatch: none exists on purpose, so for cleanup here we disable the trigger,
-- delete, then re-enable. This is a test-only maneuver, never something app code should do.
DISABLE TRIGGER dbo.trg_InspectionTemplates_PreventHardDelete ON dbo.InspectionTemplates;
DELETE FROM dbo.InspectionTemplates WHERE InspectionTemplateId = @TemplateId;
ENABLE TRIGGER dbo.trg_InspectionTemplates_PreventHardDelete ON dbo.InspectionTemplates;

DELETE FROM dbo.Properties WHERE CompanyId = @CompanyId;
DELETE FROM dbo.Companies WHERE CompanyId = @CompanyId;

PRINT '--- Cleanup complete ---';
SELECT COUNT(*) AS LeftoverTestRows FROM dbo.Companies WHERE CompanyName = 'TMP Check Co';
GO
