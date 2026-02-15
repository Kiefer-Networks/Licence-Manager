'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api, BackupRestoreResponse } from '@/lib/api';

export type SetupStep = 'restore' | 'welcome' | 'hibob' | 'providers' | 'complete';

export interface SetupStatus {
  is_complete: boolean;
}

/**
 * Return type for the useSetup hook.
 */
export interface UseSetupReturn {
  // Wizard state
  step: SetupStep;
  setStep: (step: SetupStep) => void;
  setupStatus: SetupStatus | null;
  loading: boolean;
  error: string | null;
  steps: { id: string; label: string }[];
  currentStepIndex: number;

  // HiBob credentials
  hibobAuthToken: string;
  setHibobAuthToken: (token: string) => void;

  // Backup restore state
  backupFile: File | null;
  backupPassword: string;
  setBackupPassword: (password: string) => void;
  showPassword: boolean;
  setShowPassword: (show: boolean) => void;
  isDragging: boolean;
  restoreResult: BackupRestoreResponse | null;

  // Actions
  handleFileSelect: (selectedFile: File) => void;
  handleDrop: (e: React.DragEvent) => void;
  handleDragOver: (e: React.DragEvent) => void;
  handleDragLeave: (e: React.DragEvent) => void;
  handleRestore: () => Promise<void>;
  handleSkipRestore: () => void;
  handleHibobSetup: () => Promise<void>;
  handleSkipProviders: () => void;
  handleComplete: () => Promise<void>;
}

/**
 * Custom hook that encapsulates all business logic for the Setup page.
 * Manages multi-step wizard, backup restore, credential setup, and status checking.
 */
export function useSetup(
  t: (key: string, params?: Record<string, string | number>) => string,
  tProviders: (key: string) => string,
  tSettings: (key: string) => string,
): UseSetupReturn {
  const router = useRouter();
  const [step, setStep] = useState<SetupStep>('restore');
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // HiBob credentials - cleared on unmount for security
  const [hibobAuthToken, setHibobAuthToken] = useState('');

  // Backup restore state
  const [backupFile, setBackupFile] = useState<File | null>(null);
  const [backupPassword, setBackupPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [restoreResult, setRestoreResult] = useState<BackupRestoreResponse | null>(null);

  // Clear sensitive data on unmount to prevent memory exposure
  useEffect(() => {
    return () => {
      setHibobAuthToken('');
      setBackupPassword('');
    };
  }, []);

  useEffect(() => {
    async function checkStatus() {
      try {
        const status = await api.getSetupStatus();
        setSetupStatus(status);
        if (status.is_complete) {
          router.push('/dashboard');
        }
      } catch {
        // Silently handle - user will see setup page
      }
    }
    checkStatus();
  }, [router]);

  const handleFileSelect = (selectedFile: File) => {
    if (selectedFile.name.endsWith('.lcbak')) {
      setBackupFile(selectedFile);
      setError(null);
    } else {
      setError(tSettings('selectBackupFile'));
      setBackupFile(null);
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
    if (!backupFile || backupPassword.length < 8) return;

    setLoading(true);
    setError(null);

    try {
      const result = await api.setupRestoreBackup(backupFile, backupPassword);
      setRestoreResult(result);

      if (result.success) {
        // Redirect to dashboard after successful restore
        setTimeout(() => {
          router.push('/dashboard');
        }, 2000);
      } else {
        setError(result.error || tSettings('restoreFailed'));
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : tSettings('restoreFailed');
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleSkipRestore = () => {
    setStep('welcome');
  };

  const handleHibobSetup = async () => {
    setLoading(true);
    setError(null);

    // Copy token for use, then clear from state immediately for security
    const token = hibobAuthToken;

    try {
      // Test connection first
      const testResult = await api.testProviderConnection('hibob', {
        auth_token: token,
      });

      if (!testResult.success) {
        setError(testResult.message);
        return;
      }

      // Create provider
      await api.createProvider({
        name: 'hibob',
        display_name: tProviders('hibob'),
        credentials: {
          auth_token: token,
        },
      });

      // Clear sensitive data from state after successful submission
      setHibobAuthToken('');
      setStep('providers');
    } catch (err: unknown) {
      // Sanitize error message - don't expose internal details
      const message = err instanceof Error ? err.message : t('configurationFailed');
      setError(message.includes('token') ? t('invalidCredentials') : message);
    } finally {
      setLoading(false);
    }
  };

  const handleSkipProviders = () => {
    setStep('complete');
  };

  const handleComplete = async () => {
    // Trigger initial sync (non-blocking, errors are logged server-side)
    try {
      await api.triggerSync();
    } catch {
      // Sync failures are handled server-side, don't block navigation
    }
    router.push('/dashboard');
  };

  const steps = [
    { id: 'restore', label: t('restoreBackup') },
    { id: 'welcome', label: t('welcome') },
    { id: 'hibob', label: tProviders('hibob') },
    { id: 'providers', label: tProviders('title') },
    { id: 'complete', label: t('complete') },
  ];

  const currentStepIndex = steps.findIndex((s) => s.id === step);

  return {
    // Wizard state
    step,
    setStep,
    setupStatus,
    loading,
    error,
    steps,
    currentStepIndex,

    // HiBob credentials
    hibobAuthToken,
    setHibobAuthToken,

    // Backup restore state
    backupFile,
    backupPassword,
    setBackupPassword,
    showPassword,
    setShowPassword,
    isDragging,
    restoreResult,

    // Actions
    handleFileSelect,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    handleRestore,
    handleSkipRestore,
    handleHibobSetup,
    handleSkipProviders,
    handleComplete,
  };
}
