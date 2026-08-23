-- Shared infrastructure: MediaFiles, Notes.
-- See docs/DATABASE.md §7 for design rationale.
--
-- Both use a polymorphic (EntityType, EntityId) pattern rather than one nullable FK column
-- per possible parent table (Property, Unit, Inspection, InspectionResponse, MeterReading,
-- MaintenanceIssue, RiskAssessment, CleaningInspection - 8+ nullable FKs otherwise). Accepted
-- tradeoff: no DB-enforced FK on EntityId, validated at the service layer instead. See
-- docs/DATABASE.md §9 (design decisions) - this is deliberate, not an oversight.

USE InspectIQDb;
GO

CREATE TABLE dbo.MediaFiles (
    MediaFileId       INT IDENTITY(1,1) NOT NULL,
    CompanyId           INT               NOT NULL,
    FileName              NVARCHAR(260)     NOT NULL,
    OriginalFileName        NVARCHAR(260)     NOT NULL,
    ContentType               NVARCHAR(100)     NOT NULL,
    FileSizeBytes               BIGINT            NOT NULL,
    StorageKey                    NVARCHAR(500)     NOT NULL,
    EntityType                      NVARCHAR(50)      NOT NULL,
    EntityId                          INT               NOT NULL,
    Caption                             NVARCHAR(500)     NULL,
    UploadedByUserId                     INT               NOT NULL,
    UploadedAt                             DATETIME2         NOT NULL CONSTRAINT DF_MediaFiles_UploadedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_MediaFiles PRIMARY KEY CLUSTERED (MediaFileId),
    CONSTRAINT FK_MediaFiles_Companies FOREIGN KEY (CompanyId) REFERENCES dbo.Companies (CompanyId),
    CONSTRAINT FK_MediaFiles_UploadedByUser FOREIGN KEY (UploadedByUserId) REFERENCES dbo.Users (UserId)
);
GO

CREATE TABLE dbo.Notes (
    NoteId          INT IDENTITY(1,1) NOT NULL,
    CompanyId         INT               NOT NULL,
    EntityType          NVARCHAR(50)      NOT NULL,
    EntityId               INT               NOT NULL,
    UserId                    INT               NOT NULL,
    NoteText                    NVARCHAR(MAX)     NOT NULL,
    CreatedAt                      DATETIME2         NOT NULL CONSTRAINT DF_Notes_CreatedAt DEFAULT (SYSUTCDATETIME()),
    EditedAt                          DATETIME2         NULL,
    CONSTRAINT PK_Notes PRIMARY KEY CLUSTERED (NoteId),
    CONSTRAINT FK_Notes_Companies FOREIGN KEY (CompanyId) REFERENCES dbo.Companies (CompanyId),
    CONSTRAINT FK_Notes_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
);
GO

-- Deferred FK from 04_InspectionTables.sql: MeterReadings.PhotoMediaFileId -> MediaFiles now
-- that MediaFiles exists. Added here rather than in 09_Constraints.sql since it's a plain FK,
-- not a CHECK/value-domain rule - keeping it next to the table it completes.
ALTER TABLE dbo.MeterReadings
    ADD CONSTRAINT FK_MeterReadings_MediaFiles FOREIGN KEY (PhotoMediaFileId) REFERENCES dbo.MediaFiles (MediaFileId);
GO
