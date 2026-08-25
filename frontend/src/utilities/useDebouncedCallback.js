import { useEffect, useRef } from "react";

/**
 * Returns a debounced version of `callback` plus a `flush(arg)` escape hatch that cancels any
 * pending timer and calls immediately - used for onBlur so navigating away doesn't wait out the
 * debounce window. Blur alone isn't reliable enough on its own for a field an inspector is
 * typing into on a phone (backgrounding the app or the OS dismissing the keyboard doesn't
 * always fire it), so debounce-while-typing is the primary save path and blur/flush is a
 * fallback, not the only save trigger - found while verifying InspectionQuestionPage's Text/
 * Number/Notes fields (2026-08-25).
 */
export function useDebouncedCallback(callback, delayMs = 700) {
  const callbackRef = useRef(callback);
  const timerRef = useRef(null);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => () => clearTimeout(timerRef.current), []);

  function debounced(arg) {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => callbackRef.current(arg), delayMs);
  }

  function flush(arg) {
    clearTimeout(timerRef.current);
    callbackRef.current(arg);
  }

  return [debounced, flush];
}
