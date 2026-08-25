/**
 * The wizard's top-level screen (Prompt 17: "Top: property name, address, inspection date,
 * completion percentage. Then inspection sections each with a completion percentage.") - a
 * tappable index into the per-question screen (InspectionQuestionPage), not the questions
 * themselves.
 */
import { Link, useOutletContext, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { isAnswered } from "../../utilities/inspectionAnswers";

export function InspectionSectionsPage() {
  const { id } = useParams();
  const { inspection, property, canEdit } = useOutletContext();

  const totalResponses = inspection.Sections.reduce((sum, s) => sum + s.Responses.length, 0);
  const totalAnswered = inspection.Sections.reduce(
    (sum, s) => sum + s.Responses.filter(isAnswered).length,
    0,
  );

  return (
    <div>
      <PageHeader
        title={property.PropertyName}
        description={[property.AddressLine1, property.City].filter(Boolean).join(", ")}
      />

      <div className="detail-card">
        <StatusBadge status={inspection.Status} />
        <div className="inspection-progress">
          <div className="inspection-progress__bar">
            <div className="inspection-progress__fill" style={{ width: `${inspection.CompletionPercentage}%` }} />
          </div>
          <span className="inspection-progress__label">
            {inspection.CompletionPercentage}% complete ({totalAnswered}/{totalResponses} questions)
          </span>
        </div>
        <div className="detail-grid">
          <div className="detail-grid__item">
            <span className="detail-grid__label">Inspection date</span>
            <span>{inspection.InspectionDate}</span>
          </div>
          <div className="detail-grid__item">
            <span className="detail-grid__label">Type</span>
            <span>{inspection.InspectionType ?? "—"}</span>
          </div>
        </div>
        {!canEdit && (
          <p className="empty-state">
            You can view this inspection, but only its assigned inspector (or an Administrator/Manager) can
            answer its questions.
          </p>
        )}
      </div>

      <ul className="section-list">
        {inspection.Sections.map((section, sectionIndex) => {
          const answered = section.Responses.filter(isAnswered).length;
          const total = section.Responses.length;
          const complete = total > 0 && answered === total;
          return (
            <li key={section.SectionName}>
              <Link to={`/inspections/${id}/sections/${sectionIndex}/questions/0`} className="section-list__item">
                <span className="section-list__name">{section.SectionName}</span>
                <span className={`section-list__progress${complete ? " section-list__progress--complete" : ""}`}>
                  {answered}/{total}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>

      {inspection.Status === "InProgress" && canEdit && (
        <p>
          <Link to={`/inspections/${id}/sections/0/questions/0`} className="button">
            {totalAnswered === 0 ? "Start answering" : "Continue answering"}
          </Link>
        </p>
      )}

      <p>
        <Link to="/inspections">← Back to inspections</Link>
      </p>
    </div>
  );
}
