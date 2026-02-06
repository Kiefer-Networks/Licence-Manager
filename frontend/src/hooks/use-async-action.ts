'use client';

import { useState, useCallback } from 'react';
import { handleSilentError } from '@/lib/error-handler';

/**
 * Options for the useAsyncAction hook.
 */
export interface UseAsyncActionOptions<T> {
  /** Callback function when action succeeds */
  onSuccess?: (result: T) => void;
  /** Callback function when action fails */
  onError?: (error: Error) => void;
  /** Context name for error logging */
  errorContext?: string;
}

/**
 * Return type for the useAsyncAction hook.
 */
export interface UseAsyncActionReturn<TArgs extends unknown[], TResult> {
  /** Execute the async action */
  execute: (...args: TArgs) => Promise<TResult | undefined>;
  /** Whether the action is currently loading */
  loading: boolean;
  /** Last error that occurred */
  error: Error | null;
  /** Reset error state */
  clearError: () => void;
}

/**
 * Hook for handling async actions with automatic loading and error state management.
 *
 * Consolidates the common pattern of:
 * - Setting loading state
 * - Executing async action
 * - Handling errors with handleSilentError
 * - Resetting loading state in finally
 *
 * @example
 * ```tsx
 * const { execute: deleteItem, loading: deleting } = useAsyncAction(
 *   async (id: string) => {
 *     await api.deleteItem(id);
 *     onUpdate?.();
 *   },
 *   { errorContext: 'deleteItem' }
 * );
 *
 * // In JSX:
 * <Button onClick={() => deleteItem(item.id)} disabled={deleting}>
 *   {deleting ? 'Deleting...' : 'Delete'}
 * </Button>
 * ```
 */
export function useAsyncAction<TArgs extends unknown[], TResult>(
  action: (...args: TArgs) => Promise<TResult>,
  options: UseAsyncActionOptions<TResult> = {}
): UseAsyncActionReturn<TArgs, TResult> {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const { onSuccess, onError, errorContext = 'asyncAction' } = options;

  const execute = useCallback(
    async (...args: TArgs): Promise<TResult | undefined> => {
      setLoading(true);
      setError(null);
      try {
        const result = await action(...args);
        onSuccess?.(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        handleSilentError(errorContext, err);
        onError?.(error);
        return undefined;
      } finally {
        setLoading(false);
      }
    },
    [action, onSuccess, onError, errorContext]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    execute,
    loading,
    error,
    clearError,
  };
}

/**
 * Hook for managing multiple related loading states.
 *
 * @example
 * ```tsx
 * const { isLoading, startLoading, stopLoading, withLoading } = useLoadingStates([
 *   'save', 'delete', 'refresh'
 * ]);
 *
 * // Check if any action is loading
 * const anyLoading = isLoading('save') || isLoading('delete');
 *
 * // Execute with automatic loading state
 * await withLoading('save', async () => {
 *   await api.save(data);
 * });
 * ```
 */
export function useLoadingStates<T extends string>(keys: T[]) {
  const [loadingStates, setLoadingStates] = useState<Record<T, boolean>>(
    () => Object.fromEntries(keys.map((k) => [k, false])) as Record<T, boolean>
  );

  const isLoading = useCallback(
    (key: T) => loadingStates[key],
    [loadingStates]
  );

  const startLoading = useCallback((key: T) => {
    setLoadingStates((prev) => ({ ...prev, [key]: true }));
  }, []);

  const stopLoading = useCallback((key: T) => {
    setLoadingStates((prev) => ({ ...prev, [key]: false }));
  }, []);

  const withLoading = useCallback(
    async <R>(key: T, fn: () => Promise<R>): Promise<R> => {
      startLoading(key);
      try {
        return await fn();
      } finally {
        stopLoading(key);
      }
    },
    [startLoading, stopLoading]
  );

  return {
    isLoading,
    startLoading,
    stopLoading,
    withLoading,
    loadingStates,
  };
}
