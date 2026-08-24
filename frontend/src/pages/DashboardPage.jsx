/**
 * Consumes GET /api/dashboard (app/schemas/dashboard.py's DashboardResponse) directly - the
 * first real page in this app beyond auth, and the natural end-to-end proof that scaffold +
 * auth actually works against the real backend (same "verify against a real running server,
 * not just that it compiles" discipline the backend held itself to every phase).
 */
import { useEffect, useState } from "react";
import { getDashboard } from "../services/dashboardService";
import { getErrorMessage } from "../utilities/apiError";
import { LoadingSpinner } from "../components/LoadingSpinner";

function StatCard({ label, value, tone = "default" }) {
  return (
    <div className={`stat-card stat-card--${tone}`}>
      <span className="stat-card__value">{value}</span>
      <span className="stat-card__label">{label}</span>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="dashboard-section">
      <h2>{title}</h2>
      <div className="stat-card-grid">{children}</div>
    </section>
  );
}

export function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getDashboard()
      .then((data) => {
        if (!cancelled) setDashboard(data);
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <LoadingSpinner fullPage label="Loading dashboard…" />;
  }

  if (error) {
    return (
      <p className="form-error" role="alert">
        {error}
      </p>
    );
  }

  const { Inspections, Maintenance, Risks, Cleaning, Properties, RecentActivity } = dashboard;

  return (
    <div className="dashboard-page">
      <h1>Dashboard</h1>

      <Section title="Inspections">
        <StatCard label="Due today" value={Inspections.DueToday} />
        <StatCard label="Due this week" value={Inspections.DueThisWeek} />
        <StatCard label="Overdue" value={Inspections.Overdue} tone={Inspections.Overdue > 0 ? "danger" : "default"} />
        <StatCard label="Completed this month" value={Inspections.CompletedThisMonth} />
      </Section>

      <Section title="Maintenance">
        <StatCard label="Open" value={Maintenance.OpenCount} />
        <StatCard label="High priority" value={Maintenance.HighPriority} />
        <StatCard
          label="Urgent / emergency"
          value={Maintenance.UrgentOrEmergency}
          tone={Maintenance.UrgentOrEmergency > 0 ? "danger" : "default"}
        />
        <StatCard label="Overdue" value={Maintenance.OverdueCount} />
      </Section>

      <Section title="Risks">
        <StatCard
          label="Critical"
          value={Risks.CriticalCount}
          tone={Risks.CriticalCount > 0 ? "danger" : "default"}
        />
        <StatCard label="High" value={Risks.HighCount} tone={Risks.HighCount > 0 ? "warning" : "default"} />
        <StatCard label="Outstanding" value={Risks.OutstandingCount} />
      </Section>

      <Section title="Cleaning (latest grade per area)">
        <StatCard label="Grade A/B" value={Cleaning.GradeAOrB} tone="success" />
        <StatCard label="Grade C" value={Cleaning.GradeC} tone="warning" />
        <StatCard label="Grade D/E" value={Cleaning.GradeDOrE} tone={Cleaning.GradeDOrE > 0 ? "danger" : "default"} />
      </Section>

      <Section title="Properties">
        <StatCard label="Total active" value={Properties.TotalActiveProperties} />
        <StatCard
          label="Requiring attention"
          value={Properties.PropertiesRequiringAttention}
          tone={Properties.PropertiesRequiringAttention > 0 ? "warning" : "default"}
        />
      </Section>

      <section className="dashboard-section">
        <h2>Recent activity</h2>

        <h3>Inspections</h3>
        {RecentActivity.Inspections.length === 0 ? (
          <p className="empty-state">No recent inspections.</p>
        ) : (
          <ul className="activity-list">
            {RecentActivity.Inspections.map((item) => (
              <li key={item.InspectionId}>
                <strong>{item.PropertyName}</strong> — {item.Status} — inspected by{" "}
                {item.InspectorName} on {item.InspectionDate}
              </li>
            ))}
          </ul>
        )}

        <h3>Maintenance issues</h3>
        {RecentActivity.MaintenanceIssues.length === 0 ? (
          <p className="empty-state">No open maintenance issues.</p>
        ) : (
          <ul className="activity-list">
            {RecentActivity.MaintenanceIssues.map((item) => (
              <li key={item.MaintenanceIssueId}>
                <strong>{item.PropertyName}</strong> — {item.Title} ({item.Priority},{" "}
                {item.Status})
              </li>
            ))}
          </ul>
        )}

        <h3>High / critical risks</h3>
        {RecentActivity.RiskAssessments.length === 0 ? (
          <p className="empty-state">No high or critical open risks.</p>
        ) : (
          <ul className="activity-list">
            {RecentActivity.RiskAssessments.map((item) => (
              <li key={item.RiskAssessmentId}>
                <strong>{item.PropertyName}</strong> — {item.Hazard} ({item.RiskLevel}, score{" "}
                {item.RiskScore})
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
