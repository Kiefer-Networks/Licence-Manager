'use client';

import { useState, useCallback } from 'react';
import { api, BackupRestoreResponse } from '@/lib/api';

interface UseBackupRestoreProps {
  onOpenChange: (open: boolean) => void;
  onSuccess?: (result: BackupRestoreResponse) => void;
  onError?: (error: string) => void;
  /** Translation function for fallback error messages */
  fallbackErrorMessage: string;
  /** Translation for invalid file type */
  invalidFileMessage: string;
}

export interface UseBackupRestoreReturn {
  file: File | null;
  password: string;
  setPassword: (value: string) => void;
  showPassword: boolean;
  setShowPassword: (value: boolean) => void;
  confirmed: boolean;
  setConfirmed: (value: boolean) => void;
  isLoading: boolean;
  error: string | null;
  result: BackupRestoreResponse | null;
  isDragging: boolean;
  canSubmit: boolean;
  handleFileSelect: (selectedFile: File) => void;
  handleDrop: (e: React.DragEvent) => void;
  handleDragOver: (e: React.DragEvent) => void;
  handleDragLeave: (e: React.DragEvent) => void;
  handleRestore: () => Promise<void>;
  handleClose: () => void;
}

/**
 * Custom hook that encapsulates all business logic for the BackupRestoreDialog component.
 * Manages file upload, password, confirmation, and restore execution.
 */
export function useBackupRestore({
  onOpenChange,
  onSuccess,
  onError,
  fallbackErrorMessage,
  invalidFileMessage,
}: UseBackupRestoreProps): UseBackupRestoreReturn {
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BackupRestoreResponse | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const canSubmit = !!(file && password.length >= 8 && confirmed && !result);

  const handleFileSelect = (selectedFile: File) => {
    if (selectedFile.name.endsWith('.lcbak')) {
      setFile(selectedFile);
      setError(null);
    } else {
      setError(invalidFileMessage);
      setFile(null);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleRestore = async () => {
    if (!file || !canSubmit) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.restoreBackup(file, password);
      setResult(response);

      if (response.success) {
        onSuccess?.(response);
      } else {
        setError(response.error || fallbackErrorMessage);
        onError?.(response.error || fallbackErrorMessage);
      }
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
      setFile(null);
      setPassword('');
      setConfirmed(false);
      setError(null);
      setResult(null);
      onOpenChange(false);
    }
  };

  return {
    file,
    password,
    setPassword,
    showPassword,
    setShowPassword,
    confirmed,
    setConfirmed,
    isLoading,
    error,
    result,
    isDragging,
    canSubmit,
    handleFileSelect,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    handleRestore,
    handleClose,
  };
}
