/**
 * Nav list only - grows one <NavLink> per module as each module's frontend gets built
 * (Dashboard + Properties so far). Mobile-first: collapsed off-canvas by default below the
 * desktop breakpoint, toggled by Header's hamburger button (see MainLayout's `sidebarOpen`
 * state) - always visible on wider viewports regardless of that state (styles/global.css).
 * Properties has no role gate here even though creating/editing one does (constants/roles.js) -
 * every role can at least view the list, so the nav link itself stays unconditional.
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
      </nav>
    </>
  );
}
