-- Risk module: RiskAssessments, RiskMatrixLevels.
-- See docs/DATABASE.md §6 for design rationale.

USE InspectIQDb;
GO

-- Required for the PERSISTED computed column (RiskScore) below - SQL Server rejects CREATE
-- TABLE with a computed column unless both are explicitly ON at creation time.
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- CompanyId denormalized here for the same reason as MaintenanceIssues - see 05_MaintenanceTables.sql
-- header comment and docs/DATABASE.md §10.1.
CREATE TABLE dbo.RiskAssessments (
    RiskAssessmentId       INT IDENTITY(1,1) NOT NULL,
    CompanyId                INT               NOT NULL,
    PropertyId                 INT               NOT NULL,
    InspectionId                 INT               NULL,
    InspectionResponseId           INT               NULL,
    MaintenanceIssueId               INT               NULL,
    Location                           NVARCHAR(200)     NULL,
    Hazard                               NVARCHAR(MAX)     NOT NULL,
    WhoMayBeAffected                      NVARCHAR(MAX)     NULL,
    ExistingControls                        NVARCHAR(MAX)     NULL,
    Likelihood                                TINYINT           NOT NULL,  -- CHECK 1-5 in 09
    Severity                                    TINYINT           NOT NULL,  -- CHECK 1-5 in 09
    -- Computed, not insertable - a client-supplied score is structurally impossible, not just
    -- disallowed by app convention (scope §14: "do not trust a risk score supplied by the
    -- frontend"). See docs/DATABASE.md §9.6.
    RiskScore                                     AS (Likelihood * Severity) PERSISTED,
    -- Snapshotted at write time from RiskMatrixLevels, not derived live - thresholds can
    -- change later without reclassifying old assessments. Same principle as the §13.1
    -- InspectionResponse snapshot, applied consistently rather than as a one-off.
    RiskLevel                                       NVARCHAR(20)      NOT NULL,
    AdditionalActionRequired                          NVARCHAR(MAX)     NULL,
    ResponsiblePersonUserId                             INT               NULL,
    TargetCompletionDate                                  DATE              NULL,
    Status                                                   NVARCHAR(20)      NOT NULL CONSTRAINT DF_RiskAssessments_Status DEFAULT ('Open'),  -- CHECK in 09
    Notes                                                       NVARCHAR(MAX)     NULL,
    CreatedAt                                                     DATETIME2         NOT NULL CONSTRAINT DF_RiskAssessments_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_RiskAssessments PRIMARY KEY CLUSTERED (RiskAssessmentId),
    CONSTRAINT FK_RiskAssessments_Companies FOREIGN KEY (CompanyId) REFERENCES dbo.Companies (CompanyId),
    CONSTRAINT FK_RiskAssessments_Properties FOREIGN KEY (PropertyId) REFERENCES dbo.Properties (PropertyId),
    CONSTRAINT FK_RiskAssessments_Inspections FOREIGN KEY (InspectionId) REFERENCES dbo.Inspections (InspectionId),
    CONSTRAINT FK_RiskAssessments_Responses FOREIGN KEY (InspectionResponseId) REFERENCES dbo.InspectionResponses (InspectionResponseId),
    CONSTRAINT FK_RiskAssessments_MaintenanceIssues FOREIGN KEY (MaintenanceIssueId) REFERENCES dbo.MaintenanceIssues (MaintenanceIssueId),
    CONSTRAINT FK_RiskAssessments_ResponsibleUser FOREIGN KEY (ResponsiblePersonUserId) REFERENCES dbo.Users (UserId)
);
GO

-- Configurable risk-level bands (scope §19: "keep the risk-level thresholds configurable").
-- CompanyId NULLABLE: NULL = global default matrix, same pattern as InspectionTemplates.
CREATE TABLE dbo.RiskMatrixLevels (
    RiskMatrixLevelId  INT IDENTITY(1,1) NOT NULL,
    CompanyId            INT               NULL,
    MinScore               TINYINT           NOT NULL,
    MaxScore                 TINYINT           NOT NULL,
    LevelName                  NVARCHAR(20)      NOT NULL,
    SortOrder                    INT               NOT NULL CONSTRAINT DF_RiskMatrixLevels_SortOrder DEFAULT (0),
    ColorHint                      NVARCHAR(20)      NULL,
    CONSTRAINT PK_RiskMatrixLevels PRIMARY KEY CLUSTERED (RiskMatrixLevelId),
    CONSTRAINT FK_RiskMatrixLevels_Companies FOREIGN KEY (CompanyId) REFERENCES dbo.Companies (CompanyId),
    CONSTRAINT CK_RiskMatrixLevels_ScoreRange CHECK (MinScore <= MaxScore)
);
GO
