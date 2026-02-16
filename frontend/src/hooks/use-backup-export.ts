'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

interface UseBackupExportProps {
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onError?: (error: string) => void;
  /** Translation function for fallback error messages */
  fallbackErrorMessage: string;
}

export interface UseBackupExportReturn {
  password: string;
  setPassword: (value: string) => void;
  confirmPassword: string;
  setConfirmPassword: (value: string) => void;
  showPassword: boolean;
  setShowPassword: (value: boolean) => void;
  showConfirmPassword: boolean;
  setShowConfirmPassword: (value: boolean) => void;
  isLoading: boolean;
  error: string | null;
  passwordsMatch: boolean;
  isPasswordValid: boolean;
  canSubmit: boolean;
  handleExport: () => Promise<void>;
  handleClose: () => void;
}

/**
 * Custom hook that encapsulates all business logic for the BackupExportDialog component.
 * Manages password state, validation, backup creation, and file download.
 */
export function useBackupExport({
  onOpenChange,
  onSuccess,
  onError,
  fallbackErrorMessage,
}: UseBackupExportProps): UseBackupExportReturn {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordsMatch = password === confirmPassword;
  const isPasswordValid = password.length >= 8;
  const canSubmit = isPasswordValid && passwordsMatch && password.length > 0;

  const handleExport = async () => {
    if (!canSubmit) return;

    setIsLoading(true);
    setError(null);

    try {
      const blob = await api.createBackup(password);

      // Generate filename with timestamp
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-');
      const filename = `licence-backup-${timestamp}.lcbak`;

      // Trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      // Reset form and close
      setPassword('');
      setConfirmPassword('');
      onOpenChange(false);
      onSuccess?.();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : fallbackErrorMessage;
      setError(message);
      onError?.(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setPassword('');
      setConfirmPassword('');
      setError(null);
      onOpenChange(false);
    }
  };

  return {
    password,
    setPassword,
    confirmPassword,
    setConfirmPassword,
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading,
    error,
    passwordsMatch,
    isPasswordValid,
    canSubmit,
    handleExport,
    handleClose,
  };
}
