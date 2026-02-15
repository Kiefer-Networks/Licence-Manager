'use client';

import { useEffect, useState } from 'react';
import {
  api,
  LicenseLifecycleOverview,
  ExpiringLicense,
  CancelledLicense,
} from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';

/**
 * Toast state for user feedback.
 */
export interface LifecycleToast {
  type: 'success' | 'error';
  text: string;
}

/**
 * Return type for the useLifecycle hook.
 */
export interface UseLifecycleReturn {
  // Data
  overview: LicenseLifecycleOverview | null;
  needsReorderLicenses: ExpiringLicense[];

  // Loading & toast
  loading: boolean;
  toast: LifecycleToast | null;

  // Tab state
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // Dialog states
  cancelDialogOpen: boolean;
  setCancelDialogOpen: (open: boolean) => void;
  renewDialogOpen: boolean;
  setRenewDialogOpen: (open: boolean) => void;
  selectedLicense: ExpiringLicense | CancelledLicense | null;
  setSelectedLicense: (license: ExpiringLicense | CancelledLicense | null) => void;

  // Actions
  fetchOverview: () => Promise<void>;
  handleCancel: (effectiveDate: string, reason: string) => Promise<void>;
  handleRenew: (newExpirationDate: string, clearCancellation: boolean) => Promise<void>;
  handleToggleNeedsReorder: (license: ExpiringLicense) => Promise<void>;
}

/**
 * Custom hook that encapsulates all business logic for the Lifecycle page.
 * Manages license lifecycle overview, cancellation, renewal, and reorder toggling.
 */
export function useLifecycle(
  t: (key: string, params?: Record<string, string | number>) => string,
): UseLifecycleReturn {
  const [overview, setOverview] = useState<LicenseLifecycleOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('expiring');
  const [toast, setToast] = useState<LifecycleToast | null>(null);

  // Dialog states
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [renewDialogOpen, setRenewDialogOpen] = useState(false);
  const [selectedLicense, setSelectedLicense] = useState<ExpiringLicense | CancelledLicense | null>(null);

  useEffect(() => {
    fetchOverview();
  }, []);

  async function fetchOverview() {
    try {
      const data = await api.getLicenseLifecycleOverview();
      setOverview(data);
    } catch (error) {
      handleSilentError('fetchLifecycleOverview', error);
    } finally {
      setLoading(false);
    }
  }

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 4000);
  };

  const handleCancel = async (effectiveDate: string, reason: string) => {
    if (!selectedLicense) return;
    try {
      await api.cancelLicense(selectedLicense.license_id, {
        effective_date: effectiveDate,
        reason: reason || undefined,
      });
      showToast('success', t('licenseCancelled'));
      fetchOverview();
    } catch (error) {
      showToast('error', t('failedToCancel'));
    }
  };

  const handleRenew = async (newExpirationDate: string, clearCancellation: boolean) => {
    if (!selectedLicense) return;
    try {
      await api.renewLicense(selectedLicense.license_id, {
        new_expiration_date: newExpirationDate,
        clear_cancellation: clearCancellation,
      });
      showToast('success', t('licenseRenewed'));
      fetchOverview();
    } catch (error) {
      showToast('error', t('failedToRenew'));
    }
  };

  const handleToggleNeedsReorder = async (license: ExpiringLicense) => {
    try {
      await api.setLicenseNeedsReorder(license.license_id, !license.needs_reorder);
      showToast('success', license.needs_reorder ? t('removedFromReorder') : t('addedToReorder'));
      fetchOverview();
    } catch (error) {
      showToast('error', t('failedToUpdate'));
    }
  };

  const needsReorderLicenses = overview?.expiring_licenses.filter(l => l.needs_reorder) || [];

  return {
    // Data
    overview,
    needsReorderLicenses,

    // Loading & toast
    loading,
    toast,

    // Tab state
    activeTab,
    setActiveTab,

    // Dialog states
    cancelDialogOpen,
    setCancelDialogOpen,
    renewDialogOpen,
    setRenewDialogOpen,
    selectedLicense,
    setSelectedLicense,

    // Actions
    fetchOverview,
    handleCancel,
    handleRenew,
    handleToggleNeedsReorder,
  };
}
