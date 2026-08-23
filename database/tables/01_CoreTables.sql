-- Core / tenancy tables: Companies, Roles, Users, UserRoles.
-- See docs/DATABASE.md §1 for design rationale.
--
-- CHECK constraints for enum-like columns are added later in constraints/09_Constraints.sql,
-- to keep table definitions focused on structure (columns/PK/FK/defaults) and value-domain
-- rules in one reviewable place. Nothing in this file has enum columns anyway - Companies/
-- Users/Roles/UserRoles are all structural, not status-driven.

USE InspectIQDb;
GO

CREATE TABLE dbo.Companies (
    CompanyId       INT IDENTITY(1,1)   NOT NULL,
    CompanyName     NVARCHAR(200)       NOT NULL,
    AddressLine1    NVARCHAR(200)       NULL,
    AddressLine2    NVARCHAR(200)       NULL,
    City            NVARCHAR(100)       NULL,
    Postcode        NVARCHAR(20)        NULL,
    Telephone       NVARCHAR(30)        NULL,
    Email           NVARCHAR(200)       NULL,
    LogoPath        NVARCHAR(500)       NULL,
    IsActive        BIT                 NOT NULL CONSTRAINT DF_Companies_IsActive DEFAULT (1),
    CreatedAt       DATETIME2           NOT NULL CONSTRAINT DF_Companies_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Companies PRIMARY KEY CLUSTERED (CompanyId)
);
GO

-- Fixed 5-role lookup (Administrator/Manager/Inspector/Maintenance/Viewer). Global, not
-- per-company - role *behavior* lives in application permission code, this table just gives
-- UserRoles a stable FK target. Seeded in seed/11_SeedRoles.sql, not user-editable in v1.
CREATE TABLE dbo.Roles (
    RoleId          INT IDENTITY(1,1)   NOT NULL,
    RoleName        NVARCHAR(50)        NOT NULL,
    Description     NVARCHAR(500)       NULL,
    CONSTRAINT PK_Roles PRIMARY KEY CLUSTERED (RoleId),
    CONSTRAINT UQ_Roles_RoleName UNIQUE (RoleName)
);
GO

CREATE TABLE dbo.Users (
    UserId          INT IDENTITY(1,1)   NOT NULL,
    CompanyId       INT                 NOT NULL,
    FirstName       NVARCHAR(100)       NOT NULL,
    LastName        NVARCHAR(100)       NOT NULL,
    Email           NVARCHAR(256)       NOT NULL,
    Phone           NVARCHAR(30)        NULL,
    PasswordHash    NVARCHAR(500)       NOT NULL,
    IsActive        BIT                 NOT NULL CONSTRAINT DF_Users_IsActive DEFAULT (1),
    CreatedAt       DATETIME2           NOT NULL CONSTRAINT DF_Users_CreatedAt DEFAULT (SYSUTCDATETIME()),
    LastLoginAt     DATETIME2           NULL,
    CONSTRAINT PK_Users PRIMARY KEY CLUSTERED (UserId),
    CONSTRAINT UQ_Users_Email UNIQUE (Email),
    CONSTRAINT FK_Users_Companies FOREIGN KEY (CompanyId) REFERENCES dbo.Companies (CompanyId)
);
GO

-- Users<->Roles, many-to-many. A join table (not a single RoleId on Users) even though v1 UI
-- likely assigns one role per user - see docs/DATABASE.md §1.
CREATE TABLE dbo.UserRoles (
    UserId          INT NOT NULL,
    RoleId          INT NOT NULL,
    CONSTRAINT PK_UserRoles PRIMARY KEY CLUSTERED (UserId, RoleId),
    CONSTRAINT FK_UserRoles_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId),
    CONSTRAINT FK_UserRoles_Roles FOREIGN KEY (RoleId) REFERENCES dbo.Roles (RoleId)
);
GO
