/**
 * GET /api/inspection-templates/{id} - the full nested Sections -> Questions tree in one
 * request (the backend's own docstring: "a mobile client needs the whole checklist structure
 * at once, not N+1 calls per section"). Sections render as native <details>/<summary> elements
 * rather than custom collapse state - the default template alone has 21 sections/102
 * questions, so something has to collapse, and <details> gets that for free, accessibly, with
 * no extra JS.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { StatusBadge } from "../../components/StatusBadge";
import { getTemplate } from "../../services/inspectionTemplateService";
import { getErrorMessage } from "../../utilities/apiError";

const QUESTION_FLAGS = [
  ["IsMandatory", "Mandatory"],
  ["AllowNotes", "Notes"],
  ["AllowPhoto", "Photo"],
  ["RequirePhoto", "Photo required"],
  ["AllowMaintenanceFlag", "Can raise maintenance"],
  ["AllowRiskFlag", "Can raise risk"],
];

function QuestionRow({ question }) {
  return (
    <li className={`template-question${question.IsActive ? "" : " template-question--inactive"}`}>
      <div className="template-question__text">
        {question.QuestionText}
        <span className="template-question__answer-type">{question.AnswerType}</span>
      </div>
      <div className="template-question__flags">
        {QUESTION_FLAGS.filter(([key]) => question[key]).map(([key, label]) => (
          <span key={key} className="template-question__flag">
            {label}
          </span>
        ))}
        {!question.IsActive && <StatusBadge status="Inactive" />}
      </div>
    </li>
  );
}

export function InspectionTemplateDetailPage() {
  const { id } = useParams();
  const [template, setTemplate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadTemplate = useCallback(() => {
    setLoading(true);
    setError(null);
    getTemplate(id)
      .then(setTemplate)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadTemplate();
  }, [loadTemplate]);

  if (loading) {
    return <LoadingSpinner label="Loading template…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadTemplate} />;
  }

  const totalQuestions = template.Sections.reduce((sum, section) => sum + section.Questions.length, 0);

  return (
    <div>
      <PageHeader title={template.TemplateName} description={template.Description} />

      <div className="detail-card">
        <StatusBadge status={template.IsActive ? "Active" : "Inactive"} />
        <StatusBadge status={template.CompanyId === null ? "Global default" : "Company-specific"} tone="neutral" />
        <div className="detail-grid">
          <div className="detail-grid__item">
            <span className="detail-grid__label">Version</span>
            <span>{template.Version}</span>
          </div>
          <div className="detail-grid__item">
            <span className="detail-grid__label">Sections</span>
            <span>{template.Sections.length}</span>
          </div>
          <div className="detail-grid__item">
            <span className="detail-grid__label">Questions</span>
            <span>{totalQuestions}</span>
          </div>
        </div>
      </div>

      {template.Sections.map((section) => (
        <details key={section.InspectionSectionId} className="template-section">
          <summary>
            {section.SectionName}
            <span className="template-section__count">{section.Questions.length} questions</span>
            {!section.IsActive && <StatusBadge status="Inactive" />}
          </summary>
          <ul className="template-question-list">
            {section.Questions.map((question) => (
              <QuestionRow key={question.InspectionQuestionId} question={question} />
            ))}
          </ul>
        </details>
      ))}

      <p>
        <Link to="/inspection-templates">← Back to templates</Link>
      </p>
    </div>
  );
}
