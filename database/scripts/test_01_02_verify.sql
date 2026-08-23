-- Throwaway verification script for tables/01_CoreTables.sql and 02_PropertyTables.sql.
-- Not part of the run-all sequence - ad hoc, run manually, cleans up after itself.
USE InspectIQDb;
GO

-- 1. Happy path: full insert chain works.
DECLARE @CompanyId INT, @UserId INT, @PropertyId INT, @UnitId INT;

INSERT INTO dbo.Roles (RoleName, Description) VALUES ('TestRole_TMP', 'throwaway');
INSERT INTO dbo.Companies (CompanyName, Email) VALUES ('Test Co TMP', 'testco@example.com');
SET @CompanyId = SCOPE_IDENTITY();

INSERT INTO dbo.Users (CompanyId, FirstName, LastName, Email, PasswordHash)
VALUES (@CompanyId, 'Test', 'User', 'test.user.tmp@example.com', 'hash');
SET @UserId = SCOPE_IDENTITY();

INSERT INTO dbo.UserRoles (UserId, RoleId)
SELECT @UserId, RoleId FROM dbo.Roles WHERE RoleName = 'TestRole_TMP';

INSERT INTO dbo.Properties (CompanyId, PropertyName, AddressLine1, Postcode, PropertyType, PropertyStatus, InspectionFrequency, CreatedBy)
VALUES (@CompanyId, 'Test Property TMP', '1 Test Street', 'TE5 7ST', 'HMO', 'Active', 'Monthly', @UserId);
SET @PropertyId = SCOPE_IDENTITY();

INSERT INTO dbo.PropertyContacts (PropertyId, ContactName, ContactType) VALUES (@PropertyId, 'Out of hours contact', 'OutOfHours');
INSERT INTO dbo.PropertyAccess (PropertyId, AccessType, Location) VALUES (@PropertyId, 'KeySafe', 'Front porch');
INSERT INTO dbo.Units (PropertyId, UnitNumber, OccupancyStatus) VALUES (@PropertyId, 'Flat 1', 'Occupied');
SET @UnitId = SCOPE_IDENTITY();

PRINT '--- Happy path insert chain: OK ---';
SELECT c.CompanyName, u.Email AS UserEmail, p.PropertyName, un.UnitNumber
FROM dbo.Companies c
JOIN dbo.Users u ON u.CompanyId = c.CompanyId
JOIN dbo.Properties p ON p.CompanyId = c.CompanyId
JOIN dbo.Units un ON un.PropertyId = p.PropertyId
WHERE c.CompanyId = @CompanyId;

-- 2. UNIQUE constraint: duplicate email must fail.
BEGIN TRY
    INSERT INTO dbo.Users (CompanyId, FirstName, LastName, Email, PasswordHash)
    VALUES (@CompanyId, 'Dup', 'User', 'test.user.tmp@example.com', 'hash');
    PRINT '--- FAIL: duplicate email was allowed ---';
END TRY
BEGIN CATCH
    PRINT '--- PASS: duplicate email correctly rejected: ' + ERROR_MESSAGE() + ' ---';
END CATCH

-- 3. FK constraint: bad CompanyId must fail.
BEGIN TRY
    INSERT INTO dbo.Users (CompanyId, FirstName, LastName, Email, PasswordHash)
    VALUES (-999, 'Bad', 'FK', 'bad.fk.tmp@example.com', 'hash');
    PRINT '--- FAIL: invalid CompanyId FK was allowed ---';
END TRY
BEGIN CATCH
    PRINT '--- PASS: invalid CompanyId correctly rejected: ' + ERROR_MESSAGE() + ' ---';
END CATCH

-- Cleanup - delete in FK-dependency order.
DELETE FROM dbo.Units WHERE PropertyId = @PropertyId;
DELETE FROM dbo.PropertyAccess WHERE PropertyId = @PropertyId;
DELETE FROM dbo.PropertyContacts WHERE PropertyId = @PropertyId;
DELETE FROM dbo.Properties WHERE PropertyId = @PropertyId;
DELETE FROM dbo.UserRoles WHERE UserId = @UserId;
DELETE FROM dbo.Users WHERE CompanyId = @CompanyId;
DELETE FROM dbo.Roles WHERE RoleName = 'TestRole_TMP';
DELETE FROM dbo.Companies WHERE CompanyId = @CompanyId;

PRINT '--- Cleanup complete ---';

-- Verify no leftover test rows.
SELECT COUNT(*) AS LeftoverTestRows FROM dbo.Companies WHERE CompanyName = 'Test Co TMP';
GO
