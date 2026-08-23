-- Property structure: Properties, PropertyContacts, PropertyAccess, Units.
-- See docs/DATABASE.md §2 for design rationale, including why PropertyContacts/PropertyAccess
-- are explicitly *additional* records, not duplicates of Properties' own main-contact/access
-- fields (a real ambiguity in the original scope doc, resolved there).

USE InspectIQDb;
GO

CREATE TABLE dbo.Properties (
    PropertyId          INT IDENTITY(1,1)  NOT NULL,
    CompanyId            INT                NOT NULL,
    PropertyName          NVARCHAR(200)      NOT NULL,
    AddressLine1          NVARCHAR(200)      NOT NULL,
    AddressLine2          NVARCHAR(200)      NULL,
    City                  NVARCHAR(100)      NULL,
    Postcode              NVARCHAR(20)       NOT NULL,
    PropertyType          NVARCHAR(50)       NOT NULL,  -- CHECK added in 09_Constraints.sql
    PropertyStatus        NVARCHAR(50)       NOT NULL,  -- CHECK added in 09_Constraints.sql
    NumberOfUnits         INT                NULL,       -- declared count; see docs/DATABASE.md §10.3
    MainContactName       NVARCHAR(200)      NULL,
    MainContactPhone      NVARCHAR(30)       NULL,
    MainContactEmail      NVARCHAR(200)      NULL,
    AccessInstructions    NVARCHAR(MAX)      NULL,
    KeyLocation           NVARCHAR(200)      NULL,
    AlarmAccessCode       NVARCHAR(50)       NULL,       -- sensitive; see docs/DATABASE.md §10.4
    GeneralNotes          NVARCHAR(MAX)      NULL,
    InspectionFrequency   NVARCHAR(30)       NOT NULL,  -- CHECK added in 09_Constraints.sql
    LastInspectionDate    DATE               NULL,
    NextInspectionDue     DATE               NULL,
    IsActive              BIT                NOT NULL CONSTRAINT DF_Properties_IsActive DEFAULT (1),
    CreatedAt             DATETIME2          NOT NULL CONSTRAINT DF_Properties_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CreatedBy             INT                NULL,
    CONSTRAINT PK_Properties PRIMARY KEY CLUSTERED (PropertyId),
    CONSTRAINT FK_Properties_Companies FOREIGN KEY (CompanyId) REFERENCES dbo.Companies (CompanyId),
    CONSTRAINT FK_Properties_CreatedBy FOREIGN KEY (CreatedBy) REFERENCES dbo.Users (UserId)
);
GO

-- Additional contacts beyond Properties' own MainContact* fields (out-of-hours, secondary,
-- contractor liaison). Not a duplicate of the primary contact - see file header.
CREATE TABLE dbo.PropertyContacts (
    PropertyContactId  INT IDENTITY(1,1)  NOT NULL,
    PropertyId          INT                NOT NULL,
    ContactName          NVARCHAR(200)      NOT NULL,
    ContactType          NVARCHAR(50)       NULL,
    Phone                NVARCHAR(30)       NULL,
    Email                NVARCHAR(200)      NULL,
    Notes                NVARCHAR(MAX)      NULL,
    IsActive              BIT                NOT NULL CONSTRAINT DF_PropertyContacts_IsActive DEFAULT (1),
    CONSTRAINT PK_PropertyContacts PRIMARY KEY CLUSTERED (PropertyContactId),
    CONSTRAINT FK_PropertyContacts_Properties FOREIGN KEY (PropertyId) REFERENCES dbo.Properties (PropertyId)
);
GO

-- Additional access methods beyond Properties.AccessInstructions/KeyLocation - for properties
-- with more than one entry point (multi-unit blocks, HMOs). See file header.
CREATE TABLE dbo.PropertyAccess (
    PropertyAccessId   INT IDENTITY(1,1)  NOT NULL,
    PropertyId           INT                NOT NULL,
    AccessType            NVARCHAR(30)       NOT NULL,  -- CHECK added in 09_Constraints.sql
    Location              NVARCHAR(200)      NULL,
    AccessCode            NVARCHAR(50)       NULL,       -- sensitive; see docs/DATABASE.md §10.4
    Notes                 NVARCHAR(MAX)      NULL,
    IsActive               BIT                NOT NULL CONSTRAINT DF_PropertyAccess_IsActive DEFAULT (1),
    CONSTRAINT PK_PropertyAccess PRIMARY KEY CLUSTERED (PropertyAccessId),
    CONSTRAINT FK_PropertyAccess_Properties FOREIGN KEY (PropertyId) REFERENCES dbo.Properties (PropertyId)
);
GO

CREATE TABLE dbo.Units (
    UnitId               INT IDENTITY(1,1)  NOT NULL,
    PropertyId            INT                NOT NULL,
    UnitNumber            NVARCHAR(50)       NOT NULL,
    Floor                 NVARCHAR(30)       NULL,
    OccupancyStatus       NVARCHAR(30)       NOT NULL,  -- CHECK added in 09_Constraints.sql
    TenantOccupierName    NVARCHAR(200)      NULL,
    Notes                 NVARCHAR(MAX)      NULL,
    IsActive               BIT                NOT NULL CONSTRAINT DF_Units_IsActive DEFAULT (1),
    CreatedAt              DATETIME2          NOT NULL CONSTRAINT DF_Units_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Units PRIMARY KEY CLUSTERED (UnitId),
    CONSTRAINT FK_Units_Properties FOREIGN KEY (PropertyId) REFERENCES dbo.Properties (PropertyId)
);
GO
