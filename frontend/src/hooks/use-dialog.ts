'use client';

import { useState, useCallback } from 'react';

/**
 * Dialog state hook for managing common dialog patterns.
 * Centralizes open/close, loading, and error state management.
 */
export interface UseDialogReturn<T = undefined> {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Whether an async action is in progress */
  isLoading: boolean;
  /** Error message if action failed */
  error: string | null;
  /** Data passed when opening the dialog */
  data: T | null;
  /** Open the dialog, optionally with data */
  open: (data?: T) => void;
  /** Close the dialog and reset state */
  close: () => void;
  /** Set loading state */
  setLoading: (loading: boolean) => void;
  /** Set error message */
  setError: (error: string | null) => void;
  /** Reset error and loading state */
  reset: () => void;
  /** Execute async action with automatic loading/error handling */
  execute: <R>(action: () => Promise<R>) => Promise<R | undefined>;
}

/**
 * Custom hook for dialog state management.
 *
 * @example
 * // Simple dialog
 * const dialog = useDialog();
 * <Button onClick={() => dialog.open()}>Open</Button>
 * <Dialog open={dialog.isOpen} onOpenChange={(open) => !open && dialog.close()}>
 *   ...
 * </Dialog>
 *
 * @example
 * // Dialog with data
 * const deleteDialog = useDialog<License>();
 * <Button onClick={() => deleteDialog.open(license)}>Delete</Button>
 * // Access deleteDialog.data in the dialog content
 *
 * @example
 * // With async action
 * const handleConfirm = async () => {
 *   await dialog.execute(async () => {
 *     await api.deleteLicense(dialog.data!.id);
 *     showToast('Deleted successfully', 'success');
 *     dialog.close();
 *   });
 * };
 */
export function useDialog<T = undefined>(): UseDialogReturn<T> {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<T | null>(null);

  const open = useCallback((newData?: T) => {
    setData(newData ?? null);
    setError(null);
    setIsLoading(false);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    // Delay clearing data to allow for close animation
    setTimeout(() => {
      setData(null);
      setError(null);
      setIsLoading(false);
    }, 200);
  }, []);

  const reset = useCallback(() => {
    setError(null);
    setIsLoading(false);
  }, []);

  const execute = useCallback(async <R,>(action: () => Promise<R>): Promise<R | undefined> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await action();
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred';
      setError(message);
      return undefined;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    isOpen,
    isLoading,
    error,
    data,
    open,
    close,
    setLoading: setIsLoading,
    setError,
    reset,
    execute,
  };
}

/**
 * Hook for managing confirmation dialogs with a simple confirm/cancel pattern.
 */
export interface UseConfirmDialogReturn<T = undefined> extends UseDialogReturn<T> {
  /** Confirm the action */
  confirm: () => Promise<boolean>;
  /** Resolver for the confirm promise */
  onConfirm: (() => void) | null;
}

/**
 * Custom hook for confirmation dialogs.
 * Returns a promise that resolves when the user confirms or rejects.
 *
 * @example
 * const confirmDialog = useConfirmDialog<string>();
 *
 * const handleDelete = async () => {
 *   confirmDialog.open('item-id');
 *   const confirmed = await confirmDialog.confirm();
 *   if (confirmed) {
 *     await api.delete(confirmDialog.data);
 *   }
 * };
 */
export function useConfirmDialog<T = undefined>(): UseConfirmDialogReturn<T> {
  const dialog = useDialog<T>();
  const [resolver, setResolver] = useState<((value: boolean) => void) | null>(null);

  const confirm = useCallback((): Promise<boolean> => {
    return new Promise((resolve) => {
      setResolver(() => resolve);
    });
  }, []);

  const handleConfirm = useCallback(() => {
    if (resolver) {
      resolver(true);
      setResolver(null);
    }
    dialog.close();
  }, [resolver, dialog]);

  const handleClose = useCallback(() => {
    if (resolver) {
      resolver(false);
      setResolver(null);
    }
    dialog.close();
  }, [resolver, dialog]);

  return {
    ...dialog,
    close: handleClose,
    confirm,
    onConfirm: resolver ? handleConfirm : null,
  };
}
