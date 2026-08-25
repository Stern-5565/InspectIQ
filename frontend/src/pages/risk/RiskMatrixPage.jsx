/**
 * GET/POST/PATCH /api/risk-matrix-levels - all three already existed since Phase 13
 * (RiskAssessmentsListPage.jsx's own filter dropdown already reads getRiskMatrix live); this
 * page is genuinely just a frontend addition, no new backend needed - confirmed by reading
 * app/api/risk.py/risk_service.py/risk_repository.py first, the same "check before assuming a
 * gap exists" discipline every module this stretch has held itself to.
 *
 * View has no role restriction (any company member - app/api/risk.py's own module docstring);
 * mutation is Administrator/Manager (`CAN_MANAGE_RISK`, NOT the Admin-Settings-only tier - risk
 * matrix configuration was already Admin/Manager before Admin Settings introduced the narrower
 * Admin-only pattern, confirmed by rereading risk_service.py rather than assuming the newest
 * tier applies here too).
 *
 * The one real design problem this page has to solve that the backend doesn't: a company's own
 * bands fully REPLACE the global default the instant any exist
 * (risk_repository.get_risk_matrix_for_company's own docstring) - so adding a SINGLE custom band
 * would immediately drop every score outside it from having any resolvable level at all (a real
 * 422 the next risk assessment creation would hit, `risk_service._resolve_risk_level`). Rather
 * than let an Administrator discover that the hard way, "Customize for your company" clones the
 * current (global) 4 bands as company-specific rows in one batch - a safe, complete starting
 * point to edit from, never a partial one. A live gap/overlap check (`computeCoverageIssues`)
 * warns about any score 1-25 left uncovered after that, the same "make sure you won't regret
 * this" instinct this project's own Phase 1 sign-off decision was built on - not enforced by the
 * backend (no delete endpoint exists either, per the same "scope doesn't ask for full lifecycle
 * management" reasoning), so this is a frontend-only safety net, not a blocking validation.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_RISK } from "../../constants/roles";
import { createRiskMatrixLevel, getRiskMatrix, updateRiskMatrixLevel } from "../../services/riskService";
import { getErrorMessage } from "../../utilities/apiError";

const DEFAULT_COLOR = "#888888";

function computeCoverageIssues(levels) {
  if (levels.length === 0) {
    return ["No risk levels are configured at all - every risk assessment will fail to score."];
  }
  const sorted = [...levels].sort((a, b) => a.MinScore - b.MinScore);
  const issues = [];
  if (sorted[0].MinScore > 1) {
    issues.push(`Scores 1–${sorted[0].MinScore - 1} aren't covered by any level.`);
  }
  for (let i = 0; i < sorted.length - 1; i++) {
    const current = sorted[i];
    const next = sorted[i + 1];
    if (next.MinScore > current.MaxScore + 1) {
      issues.push(`Scores ${current.MaxScore + 1}–${next.MinScore - 1} aren't covered by any level.`);
    } else if (next.MinScore <= current.MaxScore) {
      issues.push(`"${current.LevelName}" and "${next.LevelName}" overlap (score ${next.MinScore}–${current.MaxScore}).`);
    }
  }
  const last = sorted[sorted.length - 1];
  if (last.MaxScore < 25) {
    issues.push(`Scores ${last.MaxScore + 1}–25 aren't covered by any level.`);
  }
  return issues;
}

function LevelRow({ level, canManage, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  function startEdit() {
    setForm({
      MinScore: String(level.MinScore),
      MaxScore: String(level.MaxScore),
      LevelName: level.LevelName,
      SortOrder: String(level.SortOrder),
      ColorHint: level.ColorHint ?? DEFAULT_COLOR,
    });
    setError(null);
    setEditing(true);
  }

  function handleSave() {
    const minScore = Number(form.MinScore);
    const maxScore = Number(form.MaxScore);
    if (minScore > maxScore) {
      setError("Min score cannot be greater than max score.");
      return;
    }
    setSaving(true);
    setError(null);
    updateRiskMatrixLevel(level.RiskMatrixLevelId, {
      MinScore: minScore,
      MaxScore: maxScore,
      LevelName: form.LevelName.trim(),
      SortOrder: Number(form.SortOrder),
      ColorHint: form.ColorHint,
    })
      .then((updated) => {
        onSaved(updated);
        setEditing(false);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  if (editing) {
    return (
      <tr>
        <td colSpan={5}>
          <div className="unit-edit-row">
            <FormField label="Min score" name="MinScore" type="number" value={form.MinScore} onChange={(e) => setForm((p) => ({ ...p, MinScore: e.target.value }))} required />
            <FormField label="Max score" name="MaxScore" type="number" value={form.MaxScore} onChange={(e) => setForm((p) => ({ ...p, MaxScore: e.target.value }))} required />
            <FormField label="Level name" name="LevelName" value={form.LevelName} onChange={(e) => setForm((p) => ({ ...p, LevelName: e.target.value }))} required />
            <FormField label="Sort order" name="SortOrder" type="number" value={form.SortOrder} onChange={(e) => setForm((p) => ({ ...p, SortOrder: e.target.value }))} />
            <FormField label="Color" name="ColorHint" type="color" value={form.ColorHint} onChange={(e) => setForm((p) => ({ ...p, ColorHint: e.target.value }))} />
            {error && <ErrorMessage message={error} />}
            <div className="unit-edit-row__actions">
              <button type="button" className="button" onClick={handleSave} disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </button>
              <button type="button" className="button button--secondary" onClick={() => setEditing(false)}>
                Cancel
              </button>
            </div>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td>
        {level.MinScore}–{level.MaxScore}
      </td>
      <td>
        <span className="risk-matrix__swatch" style={{ backgroundColor: level.ColorHint ?? DEFAULT_COLOR }} aria-hidden="true" />
        {level.LevelName}
      </td>
      <td>{level.SortOrder}</td>
      <td>{level.ColorHint ?? "—"}</td>
      <td>
        {canManage && (
          <button type="button" className="button button--secondary button--small" onClick={startEdit}>
            Edit
          </button>
        )}
        {error && <ErrorMessage message={error} />}
      </td>
    </tr>
  );
}

function AddLevelForm({ onCreated, onCancel }) {
  const [minScore, setMinScore] = useState("");
  const [maxScore, setMaxScore] = useState("");
  const [levelName, setLevelName] = useState("");
  const [sortOrder, setSortOrder] = useState("0");
  const [colorHint, setColorHint] = useState(DEFAULT_COLOR);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function handleSubmit(event) {
    event.preventDefault();
    if (!levelName.trim() || minScore === "" || maxScore === "") {
      setError("Min score, max score, and level name are required.");
      return;
    }
    if (Number(minScore) > Number(maxScore)) {
      setError("Min score cannot be greater than max score.");
      return;
    }
    setSubmitting(true);
    setError(null);
    createRiskMatrixLevel({
      minScore: Number(minScore),
      maxScore: Number(maxScore),
      levelName: levelName.trim(),
      sortOrder: Number(sortOrder) || 0,
      colorHint,
    })
      .then((level) => {
        onCreated(level);
        setMinScore("");
        setMaxScore("");
        setLevelName("");
        setSortOrder("0");
        setColorHint(DEFAULT_COLOR);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  return (
    <form className="unit-add-form" onSubmit={handleSubmit}>
      <FormField label="Min score" name="minScore" type="number" value={minScore} onChange={(e) => setMinScore(e.target.value)} required />
      <FormField label="Max score" name="maxScore" type="number" value={maxScore} onChange={(e) => setMaxScore(e.target.value)} required />
      <FormField label="Level name" name="levelName" value={levelName} onChange={(e) => setLevelName(e.target.value)} required />
      <FormField label="Sort order" name="sortOrder" type="number" value={sortOrder} onChange={(e) => setSortOrder(e.target.value)} />
      <FormField label="Color" name="colorHint" type="color" value={colorHint} onChange={(e) => setColorHint(e.target.value)} />
      {error && <ErrorMessage message={error} />}
      <div className="unit-edit-row__actions">
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Adding…" : "Add"}
        </button>
        <button type="button" className="button button--secondary" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export function RiskMatrixPage() {
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_RISK);

  const [levels, setLevels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [addingLevel, setAddingLevel] = useState(false);
  const [customizing, setCustomizing] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getRiskMatrix()
      .then(setLevels)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function replaceLevel(updated) {
    setLevels((prev) => prev.map((l) => (l.RiskMatrixLevelId === updated.RiskMatrixLevelId ? updated : l)));
  }

  function handleCreated(level) {
    setLevels((prev) => [...prev, level]);
    setAddingLevel(false);
    setToast(`"${level.LevelName}" added.`);
  }

  function handleCustomize() {
    setCustomizing(true);
    setError(null);
    const sorted = [...levels].sort((a, b) => a.SortOrder - b.SortOrder);
    Promise.all(
      sorted.map((level) =>
        createRiskMatrixLevel({
          minScore: level.MinScore,
          maxScore: level.MaxScore,
          levelName: level.LevelName,
          sortOrder: level.SortOrder,
          colorHint: level.ColorHint,
        })
      )
    )
      .then(() => {
        setToast("Your company now has its own editable risk matrix, starting from the global default.");
        load();
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setCustomizing(false));
  }

  const isGlobalDefault = levels.length > 0 && levels[0].CompanyId == null;
  const sortedForDisplay = [...levels].sort((a, b) => a.SortOrder - b.SortOrder);
  const coverageIssues = levels.length > 0 ? computeCoverageIssues(levels) : [];

  return (
    <div>
      <PageHeader
        title="Risk Matrix"
        description="The score bands used to grade every risk assessment across your company."
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      {loading && <LoadingSpinner label="Loading risk matrix…" />}
      {error && <ErrorMessage message={error} onRetry={load} />}

      {!loading && !error && (
        <div className="detail-card">
          {isGlobalDefault && (
            <div className="banner banner--info">
              <p>Your company is using the global default risk matrix. Editing a band here creates your own company-specific matrix.</p>
              {canManage && !customizing && (
                <button type="button" className="button button--secondary" onClick={handleCustomize}>
                  Customize for your company
                </button>
              )}
              {customizing && <LoadingSpinner label="Setting up your company's matrix…" />}
            </div>
          )}

          {coverageIssues.length > 0 && (
            <div className="banner banner--warning">
              <p>This matrix doesn't cover every possible score (1–25):</p>
              <ul>
                {coverageIssues.map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Score range</th>
                  <th scope="col">Level</th>
                  <th scope="col">Sort order</th>
                  <th scope="col">Color</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedForDisplay.map((level) => (
                  <LevelRow
                    key={level.RiskMatrixLevelId}
                    level={level}
                    canManage={canManage && !isGlobalDefault}
                    onSaved={replaceLevel}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {canManage && !isGlobalDefault && (
            <>
              {addingLevel ? (
                <AddLevelForm onCreated={handleCreated} onCancel={() => setAddingLevel(false)} />
              ) : (
                <button type="button" className="button button--secondary" onClick={() => setAddingLevel(true)}>
                  + Add band
                </button>
              )}
            </>
          )}
        </div>
      )}

      <p>
        <Link to="/risk-assessments">← Back to Risk Register</Link>
      </p>
    </div>
  );
}
