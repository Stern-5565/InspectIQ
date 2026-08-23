-- Two parts, deliberately separated:
--
-- PART A - global default risk matrix. This is CORE CONFIG, not demo data - every environment
-- (including production) needs it, since RiskAssessments.RiskLevel has nothing to snapshot
-- from without it. Safe and expected to run everywhere.
--
-- PART B - local-dev-only demo companies/properties/units. DO NOT run this against
-- production. Same lesson PropertyManager learned the hard way (its own seed script's
-- Password123! demo accounts were explicitly kept out of production - see that project's
-- deployment history) - applying it here from the start instead of relearning it.
--
-- Users are deliberately NOT seeded here. A real PasswordHash needs the actual hashing
-- algorithm Phase 5 (Authentication) decides on (PROJECT_PLAN.md §7) - inserting a fake
-- placeholder hash now would create rows that look like working logins but aren't. Demo users
-- get seeded once Phase 5 exists and can hash a real password correctly.
--
-- Idempotent by name/CompanyName checks throughout - safe to re-run.

USE InspectIQDb;
GO

-- Required for any INSERT/UPDATE/DELETE against Properties (has filtered indexes) or
-- RiskAssessments (has a PERSISTED computed column) - not just at their creation time. See
-- docs/AI_MEMORY.md's 2026-08-23 entry for the fuller explanation of this gotcha.
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-------------------------------------------------------------------------------------------
-- PART A: Global default risk matrix (scope §19). CompanyId NULL = usable by every company
-- unless they configure their own override, same pattern as InspectionTemplates.
-------------------------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM dbo.RiskMatrixLevels WHERE CompanyId IS NULL)
BEGIN
    INSERT INTO dbo.RiskMatrixLevels (CompanyId, MinScore, MaxScore, LevelName, SortOrder, ColorHint)
    VALUES
        (NULL, 1,  4,  'Low',      1, '#2E7D32'),
        (NULL, 5,  9,  'Medium',   2, '#F9A825'),
        (NULL, 10, 16, 'High',     3, '#EF6C00'),
        (NULL, 17, 25, 'Critical', 4, '#C62828');
    PRINT 'Global default risk matrix seeded.';
END
ELSE
    PRINT 'Global default risk matrix already exists - skipping.';
GO

-------------------------------------------------------------------------------------------
-- PART B: LOCAL DEV DEMO DATA ONLY. Two companies, to make cross-tenant isolation visually
-- obvious once the API exists (Company A's data should never be reachable by Company B's
-- users) - not just something Phase 19's security review has to take on faith.
-------------------------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM dbo.Companies WHERE CompanyName = 'Northgate Property Management')
BEGIN
    DECLARE @CompanyA INT, @CompanyB INT;
    DECLARE @PropA1 INT, @PropA2 INT, @PropA3 INT, @PropB1 INT;

    INSERT INTO dbo.Companies (CompanyName, AddressLine1, City, Postcode, Telephone, Email)
    VALUES ('Northgate Property Management', '4 Northgate Business Park', 'Manchester', 'M1 4AB', '0161 496 0100', 'info@northgatepm.example');
    SET @CompanyA = SCOPE_IDENTITY();

    INSERT INTO dbo.Companies (CompanyName, AddressLine1, City, Postcode, Telephone, Email)
    VALUES ('Bright Spaces Estates', '12 Riverside Court', 'Leeds', 'LS1 5JN', '0113 496 0200', 'hello@brightspaces.example');
    SET @CompanyB = SCOPE_IDENTITY();

    ----------------------------------------------------------------------------------------
    -- Northgate: 3 properties covering the property-type spread (HMO, block, house).
    ----------------------------------------------------------------------------------------
    -- LastInspectionDate/NextInspectionDue are deliberately spread across
    -- overdue/due-soon/comfortably-scheduled so the Dashboard queries (reports/
    -- 15_DashboardQueries.sql) have real, varied data to demonstrate against instead of
    -- every bucket showing zero.
    INSERT INTO dbo.Properties (CompanyId, PropertyName, AddressLine1, City, Postcode, PropertyType, PropertyStatus, NumberOfUnits, MainContactName, MainContactPhone, MainContactEmail, AccessInstructions, KeyLocation, InspectionFrequency, LastInspectionDate, NextInspectionDue, IsActive)
    VALUES (@CompanyA, '15 High Road', '15 High Road', 'Manchester', 'M14 5RT', 'HMO', 'Active', 4, 'Sarah Whitfield', '07700 900111', 'sarah.whitfield@example.com', 'Front door key safe, back door via side gate.', 'Key safe by front door, code held by office', 'Monthly', DATEADD(MONTH, -2, CAST(SYSUTCDATETIME() AS DATE)), DATEADD(DAY, -5, CAST(SYSUTCDATETIME() AS DATE)), 1);
    SET @PropA1 = SCOPE_IDENTITY();

    INSERT INTO dbo.Properties (CompanyId, PropertyName, AddressLine1, City, Postcode, PropertyType, PropertyStatus, NumberOfUnits, MainContactName, MainContactPhone, MainContactEmail, AccessInstructions, InspectionFrequency, LastInspectionDate, NextInspectionDue, IsActive)
    VALUES (@CompanyA, 'Elm Court', '22 Elm Court', 'Manchester', 'M2 3QP', 'BlockOfFlats', 'Active', 12, 'Concierge Desk', '07700 900222', 'concierge@elmcourt.example', 'Concierge on-site 8am-6pm; fob required for communal doors.', 'Quarterly', DATEADD(MONTH, -3, CAST(SYSUTCDATETIME() AS DATE)), DATEADD(DAY, 3, CAST(SYSUTCDATETIME() AS DATE)), 1);
    SET @PropA2 = SCOPE_IDENTITY();

    INSERT INTO dbo.Properties (CompanyId, PropertyName, AddressLine1, City, Postcode, PropertyType, PropertyStatus, NumberOfUnits, MainContactName, MainContactPhone, MainContactEmail, InspectionFrequency, LastInspectionDate, NextInspectionDue, IsActive)
    VALUES (@CompanyA, '8 Willow Grove', '8 Willow Grove', 'Manchester', 'M20 1LR', 'ResidentialHouse', 'Active', 1, 'Tom Baxter', '07700 900333', 'tom.baxter@example.com', 'Annually', DATEADD(MONTH, -1, CAST(SYSUTCDATETIME() AS DATE)), DATEADD(MONTH, 11, CAST(SYSUTCDATETIME() AS DATE)), 1);
    SET @PropA3 = SCOPE_IDENTITY();

    INSERT INTO dbo.Units (PropertyId, UnitNumber, Floor, OccupancyStatus) VALUES
        (@PropA1, 'Flat 1', 'Ground', 'Occupied'),
        (@PropA1, 'Flat 2', 'Ground', 'Occupied'),
        (@PropA1, 'Flat 3', 'First',  'Vacant'),
        (@PropA1, 'Flat 4', 'First',  'Occupied'),
        (@PropA1, 'Communal Area', 'Ground', 'Unknown');

    INSERT INTO dbo.Units (PropertyId, UnitNumber, Floor, OccupancyStatus) VALUES
        (@PropA2, 'Flat 1', 'Ground', 'Occupied'),
        (@PropA2, 'Flat 2', 'Ground', 'Occupied'),
        (@PropA2, 'Flat 3', 'First',  'Occupied'),
        (@PropA2, 'Flat 4', 'First',  'UnderRefurbishment');

    -- Communal cleaning areas configured for Elm Court, closing the onboarding gap flagged in
    -- docs/DATABASE.md §10.5 (a new property otherwise starts with zero configured areas).
    INSERT INTO dbo.CleaningAreas (PropertyId, AreaName, AreaType) VALUES
        (@PropA2, 'Main Entrance', 'Entrance'),
        (@PropA2, 'Ground Floor Hallway', 'Hallway'),
        (@PropA2, 'Staircase', 'Staircase'),
        (@PropA2, 'Bin Store', 'BinArea'),
        (@PropA2, 'Passenger Lift', 'Lift');

    ----------------------------------------------------------------------------------------
    -- Bright Spaces: one property, deliberately minimal - exists so an isolation query
    -- ("does Northgate's data ever return for a Bright Spaces user") has something real to
    -- test against, not to exercise every field.
    ----------------------------------------------------------------------------------------
    INSERT INTO dbo.Properties (CompanyId, PropertyName, AddressLine1, City, Postcode, PropertyType, PropertyStatus, NumberOfUnits, MainContactName, MainContactPhone, MainContactEmail, InspectionFrequency, IsActive)
    VALUES (@CompanyB, 'Riverside Office Suites', '12 Riverside Court', 'Leeds', 'LS1 5JN', 'Office', 'Active', 6, 'James Okafor', '07700 900444', 'james.okafor@example.com', 'SemiAnnually', 1);
    SET @PropB1 = SCOPE_IDENTITY();

    INSERT INTO dbo.Units (PropertyId, UnitNumber, Floor, OccupancyStatus) VALUES
        (@PropB1, 'Suite 1', 'Ground', 'Occupied'),
        (@PropB1, 'Suite 2', 'First',  'Vacant');

    PRINT 'Demo companies/properties/units seeded (Northgate: 3 properties, Bright Spaces: 1 property).';
END
ELSE
    PRINT 'Demo data already exists - skipping.';
GO
