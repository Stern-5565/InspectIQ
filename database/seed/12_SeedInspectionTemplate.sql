-- Default "Monthly Property Inspection" template (scope Prompt 4), 21 sections.
--
-- Design note on four "gateway" sections (Communal Cleaning, Units, Vacant Units,
-- Maintenance, Risk Assessment): these deliberately carry few or no detailed checklist
-- questions here, because their real substance lives in dedicated tables/flows, not generic
-- InspectionResponses - CleaningInspections/CleaningAreas for cleaning grading,
-- VacantUnitInspections for vacant units, MaintenanceIssues/RiskAssessments creatable from any
-- question throughout the inspection. Duplicating that detail as regular checklist questions
-- here would fight the schema's own design (docs/DATABASE.md §5-6), not complement it. Each
-- gateway section keeps one or two questions whose job is to prompt/confirm the inspector used
-- the dedicated flow, not to re-collect the same data twice.
--
-- Column defaults relied on throughout (see tables/03_InspectionTemplateTables.sql): AllowNotes
-- and AllowPhoto default to 1, AllowMaintenanceFlag and AllowRiskFlag default to 1 (any question
-- can raise an issue, per scope §17's "from any inspection question"), RequirePhoto and
-- IsMandatory default to 0. Only overridden below where a question needs something other than
-- the default.
--
-- Idempotent by TemplateName - if this template already exists (by name, global CompanyId
-- IS NULL), the script exits without creating a duplicate.

USE InspectIQDb;
GO

-- NOTE: no GO between this guard and the inserts below - RETURN only exits the current batch,
-- so the guard must be in the same batch as everything it's meant to skip, not a separate one.
IF EXISTS (SELECT 1 FROM dbo.InspectionTemplates WHERE TemplateName = 'Monthly Property Inspection' AND CompanyId IS NULL)
BEGIN
    PRINT 'Monthly Property Inspection template already exists - skipping.';
    RETURN;
END

DECLARE @TemplateId INT;
DECLARE @SectionId INT;

INSERT INTO dbo.InspectionTemplates (CompanyId, TemplateName, Description, IsActive, Version, CreatedBy)
VALUES (NULL, 'Monthly Property Inspection', 'Default global inspection template covering property access, safety systems, communal areas, and grounds. Usable by every company; companies may clone and customize their own copy later.', 1, 1, NULL);
SET @TemplateId = SCOPE_IDENTITY();

-------------------------------------------------------------------------------------------
-- 1. Property Access (scope §10)
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Property Access', 1);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Was access available?', 'YesNo', 1, 1, 0),
(@SectionId, 'How was access obtained?', 'Text', 2, 0, 0),
(@SectionId, 'Was a key used?', 'YesNo', 3, 0, 0),
(@SectionId, 'Key location confirmed correct?', 'YesNo', 4, 0, 0),
(@SectionId, 'Door condition', 'Condition', 5, 0, 1),
(@SectionId, 'Lock condition', 'Condition', 6, 0, 0),
(@SectionId, 'Intercom working?', 'YesNo', 7, 0, 0),
(@SectionId, 'Any access problems?', 'Text', 8, 0, 0);

-------------------------------------------------------------------------------------------
-- 2. General Property Condition
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'General Property Condition', 2);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Overall external condition', 'Condition', 1, 1, 1),
(@SectionId, 'Signs of structural damage?', 'YesNo', 2, 0, 0),
(@SectionId, 'Roof visibly in good condition?', 'YesNo', 3, 0, 0),
(@SectionId, 'Guttering and downpipes condition', 'Condition', 4, 0, 0),
(@SectionId, 'External walls condition', 'Condition', 5, 0, 0),
(@SectionId, 'Any general observations?', 'Text', 6, 0, 0);

-------------------------------------------------------------------------------------------
-- 3. Electricity Meter (scope §11)
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Electricity Meter', 3);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Electricity meter reading', 'MeterReading', 1, 1, 1),
(@SectionId, 'Meter serial number visible and recorded?', 'YesNo', 2, 0, 0),
(@SectionId, 'Meter condition / damage', 'Condition', 3, 0, 0);

-------------------------------------------------------------------------------------------
-- 4. Fire Alarm (scope §12)
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Fire Alarm', 4);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Alarm installed?', 'YesNo', 1, 1, 0),
(@SectionId, 'Alarm panel showing normal?', 'YesNo', 2, 0, 1),
(@SectionId, 'Fault showing?', 'YesNo', 3, 0, 0),
(@SectionId, 'Any visible damage?', 'YesNo', 4, 0, 0),
(@SectionId, 'Test completed?', 'YesNo', 5, 0, 0),
(@SectionId, 'Test result', 'PassFail', 6, 0, 0);

-------------------------------------------------------------------------------------------
-- 5. Smoke / Heat Detectors (scope §12)
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Smoke / Heat Detectors', 5);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Detectors present?', 'YesNo', 1, 1, 0),
(@SectionId, 'Detectors damaged?', 'YesNo', 2, 0, 0),
(@SectionId, 'Test completed?', 'YesNo', 3, 0, 0),
(@SectionId, 'Test result', 'PassFail', 4, 0, 0);

-------------------------------------------------------------------------------------------
-- 6. Emergency Lighting (scope §9 - exact worked example)
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Emergency Lighting', 6);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Is emergency lighting installed?', 'YesNo', 1, 1, 0),
(@SectionId, 'Does it appear operational?', 'PassFail', 2, 0, 0),
(@SectionId, 'Is there visible damage?', 'YesNo', 3, 0, 0),
(@SectionId, 'When was it last tested?', 'Date', 4, 0, 0),
(@SectionId, 'Is maintenance required?', 'YesNo', 5, 0, 0);

-------------------------------------------------------------------------------------------
-- 7. Fire Doors (scope §12)
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Fire Doors', 7);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Door closes correctly?', 'PassFail', 1, 1, 0),
(@SectionId, 'Door damaged?', 'YesNo', 2, 0, 1),
(@SectionId, 'Closers working?', 'YesNo', 3, 0, 0),
(@SectionId, 'Seals present?', 'YesNo', 4, 0, 0),
(@SectionId, 'Signage present?', 'YesNo', 5, 0, 0);

-------------------------------------------------------------------------------------------
-- 8. Front Garden (scope §13)
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Front Garden', 8);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Overall condition', 'Condition', 1, 0, 1),
(@SectionId, 'Rubbish present?', 'YesNo', 2, 0, 0),
(@SectionId, 'Overgrown vegetation?', 'YesNo', 3, 0, 0),
(@SectionId, 'Pathway safe?', 'YesNo', 4, 0, 0),
(@SectionId, 'Lighting working?', 'YesNo', 5, 0, 0),
(@SectionId, 'Fence condition', 'Condition', 6, 0, 0),
(@SectionId, 'Gate condition', 'Condition', 7, 0, 0),
(@SectionId, 'Trip hazards?', 'YesNo', 8, 0, 0),
(@SectionId, 'Pest evidence?', 'YesNo', 9, 0, 0);

-------------------------------------------------------------------------------------------
-- 9. Back Garden (scope §14)
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Back Garden', 9);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Overall condition', 'Condition', 1, 0, 1),
(@SectionId, 'Rubbish present?', 'YesNo', 2, 0, 0),
(@SectionId, 'Overgrown vegetation?', 'YesNo', 3, 0, 0),
(@SectionId, 'Pathways safe?', 'YesNo', 4, 0, 0),
(@SectionId, 'Lighting working?', 'YesNo', 5, 0, 0),
(@SectionId, 'Fencing condition', 'Condition', 6, 0, 0),
(@SectionId, 'Gates condition', 'Condition', 7, 0, 0),
(@SectionId, 'Drainage condition', 'Condition', 8, 0, 0),
(@SectionId, 'Trip hazards?', 'YesNo', 9, 0, 0),
(@SectionId, 'Pest evidence?', 'YesNo', 10, 0, 0);

-------------------------------------------------------------------------------------------
-- 10. Entrance
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Entrance', 10);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Entrance door condition', 'Condition', 1, 0, 0),
(@SectionId, 'Flooring condition / trip hazards', 'YesNo', 2, 0, 0),
(@SectionId, 'Lighting working?', 'YesNo', 3, 0, 0),
(@SectionId, 'Signage and notices up to date?', 'YesNo', 4, 0, 0),
(@SectionId, 'General condition', 'Condition', 5, 0, 1);

-------------------------------------------------------------------------------------------
-- 11. Hallways
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Hallways', 11);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Flooring condition', 'Condition', 1, 0, 0),
(@SectionId, 'Lighting working?', 'YesNo', 2, 0, 0),
(@SectionId, 'Walls and ceiling condition', 'Condition', 3, 0, 0),
(@SectionId, 'Trip hazards?', 'YesNo', 4, 0, 0),
(@SectionId, 'Fire escape route clear?', 'YesNo', 5, 1, 0);

-------------------------------------------------------------------------------------------
-- 12. Staircases
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Staircases', 12);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Handrail secure?', 'YesNo', 1, 1, 0),
(@SectionId, 'Steps in good condition?', 'YesNo', 2, 0, 0),
(@SectionId, 'Lighting working?', 'YesNo', 3, 0, 0),
(@SectionId, 'Non-slip treads present and intact?', 'YesNo', 4, 0, 0);

-------------------------------------------------------------------------------------------
-- 13. Communal Kitchen (scope §15)
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Communal Kitchen', 13);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Overall cleanliness', 'Condition', 1, 0, 1),
(@SectionId, 'Floor condition', 'Condition', 2, 0, 0),
(@SectionId, 'Worktops clean?', 'YesNo', 3, 0, 0),
(@SectionId, 'Sink clean?', 'YesNo', 4, 0, 0),
(@SectionId, 'Cooker clean and safe?', 'YesNo', 5, 0, 0),
(@SectionId, 'Fridge condition', 'Condition', 6, 0, 0),
(@SectionId, 'Food waste present?', 'YesNo', 7, 0, 0),
(@SectionId, 'Bins emptied?', 'YesNo', 8, 0, 0),
(@SectionId, 'Lighting working?', 'YesNo', 9, 0, 0),
(@SectionId, 'Electrical sockets visually safe?', 'YesNo', 10, 1, 0),
(@SectionId, 'Fire safety equipment present?', 'YesNo', 11, 0, 0),
(@SectionId, 'Pest evidence?', 'YesNo', 12, 0, 0),
(@SectionId, 'Leaks?', 'YesNo', 13, 0, 0),
(@SectionId, 'Damage?', 'YesNo', 14, 0, 0);

-------------------------------------------------------------------------------------------
-- 14. Communal Bathrooms
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Communal Bathrooms', 14);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Overall cleanliness', 'Condition', 1, 0, 1),
(@SectionId, 'Sanitary fittings condition', 'Condition', 2, 0, 0),
(@SectionId, 'Leaks?', 'YesNo', 3, 0, 0),
(@SectionId, 'Extractor fan working?', 'YesNo', 4, 0, 0),
(@SectionId, 'Damage?', 'YesNo', 5, 0, 0);

-------------------------------------------------------------------------------------------
-- 15. Bin Area
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Bin Area', 15);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Bins present and in good condition?', 'YesNo', 1, 0, 0),
(@SectionId, 'Area clean and tidy?', 'YesNo', 2, 0, 1),
(@SectionId, 'Overflowing waste?', 'YesNo', 3, 0, 0),
(@SectionId, 'Pest evidence?', 'YesNo', 4, 0, 0);

-------------------------------------------------------------------------------------------
-- 16. Communal Cleaning - gateway section, see file header. Real grading happens via
-- CleaningAreas/CleaningInspections, configured per property.
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Communal Cleaning', 16);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Communal cleaning assessment completed for all applicable areas at this property?', 'YesNo', 1, 1, 0);

-------------------------------------------------------------------------------------------
-- 17. Units - gateway section, see file header.
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Units', 17);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Unit occupancy statuses confirmed or updated for this property?', 'YesNo', 1, 1, 0),
(@SectionId, 'Do any occupied units require attention?', 'YesNo', 2, 0, 0);

-------------------------------------------------------------------------------------------
-- 18. Vacant Units - gateway section, see file header. Real detail captured via the
-- dedicated VacantUnitInspections flow ("Add Empty Unit").
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Vacant Units', 18);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Any vacant units identified during this inspection?', 'YesNo', 1, 1, 0),
(@SectionId, 'All identified vacant units inspected using Add Empty Unit?', 'YesNo', 2, 0, 0);

-------------------------------------------------------------------------------------------
-- 19. Maintenance - gateway/summary section, see file header. Individual issues are
-- created via "Create Maintenance Issue" from any question throughout the inspection.
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Maintenance', 19);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Any additional maintenance issues not already logged elsewhere in this inspection?', 'Text', 1, 0, 0);

-------------------------------------------------------------------------------------------
-- 20. Risk Assessment - gateway/summary section, see file header. Individual risks are
-- created via "Create Risk" from any question throughout the inspection.
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'Risk Assessment', 20);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'Any additional risks not already logged elsewhere in this inspection?', 'Text', 1, 0, 0);

-------------------------------------------------------------------------------------------
-- 21. General Notes
-------------------------------------------------------------------------------------------
INSERT INTO dbo.InspectionSections (InspectionTemplateId, SectionName, SortOrder) VALUES (@TemplateId, 'General Notes', 21);
SET @SectionId = SCOPE_IDENTITY();
INSERT INTO dbo.InspectionQuestions (InspectionSectionId, QuestionText, AnswerType, SortOrder, IsMandatory, RequirePhoto) VALUES
(@SectionId, 'General notes for this inspection', 'Text', 1, 0, 0),
(@SectionId, 'Overall inspector comments', 'Text', 2, 0, 0);

PRINT 'Monthly Property Inspection template seeded: 21 sections.';
GO
