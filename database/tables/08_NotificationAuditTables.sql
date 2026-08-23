-- Shared infrastructure: Notifications, AuditLogs.
-- See docs/DATABASE.md §7 for design rationale.
--
-- Notifications exists now so the schema doesn't need to change when V2 wires up real
-- delivery (in-app/email/SMS) - no sending/scheduling logic built yet, deliberately (scope
-- defers this to "later").

USE InspectIQDb;
GO

CREATE TABLE dbo.Notifications (
    NotificationId  INT IDENTITY(1,1) NOT NULL,
    CompanyId         INT               NOT NULL,
    UserId              INT               NOT NULL,  -- recipient
    NotificationType      NVARCHAR(50)      NOT NULL,  -- CHECK in 09
    EntityType               NVARCHAR(50)      NULL,
    EntityId                    INT               NULL,
    Message                        NVARCHAR(MAX)     NOT NULL,
    IsRead                            BIT               NOT NULL CONSTRAINT DF_Notifications_IsRead DEFAULT (0),
    CreatedAt                           DATETIME2         NOT NULL CONSTRAINT DF_Notifications_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Notifications PRIMARY KEY CLUSTERED (NotificationId),
    CONSTRAINT FK_Notifications_Companies FOREIGN KEY (CompanyId) REFERENCES dbo.Companies (CompanyId),
    CONSTRAINT FK_Notifications_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
);
GO

CREATE TABLE dbo.AuditLogs (
    AuditLogId    INT IDENTITY(1,1) NOT NULL,
    CompanyId       INT               NOT NULL,
    UserId            INT               NULL,  -- NULL for system actions
    Action              NVARCHAR(100)     NOT NULL,
    EntityType            NVARCHAR(50)      NOT NULL,
    EntityId                INT               NULL,
    PreviousValue              NVARCHAR(MAX)     NULL,
    NewValue                      NVARCHAR(MAX)     NULL,
    Timestamp                        DATETIME2         NOT NULL CONSTRAINT DF_AuditLogs_Timestamp DEFAULT (SYSUTCDATETIME()),
    IPAddress                           NVARCHAR(45)      NULL,
    DeviceInfo                             NVARCHAR(500)     NULL,
    CONSTRAINT PK_AuditLogs PRIMARY KEY CLUSTERED (AuditLogId),
    CONSTRAINT FK_AuditLogs_Companies FOREIGN KEY (CompanyId) REFERENCES dbo.Companies (CompanyId),
    CONSTRAINT FK_AuditLogs_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
);
GO
