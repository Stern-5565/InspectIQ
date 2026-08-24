/**
 * Debounced search box - "type, pause, then re-fetch with ?search=..." rather than firing a
 * request on every keystroke.
 *
 * `value` is the source of truth (a parent's `search` state used to build the API query) so
 * clearing filters externally resets this input too; `onSearch` fires `debounceMs` after the
 * user stops typing, not on every keystroke.
 */
import { useEffect, useRef, useState } from "react";

export function SearchInput({ value, onSearch, placeholder = "Search…", debounceMs = 300 }) {
  const [localValue, setLocalValue] = useState(value ?? "");
  const debounceRef = useRef(null);

  useEffect(() => {
    setLocalValue(value ?? "");
  }, [value]);

  useEffect(() => () => clearTimeout(debounceRef.current), []);

  function handleChange(event) {
    const next = event.target.value;
    setLocalValue(next);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onSearch(next), debounceMs);
  }

  return (
    <input
      type="search"
      className="search-input"
      value={localValue}
      onChange={handleChange}
      placeholder={placeholder}
      aria-label={placeholder}
    />
  );
}
