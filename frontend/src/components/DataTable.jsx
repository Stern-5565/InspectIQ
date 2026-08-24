/**
 * Generic list-page table. Pass it `columns` (what to show) and `rows` (the page of data from
 * the module's API service), and it handles the loading/error/empty states that would
 * otherwise be re-implemented on every page.
 *
 * `columns` shape: [{ key, header, render?(row) }]. `render` is optional - without it, the
 * cell just shows `row[key]`; with it, a column can show a computed value or another
 * component (e.g. <StatusBadge status={row.PropertyStatus} />) without DataTable needing to
 * know anything about that column's content.
 */
import { LoadingSpinner } from "./LoadingSpinner";
import { ErrorMessage } from "./ErrorMessage";
import { EmptyState } from "./EmptyState";

export function DataTable({
  columns,
  rows,
  getRowKey = (row, index) => row.id ?? index,
  loading = false,
  error = null,
  onRetry,
  emptyMessage = "No records found.",
}) {
  if (loading) {
    return (
      <div className="data-table__status">
        <LoadingSpinner label="Loading records…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="data-table__status">
        <ErrorMessage message={error} onRetry={onRetry} />
      </div>
    );
  }

  if (rows.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <div className="data-table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col">
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={getRowKey(row, index)}>
              {columns.map((column) => (
                <td key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
