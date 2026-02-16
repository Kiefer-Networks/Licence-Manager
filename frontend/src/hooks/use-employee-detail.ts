'use client';

import { useState, useCallback, useEffect } from 'react';
import { api, Employee, License, Provider, ExternalAccount } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';

/**
 * Toast state for user feedback.
 */
export interface Toast {
  type: 'success' | 'error';
  text: string;
}

/**
 * Return type for the useEmployeeDetail hook.
 */
export interface UseEmployeeDetailReturn {
  // Core data
  employee: Employee | null;
  licenses: License[];
  ownedAdminAccounts: License[];
  providers: Provider[];
  externalAccounts: ExternalAccount[];
  loading: boolean;

  // Toast
  toast: Toast | null;
  showToast: (type: 'success' | 'error', text: string) => void;

  // Assign License Dialog
  assignDialogOpen: boolean;
  setAssignDialogOpen: (open: boolean) => void;
  availableLicenses: License[];
  selectedLicenseId: string;
  setSelectedLicenseId: (id: string) => void;
  loadingAvailable: boolean;
  openAssignDialog: () => Promise<void>;
  handleAssignLicense: () => Promise<void>;

  // Remove Dialog
  removeDialog: License | null;
  setRemoveDialog: (license: License | null) => void;
  actionLoading: boolean;
  handleRemoveFromProvider: () => Promise<void>;

  // Unassign Dialog
  unassignDialog: License | null;
  setUnassignDialog: (license: License | null) => void;
  handleUnassignLicense: () => Promise<void>;

  // External Accounts
  linkDialogOpen: boolean;
  setLinkDialogOpen: (open: boolean) => void;
  selectedProviderType: string;
  setSelectedProviderType: (type: string) => void;
  externalUsername: string;
  setExternalUsername: (username: string) => void;
  unlinkDialog: ExternalAccount | null;
  setUnlinkDialog: (account: ExternalAccount | null) => void;
  handleLinkExternalAccount: () => Promise<void>;
  handleUnlinkExternalAccount: () => Promise<void>;

  // Computed values
  licenseMonthlyCost: number;
  adminAccountsMonthlyCost: number;
  totalMonthlyCost: number;
  manualProviders: Provider[];
  linkableProviderTypes: string[];
}

/**
 * Custom hook that encapsulates all business logic for the employee detail page.
 * Manages employee data, licenses, admin accounts, external accounts, and related actions.
 */
export function useEmployeeDetail(
  employeeId: string,
  t: (key: string, params?: Record<string, string | number>) => string,
  tCommon: (key: string) => string,
  tEmployees: (key: string, params?: Record<string, string | number>) => string,
): UseEmployeeDetailReturn {
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [licenses, setLicenses] = useState<License[]>([]);
  const [ownedAdminAccounts, setOwnedAdminAccounts] = useState<License[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<Toast | null>(null);

  // Assign License Dialog
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [availableLicenses, setAvailableLicenses] = useState<License[]>([]);
  const [selectedLicenseId, setSelectedLicenseId] = useState('');
  const [loadingAvailable, setLoadingAvailable] = useState(false);

  // Remove Dialog
  const [removeDialog, setRemoveDialog] = useState<License | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Unassign Dialog
  const [unassignDialog, setUnassignDialog] = useState<License | null>(null);

  // External Accounts
  const [externalAccounts, setExternalAccounts] = useState<ExternalAccount[]>([]);
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
  const [selectedProviderType, setSelectedProviderType] = useState('');
  const [externalUsername, setExternalUsername] = useState('');
  const [unlinkDialog, setUnlinkDialog] = useState<ExternalAccount | null>(null);

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  };

  // -- Fetch functions --

  const fetchEmployee = useCallback(async () => {
    try {
      const data = await api.getEmployee(employeeId);
      setEmployee(data);
    } catch (error) {
      handleSilentError('fetchEmployee', error);
    }
  }, [employeeId]);

  const fetchLicenses = useCallback(async () => {
    try {
      const data = await api.getLicenses({ employee_id: employeeId, page_size: 100 });
      setLicenses(data.items);
    } catch (error) {
      handleSilentError('fetchLicenses', error);
    }
  }, [employeeId]);

  const fetchProviders = useCallback(async () => {
    try {
      const data = await api.getProviders();
      setProviders(data.items);
    } catch (error) {
      handleSilentError('fetchProviders', error);
    }
  }, []);

  const fetchOwnedAdminAccounts = useCallback(async () => {
    try {
      const data = await api.getAdminAccountLicenses({ owner_id: employeeId, page_size: 100 });
      setOwnedAdminAccounts(data.items);
    } catch (error) {
      handleSilentError('fetchOwnedAdminAccounts', error);
    }
  }, [employeeId]);

  const fetchExternalAccounts = useCallback(async () => {
    try {
      const accounts = await api.getEmployeeExternalAccounts(employeeId);
      setExternalAccounts(accounts);
    } catch (error) {
      handleSilentError('fetchExternalAccounts', error);
    }
  }, [employeeId]);

  // -- Initial data load --

  useEffect(() => {
    Promise.all([fetchEmployee(), fetchLicenses(), fetchProviders(), fetchOwnedAdminAccounts(), fetchExternalAccounts()]).finally(() =>
      setLoading(false)
    );
  }, [fetchEmployee, fetchLicenses, fetchProviders, fetchOwnedAdminAccounts, fetchExternalAccounts]);

  // -- Handlers --

  const openAssignDialog = async () => {
    setAssignDialogOpen(true);
    setLoadingAvailable(true);
    try {
      // Get unassigned licenses from all providers
      const data = await api.getLicenses({ unassigned: true, page_size: 200 });
      setAvailableLicenses(data.items);
    } catch (error) {
      handleSilentError('fetchAvailableLicenses', error);
    } finally {
      setLoadingAvailable(false);
    }
  };

  const handleAssignLicense = async () => {
    if (!selectedLicenseId) return;
    setActionLoading(true);
    try {
      await api.assignManualLicense(selectedLicenseId, employeeId);
      showToast('success', t('licenseAssigned'));
      setAssignDialogOpen(false);
      setSelectedLicenseId('');
      await fetchLicenses();
      await fetchEmployee();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToAssign'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnassignLicense = async () => {
    if (!unassignDialog) return;
    setActionLoading(true);
    try {
      // Check if it's a manual license
      const license = unassignDialog;
      const provider = providers.find(p => p.id === license.provider_id);
      const isManual = provider?.config?.provider_type === 'manual' || provider?.name === 'manual';

      if (isManual) {
        await api.unassignManualLicense(license.id);
      } else {
        await api.bulkUnassignLicenses([license.id]);
      }
      showToast('success', t('licenseUnassigned'));
      setUnassignDialog(null);
      await fetchLicenses();
      await fetchEmployee();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUnassign'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRemoveFromProvider = async () => {
    if (!removeDialog) return;
    setActionLoading(true);
    try {
      const result = await api.removeLicenseFromProvider(removeDialog.id);
      if (result.success) {
        showToast('success', t('removedFromProvider'));
        setRemoveDialog(null);
        await fetchLicenses();
        await fetchEmployee();
      } else {
        showToast('error', result.message);
      }
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToRemove'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleLinkExternalAccount = async () => {
    if (!selectedProviderType || !externalUsername.trim()) return;
    setActionLoading(true);
    try {
      await api.linkExternalAccount(employeeId, {
        provider_type: selectedProviderType,
        external_username: externalUsername.trim(),
      });
      showToast('success', tEmployees('accountLinked'));
      setLinkDialogOpen(false);
      setSelectedProviderType('');
      setExternalUsername('');
      await fetchExternalAccounts();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : tEmployees('failedToLinkAccount'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnlinkExternalAccount = async () => {
    if (!unlinkDialog) return;
    setActionLoading(true);
    try {
      await api.unlinkExternalAccount(employeeId, unlinkDialog.id);
      showToast('success', tEmployees('accountUnlinked'));
      setUnlinkDialog(null);
      await fetchExternalAccounts();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : tEmployees('failedToUnlinkAccount'));
    } finally {
      setActionLoading(false);
    }
  };

  // -- Computed values --

  const licenseMonthlyCost = licenses.reduce((sum, l) => sum + (parseFloat(l.monthly_cost || '0') || 0), 0);
  const adminAccountsMonthlyCost = ownedAdminAccounts.reduce((sum, l) => sum + (parseFloat(l.monthly_cost || '0') || 0), 0);
  const totalMonthlyCost = licenseMonthlyCost + adminAccountsMonthlyCost;
  const manualProviders = providers.filter(p => p.config?.provider_type === 'manual' || p.name === 'manual');

  // Get unique provider types that can be linked (non-manual providers)
  const linkableProviderTypes = Array.from(new Set(
    providers
      .filter(p => p.config?.provider_type !== 'manual' && p.name !== 'manual')
      .map(p => p.name)
  ));

  return {
    // Core data
    employee,
    licenses,
    ownedAdminAccounts,
    providers,
    externalAccounts,
    loading,

    // Toast
    toast,
    showToast,

    // Assign License Dialog
    assignDialogOpen,
    setAssignDialogOpen,
    availableLicenses,
    selectedLicenseId,
    setSelectedLicenseId,
    loadingAvailable,
    openAssignDialog,
    handleAssignLicense,

    // Remove Dialog
    removeDialog,
    setRemoveDialog,
    actionLoading,
    handleRemoveFromProvider,

    // Unassign Dialog
    unassignDialog,
    setUnassignDialog,
    handleUnassignLicense,

    // External Accounts
    linkDialogOpen,
    setLinkDialogOpen,
    selectedProviderType,
    setSelectedProviderType,
    externalUsername,
    setExternalUsername,
    unlinkDialog,
    setUnlinkDialog,
    handleLinkExternalAccount,
    handleUnlinkExternalAccount,

    // Computed values
    licenseMonthlyCost,
    adminAccountsMonthlyCost,
    totalMonthlyCost,
    manualProviders,
    linkableProviderTypes,
  };
}
