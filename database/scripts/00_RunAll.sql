-- Runs the full InspectIQ schema against a fresh SQL Server instance, in dependency order.
-- Idempotent throughout (every table CREATE checks first, every seed script checks for
-- existing data) - safe to re-run against a database that already has some or all of this.
--
-- Run from the database/ directory with sqlcmd, e.g.:
--   sqlcmd -S localhost\SQLEXPRESS -E -i scripts\00_RunAll.sql
--
-- Requires Windows Authentication (-E) or SQL auth (-U/-P) with permission to create a
-- database on the target server. For production, run against a pre-provisioned Azure SQL
-- database instead (00_CreateDatabase.sql's CREATE DATABASE step won't apply there - see
-- PropertyManager's deployment-guide.md for the equivalent az sql / sqlcmd pattern once
-- InspectIQ reaches its own Phase 20).
--
-- Deliberately does NOT run seed/13_SeedSampleData.sql's Part B (demo companies) by
-- default in a way that could be mistaken for safe-everywhere - Part B is clearly marked
-- LOCAL DEV ONLY in that file's own header. This script includes it because InspectIQDb, as
-- named here, is understood to be a local dev database; a production run should use
-- InspectIQDb's actual production name/target and skip 13 entirely (or split Part A into its
-- own always-run script if that becomes a real deployment need later).

:setvar SQLCMDMAXVARTYPEWIDTH 0

:r 00_CreateDatabase.sql

:r tables\01_CoreTables.sql
:r tables\02_PropertyTables.sql
:r tables\03_InspectionTemplateTables.sql
:r tables\04_InspectionTables.sql
:r tables\05_MaintenanceTables.sql
:r tables\06_RiskTables.sql
:r tables\07_MediaAndNotesTables.sql
:r tables\08_NotificationAuditTables.sql

:r constraints\09_Constraints.sql

:r indexes\10_Indexes.sql

:r seed\11_SeedRoles.sql
:r seed\12_SeedInspectionTemplate.sql
:r seed\13_SeedSampleData.sql

:r views\14_InspectionViews.sql

PRINT '=== InspectIQ schema setup complete. ===';
GO
