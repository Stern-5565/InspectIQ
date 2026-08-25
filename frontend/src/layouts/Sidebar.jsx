/**
 * Nav list only - grows one <NavLink> per module as each module's frontend gets built
 * (Dashboard, Properties, Inspection Templates, Inspections, Maintenance, Risk Register,
 * Cleaning, Vacant Units, Meter Readings, Admin Settings so far). Mobile-first: collapsed
 * off-canvas by default below the desktop breakpoint, toggled by Header's hamburger button (see
 * MainLayout's `sidebarOpen` state) - always visible on wider viewports regardless of that
 * state (styles/global.css). Every link above Admin Settings carries no role gate here even
 * though managing a property or starting an inspection does (constants/roles.js) - every role
 * can at least view each list, so those nav links stay unconditional. Admin Settings is the
 * first exception: the whole page is Administrator-only even to VIEW (App.jsx), so showing the
 * link to anyone else would just send them to the Unauthorized page - gated here with
 * `hasAnyRole` rather than leaving it unconditional like every link above it.
 */
import { NavLink } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { hasAnyRole } from "../utilities/permissions";
import { CAN_MANAGE_ADMIN_SETTINGS } from "../constants/roles";

export function Sidebar({ open, onNavigate }) {
  const { user } = useAuth();

  return (
    <>
      {open && <div className="sidebar-backdrop" onClick={onNavigate} aria-hidden="true" />}
      <nav className={`sidebar${open ? " sidebar--open" : ""}`} aria-label="Main navigation">
        <div className="sidebar__brand">InspectIQ</div>
        <NavLink to="/" end className="sidebar__link" onClick={onNavigate}>
          Dashboard
        </NavLink>
        <NavLink to="/properties" className="sidebar__link" onClick={onNavigate}>
          Properties
        </NavLink>
        <NavLink to="/inspection-templates" className="sidebar__link" onClick={onNavigate}>
          Inspection Templates
        </NavLink>
        <NavLink to="/inspections" className="sidebar__link" onClick={onNavigate}>
          Inspections
        </NavLink>
        <NavLink to="/maintenance-issues" className="sidebar__link" onClick={onNavigate}>
          Maintenance
        </NavLink>
        <NavLink to="/risk-assessments" className="sidebar__link" onClick={onNavigate}>
          Risk Register
        </NavLink>
        <NavLink to="/cleaning-inspections" className="sidebar__link" onClick={onNavigate}>
          Cleaning
        </NavLink>
        <NavLink to="/vacant-unit-inspections" className="sidebar__link" onClick={onNavigate}>
          Vacant Units
        </NavLink>
        <NavLink to="/meter-readings" className="sidebar__link" onClick={onNavigate}>
          Meter Readings
        </NavLink>
        {hasAnyRole(user, CAN_MANAGE_ADMIN_SETTINGS) && (
          <NavLink to="/admin-settings" className="sidebar__link" onClick={onNavigate}>
            Admin Settings
          </NavLink>
        )}
      </nav>
    </>
  );
}
