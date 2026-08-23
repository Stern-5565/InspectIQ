-- Checklist engine, template side (mutable, edited by admins):
-- InspectionTemplates, InspectionSections, InspectionQuestions.
-- See docs/DATABASE.md §3 for design rationale.
--
-- IMPORTANT: per the Phase 1 sign-off (docs/PROJECT_PLAN.md §13.1), InspectionQuestions,
-- InspectionSections, and InspectionTemplates are SOFT-DELETE ONLY. No repository method may
-- ever issue a DELETE against these three tables - only UPDATE ... SET IsActive = 0. A hard
-- delete would silently break the FK that InspectionResponses keeps for analytics joins.
-- This is enforced at the application repository layer (SQL alone can't forbid DELETE per-row
-- without a trigger); flagging it here in the same file as the tables it protects.

USE InspectIQDb;
GO

-- CompanyId NULLABLE: NULL = a global default template usable by every company; non-null = a
-- company's own customized template. Same nullable-CompanyId pattern used by RiskMatrixLevels.
CREATE TABLE dbo.InspectionTemplates (
    InspectionTemplateId  INT IDENTITY(1,1)  NOT NULL,
    CompanyId               INT                NULL,
    TemplateName             NVARCHAR(200)      NOT NULL,
    Description               NVARCHAR(MAX)      NULL,
    IsActive                  BIT                NOT NULL CONSTRAINT DF_InspectionTemplates_IsActive DEFAULT (1),
    Version                   INT                NOT NULL CONSTRAINT DF_InspectionTemplates_Version DEFAULT (1),
    CreatedAt                 DATETIME2          NOT NULL CONSTRAINT DF_InspectionTemplates_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CreatedBy                 INT                NULL,
    CONSTRAINT PK_InspectionTemplates PRIMARY KEY CLUSTERED (InspectionTemplateId),
    CONSTRAINT FK_InspectionTemplates_Companies FOREIGN KEY (CompanyId) REFERENCES dbo.Companies (CompanyId),
    CONSTRAINT FK_InspectionTemplates_CreatedBy FOREIGN KEY (CreatedBy) REFERENCES dbo.Users (UserId)
);
GO

CREATE TABLE dbo.InspectionSections (
    InspectionSectionId    INT IDENTITY(1,1)  NOT NULL,
    InspectionTemplateId    INT                NOT NULL,
    SectionName               NVARCHAR(200)      NOT NULL,
    SortOrder                 INT                NOT NULL CONSTRAINT DF_InspectionSections_SortOrder DEFAULT (0),
    IsActive                   BIT                NOT NULL CONSTRAINT DF_InspectionSections_IsActive DEFAULT (1),
    CONSTRAINT PK_InspectionSections PRIMARY KEY CLUSTERED (InspectionSectionId),
    CONSTRAINT FK_InspectionSections_Templates FOREIGN KEY (InspectionTemplateId) REFERENCES dbo.InspectionTemplates (InspectionTemplateId)
);
GO

CREATE TABLE dbo.InspectionQuestions (
    InspectionQuestionId     INT IDENTITY(1,1)  NOT NULL,
    InspectionSectionId       INT                NOT NULL,
    QuestionText                 NVARCHAR(500)      NOT NULL,
    AnswerType                    NVARCHAR(30)       NOT NULL,  -- CHECK added in 09_Constraints.sql
    SortOrder                     INT                NOT NULL CONSTRAINT DF_InspectionQuestions_SortOrder DEFAULT (0),
    AllowNotes                     BIT                NOT NULL CONSTRAINT DF_InspectionQuestions_AllowNotes DEFAULT (1),
    AllowPhoto                     BIT                NOT NULL CONSTRAINT DF_InspectionQuestions_AllowPhoto DEFAULT (1),
    RequirePhoto                   BIT                NOT NULL CONSTRAINT DF_InspectionQuestions_RequirePhoto DEFAULT (0),
    AllowMaintenanceFlag           BIT                NOT NULL CONSTRAINT DF_InspectionQuestions_AllowMaintenanceFlag DEFAULT (1),
    AllowRiskFlag                   BIT                NOT NULL CONSTRAINT DF_InspectionQuestions_AllowRiskFlag DEFAULT (1),
    IsMandatory                     BIT                NOT NULL CONSTRAINT DF_InspectionQuestions_IsMandatory DEFAULT (0),
    IsActive                         BIT                NOT NULL CONSTRAINT DF_InspectionQuestions_IsActive DEFAULT (1),
    CONSTRAINT PK_InspectionQuestions PRIMARY KEY CLUSTERED (InspectionQuestionId),
    CONSTRAINT FK_InspectionQuestions_Sections FOREIGN KEY (InspectionSectionId) REFERENCES dbo.InspectionSections (InspectionSectionId)
);
GO
