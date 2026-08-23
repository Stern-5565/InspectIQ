-- Inspection instance tables (the actual record of what happened, mostly frozen once
-- created): Inspections, InspectionResponses, MeterReadings, CleaningAreas,
-- CleaningInspections, VacantUnitInspections.
-- See docs/DATABASE.md §4-5 for design rationale.
--
-- NOTE - deferred FK: MeterReadings.PhotoMediaFileId will reference MediaFiles(MediaFileId),
-- but MediaFiles isn't created until 07_MediaAndNotesTables.sql. That FK is added there via
-- ALTER TABLE once both tables exist, rather than reordering the file sequence away from the
-- agreed database/ layout. Flagging this now rather than silently leaving the column
-- unconstrained until 07 runs.

USE InspectIQDb;
GO

CREATE TABLE dbo.Inspections (
    InspectionId          INT IDENTITY(1,1) NOT NULL,
    PropertyId             INT               NOT NULL,
    InspectorUserId        INT               NOT NULL,
    InspectionTemplateId   INT               NOT NULL,
    TemplateVersionUsed    INT               NOT NULL,
    InspectionType          NVARCHAR(50)      NULL,
    InspectionDate           DATE              NOT NULL,
    StartedAt                 DATETIME2         NULL,
    CompletedAt                DATETIME2         NULL,
    NextInspectionDueDate       DATE              NULL,
    Status                       NVARCHAR(30)      NOT NULL CONSTRAINT DF_Inspections_Status DEFAULT ('Scheduled'),  -- CHECK in 09
    GeneralNotes                  NVARCHAR(MAX)     NULL,
    OverallCondition                NVARCHAR(30)      NULL,  -- CHECK in 09
    OverallRiskRating                 NVARCHAR(30)      NULL,
    InspectorSignaturePath              NVARCHAR(500)     NULL,
    SubmittedAt                           DATETIME2         NULL,
    CreatedAt                               DATETIME2         NOT NULL CONSTRAINT DF_Inspections_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Inspections PRIMARY KEY CLUSTERED (InspectionId),
    CONSTRAINT FK_Inspections_Properties FOREIGN KEY (PropertyId) REFERENCES dbo.Properties (PropertyId),
    CONSTRAINT FK_Inspections_Inspector FOREIGN KEY (InspectorUserId) REFERENCES dbo.Users (UserId),
    CONSTRAINT FK_Inspections_Templates FOREIGN KEY (InspectionTemplateId) REFERENCES dbo.InspectionTemplates (InspectionTemplateId)
);
GO

CREATE TABLE dbo.InspectionResponses (
    InspectionResponseId  INT IDENTITY(1,1) NOT NULL,
    InspectionId           INT               NOT NULL,
    InspectionQuestionId    INT               NOT NULL,
    QuestionTextSnapshot     NVARCHAR(500)     NOT NULL,
    SectionNameSnapshot        NVARCHAR(200)     NOT NULL,
    AnswerTypeSnapshot           NVARCHAR(30)      NOT NULL,
    AnswerText                     NVARCHAR(MAX)     NULL,
    AnswerNumber                     DECIMAL(18,4)     NULL,
    AnswerDate                         DATE              NULL,
    IsNotApplicable                      BIT               NOT NULL CONSTRAINT DF_InspectionResponses_IsNA DEFAULT (0),
    Notes                                  NVARCHAR(MAX)     NULL,
    CreatedAt                                DATETIME2         NOT NULL CONSTRAINT DF_InspectionResponses_CreatedAt DEFAULT (SYSUTCDATETIME()),
    UpdatedAt                                  DATETIME2         NULL,
    CONSTRAINT PK_InspectionResponses PRIMARY KEY CLUSTERED (InspectionResponseId),
    CONSTRAINT FK_InspectionResponses_Inspections FOREIGN KEY (InspectionId) REFERENCES dbo.Inspections (InspectionId),
    CONSTRAINT FK_InspectionResponses_Questions FOREIGN KEY (InspectionQuestionId) REFERENCES dbo.InspectionQuestions (InspectionQuestionId)
);
GO

CREATE TABLE dbo.MeterReadings (
    MeterReadingId        INT IDENTITY(1,1) NOT NULL,
    InspectionResponseId   INT               NULL,
    PropertyId              INT               NOT NULL,
    MeterType                NVARCHAR(20)      NOT NULL,  -- CHECK in 09
    MeterSerialNumber          NVARCHAR(100)     NULL,
    PhotoMediaFileId              INT               NULL,  -- FK to MediaFiles added in 07, see header note
    AIDetectedReading                DECIMAL(18,4)     NULL,
    AIConfidence                       DECIMAL(5,4)      NULL,
    ConfirmedReading                     DECIMAL(18,4)     NULL,
    ReadingDateTime                        DATETIME2         NOT NULL CONSTRAINT DF_MeterReadings_ReadingDateTime DEFAULT (SYSUTCDATETIME()),
    InspectorNotes                           NVARCHAR(MAX)     NULL,
    CONSTRAINT PK_MeterReadings PRIMARY KEY CLUSTERED (MeterReadingId),
    CONSTRAINT FK_MeterReadings_Responses FOREIGN KEY (InspectionResponseId) REFERENCES dbo.InspectionResponses (InspectionResponseId),
    CONSTRAINT FK_MeterReadings_Properties FOREIGN KEY (PropertyId) REFERENCES dbo.Properties (PropertyId)
);
GO

-- Per-property configurable list, not a fixed global enum - a block with a lift needs
-- different areas than an HMO without one. See docs/DATABASE.md §10.5 for the onboarding
-- gap this introduces (new properties start with zero configured areas).
CREATE TABLE dbo.CleaningAreas (
    CleaningAreaId  INT IDENTITY(1,1) NOT NULL,
    PropertyId       INT               NOT NULL,
    AreaName          NVARCHAR(100)     NOT NULL,
    AreaType            NVARCHAR(30)      NOT NULL,  -- CHECK in 09
    IsActive              BIT               NOT NULL CONSTRAINT DF_CleaningAreas_IsActive DEFAULT (1),
    CONSTRAINT PK_CleaningAreas PRIMARY KEY CLUSTERED (CleaningAreaId),
    CONSTRAINT FK_CleaningAreas_Properties FOREIGN KEY (PropertyId) REFERENCES dbo.Properties (PropertyId)
);
GO

CREATE TABLE dbo.CleaningInspections (
    CleaningInspectionId  INT IDENTITY(1,1) NOT NULL,
    InspectionId            INT               NOT NULL,
    CleaningAreaId           INT               NOT NULL,
    Grade                     NVARCHAR(1)       NOT NULL,  -- CHECK in 09 (A-E)
    Notes                       NVARCHAR(MAX)     NULL,
    CleaningRequired               BIT               NOT NULL CONSTRAINT DF_CleaningInspections_CleaningRequired DEFAULT (0),
    Urgent                           BIT               NOT NULL CONSTRAINT DF_CleaningInspections_Urgent DEFAULT (0),
    AssignedUserId                     INT               NULL,
    DueDate                              DATE              NULL,
    Status                                 NVARCHAR(20)      NOT NULL CONSTRAINT DF_CleaningInspections_Status DEFAULT ('Pending'),  -- CHECK in 09
    CONSTRAINT PK_CleaningInspections PRIMARY KEY CLUSTERED (CleaningInspectionId),
    CONSTRAINT FK_CleaningInspections_Inspections FOREIGN KEY (InspectionId) REFERENCES dbo.Inspections (InspectionId),
    CONSTRAINT FK_CleaningInspections_Areas FOREIGN KEY (CleaningAreaId) REFERENCES dbo.CleaningAreas (CleaningAreaId),
    CONSTRAINT FK_CleaningInspections_AssignedUser FOREIGN KEY (AssignedUserId) REFERENCES dbo.Users (UserId)
);
GO

-- Its own table, not a generic InspectionResponse - scope §13 requires storing history
-- without overwriting the unit's current status.
CREATE TABLE dbo.VacantUnitInspections (
    VacantUnitInspectionId  INT IDENTITY(1,1) NOT NULL,
    InspectionId              INT               NOT NULL,
    UnitId                     INT               NOT NULL,
    DateIdentifiedVacant         DATE              NOT NULL,
    Condition                      NVARCHAR(30)      NULL,
    ElectricityOn                    BIT               NULL,
    WaterOn                            BIT               NULL,
    HeatingWorking                       BIT               NULL,
    WindowsSecure                          BIT               NULL,
    DoorsSecure                              BIT               NULL,
    SignsOfLeaks                               BIT               NULL,
    SignsOfDamp                                  BIT               NULL,
    SignsOfPests                                   BIT               NULL,
    CleaningRequired                                 BIT               NULL,
    WasteItemsLeftBehind                               BIT               NULL,
    MaintenanceRequired                                  BIT               NULL,
    Notes                                                  NVARCHAR(MAX)     NULL,
    CreatedAt                                                DATETIME2         NOT NULL CONSTRAINT DF_VacantUnitInspections_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_VacantUnitInspections PRIMARY KEY CLUSTERED (VacantUnitInspectionId),
    CONSTRAINT FK_VacantUnitInspections_Inspections FOREIGN KEY (InspectionId) REFERENCES dbo.Inspections (InspectionId),
    CONSTRAINT FK_VacantUnitInspections_Units FOREIGN KEY (UnitId) REFERENCES dbo.Units (UnitId)
);
GO
