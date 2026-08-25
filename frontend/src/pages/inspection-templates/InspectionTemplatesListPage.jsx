/**
 * GET /api/inspection-templates - a plain list, not paginated (see
 * inspectionTemplateService.js). No search/filter beyond "include inactive" - the realistic
 * number of templates per company is small (one global default plus maybe a few
 * company-specific overrides), unlike Properties' potentially large portfolio.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { listTemplates } from "../../services/inspectionTemplateService";
import { getErrorMessage } from "../../utilities/apiError";

export function InspectionTemplatesListPage() {
  const [items, setItems] = useState([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadTemplates = useCallback(() => {
    setLoading(true);
    setError(null);
    listTemplates({ includeInactive })
      .then(setItems)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [includeInactive]);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  return (
    <div>
      <PageHeader
        title="Inspection Templates"
        description="Checklists available for starting an inspection. A company-specific template shown here overrides the global default with the same name."
      />

      <label className="checkbox-field">
        <input
          type="checkbox"
          checked={includeInactive}
          onChange={(event) => setIncludeInactive(event.target.checked)}
        />
        Include inactive templates
      </label>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadTemplates}
        emptyMessage="No inspection templates available yet."
        rows={items}
        getRowKey={(row) => row.InspectionTemplateId}
        columns={[
          {
            key: "TemplateName",
            header: "Name",
            render: (row) => (
              <Link to={`/inspection-templates/${row.InspectionTemplateId}`}>{row.TemplateName}</Link>
            ),
          },
          { key: "Description", header: "Description", render: (row) => row.Description ?? "—" },
          { key: "Version", header: "Version" },
          {
            key: "Scope",
            header: "Scope",
            render: (row) => (row.CompanyId === null ? "Global default" : "Company-specific"),
          },
          {
            key: "IsActive",
            header: "Status",
            render: (row) => <StatusBadge status={row.IsActive ? "Active" : "Inactive"} />,
          },
        ]}
      />
    </div>
  );
}
