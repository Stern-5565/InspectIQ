/**
 * The whole route is gated to Administrator only (App.jsx wraps it in
 * `<ProtectedRoute allowedRoles={CAN_MANAGE_ADMIN_SETTINGS}>`) - the first page in this project
 * where even VIEWING is role-restricted, not just mutation (constants/roles.js explains why).
 * That means every control on this page is always "manage" mode - there's no separate
 * view-only render path the way PropertyDetailPage's CleaningAreas section needs one, since
 * nobody who isn't already an Administrator can reach this component at all.
 *
 * Two sections, matching scope §3/§4's own two entities: Company Profile (one record, inline
 * edit) and Team Members (a list, inline edit per row + an add-user form) - the exact
 * inline-edit-row / add-form-below-the-table shape `PropertyDetailPage.jsx`'s Units/Cleaning
 * Areas sections already established, reused here rather than inventing a new pattern (a modal)
 * for what is structurally the same kind of "manage a small set of company config records" UI.
 *
 * A self-deactivation guard on the backend (app/services/user_service.py) rejects an
 * Administrator deactivating their own account with a 422 - mirrored here by disabling that
 * specific row's Deactivate button rather than letting the request round-trip just to fail.
 */
import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { EmptyState } from "../../components/EmptyState";
import { FormField } from "../../components/FormField";
import { SelectField } from "../../components/SelectField";
import { StatusBadge } from "../../components/StatusBadge";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { ALL_ROLES } from "../../constants/roles";
import { getCompany, updateCompany } from "../../services/companyService";
import { createUser, listUsers, updateUser } from "../../services/userService";
import { getErrorMessage } from "../../utilities/apiError";

const ROLE_OPTIONS = ALL_ROLES.map((role) => ({ value: role, label: role }));

function CompanyProfileSection({ toast, onToast }) {
  const [company, setCompany] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getCompany()
      .then(setCompany)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function startEdit() {
    setForm({
      CompanyName: company.CompanyName,
      AddressLine1: company.AddressLine1 ?? "",
      AddressLine2: company.AddressLine2 ?? "",
      City: company.City ?? "",
      Postcode: company.Postcode ?? "",
      Telephone: company.Telephone ?? "",
      Email: company.Email ?? "",
    });
    setSaveError(null);
    setEditing(true);
  }

  function handleSave(event) {
    event.preventDefault();
    if (!form.CompanyName.trim()) {
      setSaveError("Company name is required.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    updateCompany({
      CompanyName: form.CompanyName.trim(),
      AddressLine1: form.AddressLine1.trim() || null,
      AddressLine2: form.AddressLine2.trim() || null,
      City: form.City.trim() || null,
      Postcode: form.Postcode.trim() || null,
      Telephone: form.Telephone.trim() || null,
      Email: form.Email.trim() || null,
    })
      .then((updated) => {
        setCompany(updated);
        setEditing(false);
        onToast("Company profile updated.");
      })
      .catch((err) => setSaveError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  if (loading) {
    return <LoadingSpinner label="Loading company profile…" />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={load} />;
  }

  return (
    <section className="detail-card">
      <div className="detail-card__header">
        <h2>Company Profile</h2>
        {!editing && (
          <button type="button" className="button button--secondary button--small" onClick={startEdit}>
            Edit
          </button>
        )}
      </div>

      {toast && <Toast message={toast} onDismiss={() => onToast(null)} />}

      {!editing ? (
        <div className="detail-grid">
          <div className="detail-grid__item">
            <span className="detail-grid__label">Company name</span>
            <span>{company.CompanyName}</span>
          </div>
          <div className="detail-grid__item">
            <span className="detail-grid__label">Address</span>
            <span>
              {[company.AddressLine1, company.AddressLine2, company.City, company.Postcode].filter(Boolean).join(", ") || "—"}
            </span>
          </div>
          <div className="detail-grid__item">
            <span className="detail-grid__label">Telephone</span>
            <span>{company.Telephone ?? "—"}</span>
          </div>
          <div className="detail-grid__item">
            <span className="detail-grid__label">Email</span>
            <span>{company.Email ?? "—"}</span>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSave}>
          <div className="form-grid">
            <FormField
              label="Company name"
              name="CompanyName"
              value={form.CompanyName}
              onChange={(e) => setForm((prev) => ({ ...prev, CompanyName: e.target.value }))}
              required
            />
            <FormField
              label="Address line 1"
              name="AddressLine1"
              value={form.AddressLine1}
              onChange={(e) => setForm((prev) => ({ ...prev, AddressLine1: e.target.value }))}
            />
            <FormField
              label="Address line 2"
              name="AddressLine2"
              value={form.AddressLine2}
              onChange={(e) => setForm((prev) => ({ ...prev, AddressLine2: e.target.value }))}
            />
            <FormField label="City" name="City" value={form.City} onChange={(e) => setForm((prev) => ({ ...prev, City: e.target.value }))} />
            <FormField
              label="Postcode"
              name="Postcode"
              value={form.Postcode}
              onChange={(e) => setForm((prev) => ({ ...prev, Postcode: e.target.value }))}
            />
            <FormField
              label="Telephone"
              name="Telephone"
              value={form.Telephone}
              onChange={(e) => setForm((prev) => ({ ...prev, Telephone: e.target.value }))}
            />
            <FormField
              label="Email"
              name="Email"
              type="email"
              value={form.Email}
              onChange={(e) => setForm((prev) => ({ ...prev, Email: e.target.value }))}
            />
          </div>

          {saveError && <ErrorMessage message={saveError} />}

          <div className="form-card__actions">
            <button type="submit" className="button" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button type="button" className="button button--secondary" onClick={() => setEditing(false)} disabled={saving}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

function UserRow({ member, isSelf, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  function startEdit() {
    setForm({ FirstName: member.FirstName, LastName: member.LastName, Phone: member.Phone ?? "", RoleName: member.Roles[0] ?? "" });
    setError(null);
    setEditing(true);
  }

  function handleSave() {
    setSaving(true);
    setError(null);
    updateUser(member.UserId, {
      FirstName: form.FirstName.trim(),
      LastName: form.LastName.trim(),
      Phone: form.Phone.trim() || null,
      RoleName: form.RoleName,
    })
      .then((updated) => {
        onSaved(updated);
        setEditing(false);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  function handleToggleActive() {
    setSaving(true);
    setError(null);
    updateUser(member.UserId, { IsActive: !member.IsActive })
      .then(onSaved)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSaving(false));
  }

  if (editing) {
    return (
      <tr>
        <td colSpan={5}>
          <div className="unit-edit-row">
            <FormField label="First name" name="FirstName" value={form.FirstName} onChange={(e) => setForm((p) => ({ ...p, FirstName: e.target.value }))} required />
            <FormField label="Last name" name="LastName" value={form.LastName} onChange={(e) => setForm((p) => ({ ...p, LastName: e.target.value }))} required />
            <FormField label="Phone" name="Phone" value={form.Phone} onChange={(e) => setForm((p) => ({ ...p, Phone: e.target.value }))} />
            <SelectField label="Role" name="RoleName" value={form.RoleName} onChange={(e) => setForm((p) => ({ ...p, RoleName: e.target.value }))} options={ROLE_OPTIONS} required />
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
        {member.FirstName} {member.LastName}
        {isSelf && " (you)"}
      </td>
      <td>{member.Email}</td>
      <td>{member.Roles.join(", ") || "—"}</td>
      <td>
        <StatusBadge status={member.IsActive ? "Active" : "Inactive"} />
      </td>
      <td>
        <button type="button" className="button button--secondary button--small" onClick={startEdit}>
          Edit
        </button>{" "}
        <button
          type="button"
          className="button button--secondary button--small"
          onClick={handleToggleActive}
          disabled={saving || isSelf}
          title={isSelf ? "You cannot deactivate your own account." : undefined}
        >
          {saving ? "…" : member.IsActive ? "Deactivate" : "Reactivate"}
        </button>
        {error && <ErrorMessage message={error} />}
      </td>
    </tr>
  );
}

function AddUserForm({ onCreated, onCancel }) {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [roleName, setRoleName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function handleSubmit(event) {
    event.preventDefault();
    if (!firstName.trim() || !lastName.trim() || !email.trim() || !password || !roleName) {
      setError("First name, last name, email, password, and role are required.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    setError(null);
    createUser({ firstName: firstName.trim(), lastName: lastName.trim(), email: email.trim(), phone: phone.trim(), password, roleName })
      .then((user) => {
        onCreated(user);
        setFirstName("");
        setLastName("");
        setEmail("");
        setPhone("");
        setPassword("");
        setRoleName("");
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSubmitting(false));
  }

  return (
    <form className="unit-add-form" onSubmit={handleSubmit}>
      <FormField label="First name" name="firstName" value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
      <FormField label="Last name" name="lastName" value={lastName} onChange={(e) => setLastName(e.target.value)} required />
      <FormField label="Email" name="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <FormField label="Phone (optional)" name="phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
      <FormField label="Initial password" name="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <SelectField label="Role" name="roleName" value={roleName} onChange={(e) => setRoleName(e.target.value)} placeholder="Choose a role" options={ROLE_OPTIONS} required />
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

function TeamMembersSection() {
  const { user: currentUser } = useAuth();
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [addingUser, setAddingUser] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    listUsers({ includeInactive: true })
      .then(setMembers)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function replaceMember(updated) {
    setMembers((prev) => prev.map((m) => (m.UserId === updated.UserId ? updated : m)));
  }

  function handleCreated(user) {
    setMembers((prev) => [...prev, user].sort((a, b) => a.FirstName.localeCompare(b.FirstName)));
    setToast(`${user.FirstName} ${user.LastName} added.`);
    setAddingUser(false);
  }

  return (
    <section className="detail-card">
      <div className="detail-card__header">
        <h2>Team Members</h2>
        {!addingUser && (
          <button type="button" className="button button--secondary" onClick={() => setAddingUser(true)}>
            + Add team member
          </button>
        )}
      </div>

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      {addingUser && <AddUserForm onCreated={handleCreated} onCancel={() => setAddingUser(false)} />}

      {loading && <LoadingSpinner label="Loading team members…" />}
      {error && <ErrorMessage message={error} onRetry={load} />}

      {!loading && !error && members.length === 0 && <EmptyState message="No team members yet." />}

      {!loading && !error && members.length > 0 && (
        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Email</th>
                <th scope="col">Role</th>
                <th scope="col">Status</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <UserRow key={member.UserId} member={member} isSelf={member.UserId === currentUser.UserId} onSaved={replaceMember} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function AdminSettingsPage() {
  const [companyToast, setCompanyToast] = useState(null);

  return (
    <div>
      <PageHeader title="Admin Settings" description="Manage your company profile and team members." />
      <CompanyProfileSection toast={companyToast} onToast={setCompanyToast} />
      <TeamMembersSection />
    </div>
  );
}
