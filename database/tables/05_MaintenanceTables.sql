-- Maintenance module: MaintenanceIssues, MaintenanceUpdates.
-- See docs/DATABASE.md §6 for design rationale.

USE InspectIQDb;
GO

-- CompanyId is denormalized here (also derivable via PropertyId -> Properties.CompanyId).
-- Deliberate - see docs/DATABASE.md §9.5 and §10.1: makes company-isolation queries direct
-- (WHERE CompanyId = @CompanyId) instead of a multi-hop join, at the cost of a service-layer
-- invariant (CompanyId must always be derived server-side from PropertyId, never client input)
-- that Phase 19's security review must explicitly verify.
CREATE TABLE dbo.MaintenanceIssues (
    MaintenanceIssueId   INT IDENTITY(1,1) NOT NULL,
    CompanyId              INT               NOT NULL,
    PropertyId              INT               NOT NULL,
    UnitId                   INT               NULL,
    InspectionId              INT               NULL,
    InspectionResponseId       INT               NULL,
    Title                        NVARCHAR(200)     NOT NULL,
    Description                    NVARCHAR(MAX)     NULL,
    Location                         NVARCHAR(200)     NULL,
    Category                           NVARCHAR(30)      NOT NULL,  -- CHECK in 09
    Priority                             NVARCHAR(20)      NOT NULL,  -- CHECK in 09
    Status                                  NVARCHAR(20)      NOT NULL CONSTRAINT DF_MaintenanceIssues_Status DEFAULT ('Open'),  -- CHECK in 09
    AssignedUserId                            INT               NULL,
    ReportedByUserId                            INT               NOT NULL,
    ReportedDate                                  DATE              NOT NULL CONSTRAINT DF_MaintenanceIssues_ReportedDate DEFAULT (CAST(SYSUTCDATETIME() AS DATE)),
    DueDate                                         DATE              NULL,
    CompletedDate                                     DATE              NULL,
    Notes                                               NVARCHAR(MAX)     NULL,
    CONSTRAINT PK_MaintenanceIssues PRIMARY KEY CLUSTERED (MaintenanceIssueId),
    CONSTRAINT FK_MaintenanceIssues_Companies FOREIGN KEY (CompanyId) REFERENCES dbo.Companies (CompanyId),
    CONSTRAINT FK_MaintenanceIssues_Properties FOREIGN KEY (PropertyId) REFERENCES dbo.Properties (PropertyId),
    CONSTRAINT FK_MaintenanceIssues_Units FOREIGN KEY (UnitId) REFERENCES dbo.Units (UnitId),
    CONSTRAINT FK_MaintenanceIssues_Inspections FOREIGN KEY (InspectionId) REFERENCES dbo.Inspections (InspectionId),
    CONSTRAINT FK_MaintenanceIssues_Responses FOREIGN KEY (InspectionResponseId) REFERENCES dbo.InspectionResponses (InspectionResponseId),
    CONSTRAINT FK_MaintenanceIssues_AssignedUser FOREIGN KEY (AssignedUserId) REFERENCES dbo.Users (UserId),
    CONSTRAINT FK_MaintenanceIssues_ReportedByUser FOREIGN KEY (ReportedByUserId) REFERENCES dbo.Users (UserId)
);
GO

-- Every status change recorded here - the timeline scope §18 asks for. Written by the service
-- layer on every transition, never reconstructed from other tables after the fact.
CREATE TABLE dbo.MaintenanceUpdates (
    MaintenanceUpdateId  INT IDENTITY(1,1) NOT NULL,
    MaintenanceIssueId     INT               NOT NULL,
    UpdateType               NVARCHAR(30)      NOT NULL,  -- CHECK in 09 (StatusChange/Comment/PhotoUploaded)
    OldStatus                  NVARCHAR(20)      NULL,
    NewStatus                    NVARCHAR(20)      NULL,
    Comment                         NVARCHAR(MAX)     NULL,
    UserId                            INT               NOT NULL,
    CreatedAt                           DATETIME2         NOT NULL CONSTRAINT DF_MaintenanceUpdates_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_MaintenanceUpdates PRIMARY KEY CLUSTERED (MaintenanceUpdateId),
    CONSTRAINT FK_MaintenanceUpdates_Issues FOREIGN KEY (MaintenanceIssueId) REFERENCES dbo.MaintenanceIssues (MaintenanceIssueId),
    CONSTRAINT FK_MaintenanceUpdates_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
);
GO
