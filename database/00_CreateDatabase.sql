-- InspectIQ database creation.
-- Idempotent: safe to re-run against an instance that already has the database.

IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = N'InspectIQDb')
BEGIN
    CREATE DATABASE InspectIQDb;
END
GO
