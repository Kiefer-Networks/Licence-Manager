'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Hook for debouncing a value.
 *
 * Returns the debounced value that only updates after the specified delay
 * has passed since the last change.
 *
 * @example
 * ```tsx
 * const [search, setSearch] = useState('');
 * const debouncedSearch = useDebounce(search, 300);
 *
 * useEffect(() => {
 *   // This only runs 300ms after the user stops typing
 *   fetchResults(debouncedSearch);
 * }, [debouncedSearch]);
 * ```
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Hook for debouncing a callback function.
 *
 * Returns a debounced version of the callback that only executes
 * after the specified delay has passed since the last invocation.
 *
 * @example
 * ```tsx
 * const handleSearch = useDebouncedCallback(
 *   (query: string) => fetchResults(query),
 *   300
 * );
 *
 * return <input onChange={(e) => handleSearch(e.target.value)} />;
 * ```
 */
export function useDebouncedCallback<TArgs extends unknown[]>(
  callback: (...args: TArgs) => void,
  delay: number = 300
): (...args: TArgs) => void {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(callback);

  // Update callback ref on each render
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return useCallback(
    (...args: TArgs) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        callbackRef.current(...args);
      }, delay);
    },
    [delay]
  );
}

/**
 * Hook for debounced search with loading state.
 *
 * Combines debouncing with automatic trigger on dialog open.
 *
 * @example
 * ```tsx
 * const {
 *   query,
 *   setQuery,
 *   loading,
 *   results,
 *   clear
 * } = useDebouncedSearch(
 *   async (searchQuery) => api.searchItems(searchQuery),
 *   { delay: 300, minLength: 0 }
 * );
 * ```
 */
export interface UseDebouncedSearchOptions {
  /** Debounce delay in ms (default: 300) */
  delay?: number;
  /** Minimum query length to trigger search (default: 0) */
  minLength?: number;
  /** Whether the search is active/visible (default: true) */
  enabled?: boolean;
}

export function useDebouncedSearch<T>(
  searchFn: (query: string) => Promise<T[]>,
  options: UseDebouncedSearchOptions = {}
) {
  const { delay = 300, minLength = 0, enabled = true } = options;

  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<T[]>([]);

  const debouncedQuery = useDebounce(query, delay);

  useEffect(() => {
    if (!enabled) return;

    const trimmed = debouncedQuery.trim();
    if (trimmed.length < minLength && minLength > 0) {
      setResults([]);
      return;
    }

    const fetchResults = async () => {
      setLoading(true);
      try {
        const data = await searchFn(trimmed);
        setResults(data);
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [debouncedQuery, enabled, minLength, searchFn]);

  const clear = useCallback(() => {
    setQuery('');
    setResults([]);
  }, []);

  return {
    query,
    setQuery,
    loading,
    results,
    clear,
  };
}
