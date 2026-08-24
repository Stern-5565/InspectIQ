import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export function Header({ onToggleSidebar }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="header">
      <button
        type="button"
        className="header__menu-toggle"
        onClick={onToggleSidebar}
        aria-label="Toggle navigation"
      >
        <span aria-hidden="true">☰</span>
      </button>
      <div className="header__user">
        <span className="header__name">
          {user.FirstName} {user.LastName}
        </span>
        <span className="header__roles">{user.Roles.join(", ")}</span>
        <button type="button" className="button button--secondary" onClick={handleLogout}>
          Log out
        </button>
      </div>
    </header>
  );
}
