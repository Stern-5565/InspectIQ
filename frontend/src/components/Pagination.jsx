/**
 * Prev/next pager matching every backend list endpoint's PaginatedResponse shape (page,
 * page_size, total, - see app/schemas/pagination.py). Deliberately just prev/next + a range
 * label, not individual page-number buttons.
 */
export function Pagination({ page, pageSize, totalItems, onPageChange }) {
  if (totalItems === 0) {
    return null;
  }

  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const rangeStart = (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(page * pageSize, totalItems);

  return (
    <nav className="pagination" aria-label="Pagination">
      <span className="pagination__summary">
        Showing {rangeStart}-{rangeEnd} of {totalItems}
      </span>
      <div className="pagination__controls">
        <button
          type="button"
          className="button button--secondary"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <span aria-live="polite">
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          className="button button--secondary"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </nav>
  );
}
