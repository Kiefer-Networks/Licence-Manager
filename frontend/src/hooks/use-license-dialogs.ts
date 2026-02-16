'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, License, Employee, EmployeeSuggestion } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';

// ==================== useMarkAsAccountDialog ====================

export interface UseMarkAsAccountDialogReturn {
  name: string;
  setName: (name: string) => void;
  ownerId: string;
  ownerQuery: string;
  setOwnerQuery: (query: string) => void;
  loading: boolean;
  showOwnerResults: boolean;
  setShowOwnerResults: (show: boolean) => void;
  employees: Employee[];
  loadingEmployees: boolean;
  handleSelectOwner: (emp: Employee) => void;
  handleClearOwner: () => void;
  handleSubmit: () => Promise<void>;
  setOwnerId: (id: string) => void;
}

export function useMarkAsAccountDialog(
  open: boolean,
  license: License | null,
  type: 'service' | 'admin',
  onSuccess: () => void,
  onToast: (message: string, type: 'success' | 'error') => void,
  onOpenChange: (open: boolean) => void,
  tServiceAccounts: (key: string) => string,
  tAdminAccounts: (key: string) => string,
  tLicenses: (key: string) => string,
): UseMarkAsAccountDialogReturn {
  const [name, setName] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [ownerQuery, setOwnerQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [showOwnerResults, setShowOwnerResults] = useState(false);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loadingEmployees, setLoadingEmployees] = useState(false);

  const loadEmployees = useCallback(async (search?: string) => {
    setLoadingEmployees(true);
    try {
      const response = await api.getEmployees({
        page_size: 50,
        status: 'active',
        search: search || undefined,
      });
      setEmployees(response.items);
    } catch (error) {
      handleSilentError('loadEmployees', error);
    } finally {
      setLoadingEmployees(false);
    }
  }, []);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setName('');
      setOwnerId('');
      setOwnerQuery('');
      setShowOwnerResults(false);
      loadEmployees();
    }
  }, [open, loadEmployees]);

  // Debounce employee search
  useEffect(() => {
    if (!open) return;

    const timer = setTimeout(() => {
      loadEmployees(ownerQuery.trim() || undefined);
    }, 300);

    return () => clearTimeout(timer);
  }, [ownerQuery, open, loadEmployees]);

  const handleSelectOwner = (emp: Employee) => {
    setOwnerId(emp.id);
    setOwnerQuery(emp.full_name);
    setShowOwnerResults(false);
  };

  const handleClearOwner = () => {
    setOwnerId('');
    setOwnerQuery('');
    setShowOwnerResults(false);
  };

  const handleSubmit = async () => {
    if (!license) return;

    setLoading(true);
    try {
      if (type === 'service') {
        await api.updateLicenseServiceAccount(license.id, {
          is_service_account: true,
          service_account_name: name || undefined,
          service_account_owner_id: ownerId || undefined,
        });
        onToast(tServiceAccounts('markedAsServiceAccount'), 'success');
      } else {
        await api.updateLicenseAdminAccount(license.id, {
          is_admin_account: true,
          admin_account_name: name || undefined,
          admin_account_owner_id: ownerId || undefined,
        });
        onToast(tAdminAccounts('markedAsAdminAccount'), 'success');
      }
      onOpenChange(false);
      onSuccess();
    } catch {
      onToast(tLicenses('failedToUpdate'), 'error');
    } finally {
      setLoading(false);
    }
  };

  return {
    name,
    setName,
    ownerId,
    ownerQuery,
    setOwnerQuery,
    loading,
    showOwnerResults,
    setShowOwnerResults,
    employees,
    loadingEmployees,
    handleSelectOwner,
    handleClearOwner,
    handleSubmit,
    setOwnerId,
  };
}

// ==================== useLinkToEmployeeDialog ====================

export interface UseLinkToEmployeeDialogReturn {
  suggestions: EmployeeSuggestion[];
  loadingSuggestions: boolean;
  linkLoading: boolean;
  handleLinkToEmployee: (employeeId: string) => Promise<void>;
}

export function useLinkToEmployeeDialog(
  open: boolean,
  license: License | null,
  onSuccess: () => void,
  onToast: (message: string, type: 'success' | 'error') => void,
  onOpenChange: (open: boolean) => void,
  tLicenses: (key: string) => string,
): UseLinkToEmployeeDialogReturn {
  const [suggestions, setSuggestions] = useState<EmployeeSuggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [linkLoading, setLinkLoading] = useState(false);

  // Fetch suggestions when dialog opens
  useEffect(() => {
    if (!open || !license) return;

    const fetchSuggestions = async () => {
      setSuggestions([]);
      setLoadingSuggestions(true);

      try {
        const metadata = license.metadata as Record<string, unknown> | undefined;
        const username = (metadata?.username as string) || (metadata?.hf_username as string) || license.external_user_id;
        const displayName = (metadata?.fullname as string) || (metadata?.display_name as string);
        const providerName = license.provider_name;

        const response = await api.getEmployeeSuggestions(providerName, username, displayName);
        setSuggestions(response.suggestions);
      } catch (error) {
        handleSilentError('getEmployeeSuggestions', error);
      } finally {
        setLoadingSuggestions(false);
      }
    };

    fetchSuggestions();
  }, [open, license]);

  const handleLinkToEmployee = async (employeeId: string) => {
    if (!license) return;

    setLinkLoading(true);
    try {
      const metadata = license.metadata as Record<string, unknown> | undefined;
      const username = (metadata?.username as string) || (metadata?.hf_username as string) || license.external_user_id;
      const displayName = (metadata?.fullname as string) || (metadata?.display_name as string);

      await api.linkExternalAccount(employeeId, {
        provider_type: license.provider_name,
        external_username: username,
        display_name: displayName,
      });

      onToast(tLicenses('linkedToEmployee'), 'success');
      onOpenChange(false);
      onSuccess();
    } catch {
      onToast(tLicenses('failedToLink'), 'error');
    } finally {
      setLinkLoading(false);
    }
  };

  return {
    suggestions,
    loadingSuggestions,
    linkLoading,
    handleLinkToEmployee,
  };
}
