/**
 * Generic collapsible wrapper around a set of filter controls. Knows nothing about what's
 * being filtered - the page composes the actual fields (SelectField, ...) as children;
 * FilterPanel just provides the expand/collapse chrome and a "Clear filters" action.
 */
import { useState } from "react";

export function FilterPanel({ title = "Filters", children, onClear }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="filter-panel">
      <div className="filter-panel__header">
        <button
          type="button"
          className="filter-panel__toggle"
          onClick={() => setExpanded((prev) => !prev)}
          aria-expanded={expanded}
        >
          {title} {expanded ? "▲" : "▼"}
        </button>
        {onClear && (
          <button type="button" className="button button--secondary" onClick={onClear}>
            Clear filters
          </button>
        )}
      </div>
      {expanded && <div className="filter-panel__body">{children}</div>}
    </div>
  );
}
