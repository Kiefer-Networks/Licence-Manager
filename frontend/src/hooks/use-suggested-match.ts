'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

interface UseSuggestedMatchTranslations {
  failedToConfirmMatch: string;
  failedToRejectMatch: string;
  failedToMarkAsGuest: string;
}

interface UseSuggestedMatchProps {
  licenseId: string;
  onUpdate?: () => void;
  messages: UseSuggestedMatchTranslations;
}

export interface UseSuggestedMatchReturn {
  isLoading: boolean;
  error: string | null;
  handleConfirm: () => Promise<void>;
  handleReject: () => Promise<void>;
  handleMarkAsGuest: () => Promise<void>;
}

/**
 * Custom hook that encapsulates all business logic for the SuggestedMatchCard component.
 * Manages confirm, reject, and mark-as-guest API operations.
 */
export function useSuggestedMatch({
  licenseId,
  onUpdate,
  messages,
}: UseSuggestedMatchProps): UseSuggestedMatchReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.confirmLicenseMatch(licenseId);
      onUpdate?.();
    } catch (err) {
      setError(messages.failedToConfirmMatch);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReject = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.rejectLicenseMatch(licenseId);
      onUpdate?.();
    } catch (err) {
      setError(messages.failedToRejectMatch);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMarkAsGuest = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.markAsExternalGuest(licenseId);
      onUpdate?.();
    } catch (err) {
      setError(messages.failedToMarkAsGuest);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    isLoading,
    error,
    handleConfirm,
    handleReject,
    handleMarkAsGuest,
  };
}
