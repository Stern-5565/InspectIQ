-- Seeds the 5 fixed roles (scope §3). Idempotent - safe to re-run.
USE InspectIQDb;
GO

INSERT INTO dbo.Roles (RoleName, Description)
SELECT v.RoleName, v.Description
FROM (VALUES
    ('Administrator', 'Full access to all companies, properties, users, and settings.'),
    ('Manager',       'Manage properties, view all inspections, assign inspections, manage maintenance, view reports.'),
    ('Inspector',     'View assigned properties, conduct inspections, upload evidence, raise maintenance issues, complete risk assessments.'),
    ('Maintenance',   'View assigned maintenance problems, update status, upload completion photos, add notes.'),
    ('Viewer',        'Read-only access to properties, inspections, and reports.')
) AS v (RoleName, Description)
WHERE NOT EXISTS (SELECT 1 FROM dbo.Roles r WHERE r.RoleName = v.RoleName);
GO
