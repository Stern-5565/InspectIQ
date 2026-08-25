/**
 * Nav list only - grows one <NavLink> per module as each module's frontend gets built
 * (Dashboard, Properties, Inspection Templates so far). Mobile-first: collapsed off-canvas by
 * default below the desktop breakpoint, toggled by Header's hamburger button (see MainLayout's
 * `sidebarOpen` state) - always visible on wider viewports regardless of that state
 * (styles/global.css). Properties/Inspection Templates have no role gate here even though
 * managing a property does (constants/roles.js) - every role can at least view both, so the nav
 * links themselves stay unconditional.
 */
import { NavLink } from "react-router-dom";

export function Sidebar({ open, onNavigate }) {
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
      </nav>
    </>
  );
}
