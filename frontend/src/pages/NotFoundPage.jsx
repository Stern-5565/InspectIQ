import { Link } from "react-router-dom";
import { getDefaultLandingPath } from "../utilities/permissions";

export function NotFoundPage() {
  return (
    <div className="status-page">
      <h1>404 - Page not found</h1>
      <p>The page you're looking for doesn't exist.</p>
      <Link to={getDefaultLandingPath()} className="button">
        Back to dashboard
      </Link>
    </div>
  );
}
