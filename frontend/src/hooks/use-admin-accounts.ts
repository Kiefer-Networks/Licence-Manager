'use client';

import { useState, useEffect } from 'react';
import {
  api,
  AdminAccountPattern,
  License,
  Provider,
  Employee,
} from '@/lib/api';

/**
 * Type for grouped admin accounts.
 */
export interface GroupedAdminAccount {
  email: string;
  name: string | null;
  owner_id: string | null;
  owner_name: string | null;
  owner_status: string | null;
  licenses: License[];
  providers: { id: string; name: string; status: string }[];
  hasGlobalPattern: boolean;
  hasSuspended: boolean;
  activeCount: number;
  suspendedCount: number;
}

/**
 * Summary statistics for admin accounts.
 */
export interface AdminAccountsSummaryStats {
  uniqueAdmins: number;
  totalLicenses: number;
  uniqueProviders: number;
  suspendedLicenses: number;
  adminsWithSuspended: number;
}

/**
 * Return type for the useAdminAccounts hook.
 */
export interface UseAdminAccountsReturn {
  // Patterns
  patterns: AdminAccountPattern[];
  loadingPatterns: boolean;
  showAddPattern: boolean;
  setShowAddPattern: (show: boolean) => void;
  newPattern: { email_pattern: string; name: string; notes: string };
  setNewPattern: (pattern: { email_pattern: string; name: string; notes: string }) => void;
  creatingPattern: boolean;
  deletingPatternId: string | null;
  applyingPatterns: boolean;
  handleCreatePattern: () => Promise<void>;
  handleDeletePattern: (patternId: string) => Promise<void>;
  handleApplyPatterns: () => Promise<void>;

  // Make Global
  makeGlobalLicense: License | null;
  setMakeGlobalLicense: (license: License | null) => void;
  makingGlobal: boolean;
  handleMakeGlobal: () => Promise<void>;

  // Pattern Matches Dialog
  matchesDialog: AdminAccountPattern | null;
  setMatchesDialog: (pattern: AdminAccountPattern | null) => void;
  matchesLicenses: License[];
  loadingMatches: boolean;
  handleShowMatches: (pattern: AdminAccountPattern) => Promise<void>;

  // Edit Owner Dialog
  editOwnerAccount: GroupedAdminAccount | null;
  setEditOwnerAccount: (account: GroupedAdminAccount | null) => void;
  selectedOwnerId: string;
  setSelectedOwnerId: (id: string) => void;
  ownerSearchQuery: string;
  setOwnerSearchQuery: (query: string) => void;
  showOwnerResults: boolean;
  setShowOwnerResults: (show: boolean) => void;
  savingOwner: boolean;
  handleOpenEditOwner: (account: GroupedAdminAccount) => void;
  handleSelectOwner: (emp: Employee) => void;
  handleClearOwner: () => void;
  handleSaveOwner: () => Promise<void>;

  // Licenses
  licenses: License[];
  loadingLicenses: boolean;
  licensesTotal: number;
  licensesPage: number;
  setLicensesPage: (page: number) => void;
  licensesSearch: string;
  setLicensesSearch: (search: string) => void;
  licensesProviderId: string;
  setLicensesProviderId: (id: string) => void;
  licensesSortColumn: string;
  licensesSortDir: 'asc' | 'desc';
  handleLicenseSort: (column: string) => void;

  // Employees
  employees: Employee[];
  loadingEmployees: boolean;

  // Computed values
  licensesPageSize: number;
  licensesTotalPages: number;
  groupedAccounts: GroupedAdminAccount[];
  summaryStats: AdminAccountsSummaryStats;
}

/**
 * Custom hook that encapsulates all business logic for the AdminAccountsTab component.
 * Manages admin account patterns, licenses, owner assignments, and related actions.
 */
export function useAdminAccounts(
  providers: Provider[],
  showToast: (type: 'success' | 'error' | 'info', text: string) => void,
  t: (key: string, params?: Record<string, string | number>) => string,
  tCommon: (key: string) => string,
  tLicenses: (key: string, params?: Record<string, string | number>) => string,
): UseAdminAccountsReturn {
  // Patterns state
  const [patterns, setPatterns] = useState<AdminAccountPattern[]>([]);
  const [loadingPatterns, setLoadingPatterns] = useState(true);
  const [showAddPattern, setShowAddPattern] = useState(false);
  const [newPattern, setNewPattern] = useState({
    email_pattern: '',
    name: '',
    notes: '',
  });
  const [creatingPattern, setCreatingPattern] = useState(false);
  const [deletingPatternId, setDeletingPatternId] = useState<string | null>(null);
  const [applyingPatterns, setApplyingPatterns] = useState(false);
  const [makeGlobalLicense, setMakeGlobalLicense] = useState<License | null>(null);
  const [makingGlobal, setMakingGlobal] = useState(false);

  // Pattern matches dialog state
  const [matchesDialog, setMatchesDialog] = useState<AdminAccountPattern | null>(null);
  const [matchesLicenses, setMatchesLicenses] = useState<License[]>([]);
  const [loadingMatches, setLoadingMatches] = useState(false);

  // Edit owner dialog state
  const [editOwnerAccount, setEditOwnerAccount] = useState<GroupedAdminAccount | null>(null);
  const [selectedOwnerId, setSelectedOwnerId] = useState<string>('');
  const [ownerSearchQuery, setOwnerSearchQuery] = useState<string>('');
  const [showOwnerResults, setShowOwnerResults] = useState(false);
  const [savingOwner, setSavingOwner] = useState(false);

  // Admin Account Licenses state
  const [licenses, setLicenses] = useState<License[]>([]);
  const [loadingLicenses, setLoadingLicenses] = useState(true);
  const [licensesTotal, setLicensesTotal] = useState(0);
  const [licensesPage, setLicensesPage] = useState(1);
  const [licensesSearch, setLicensesSearch] = useState('');
  const [licensesProviderId, setLicensesProviderId] = useState<string>('all');
  const [licensesSortColumn, setLicensesSortColumn] = useState<string>('external_user_id');
  const [licensesSortDir, setLicensesSortDir] = useState<'asc' | 'desc'>('asc');

  // Employees for owner selection
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loadingEmployees, setLoadingEmployees] = useState(false);

  // -- Data loading --

  // Load patterns
  useEffect(() => {
    loadPatterns();
  }, []);

  // Load admin account licenses
  useEffect(() => {
    loadLicenses();
  }, [licensesPage, licensesSearch, licensesProviderId, licensesSortColumn, licensesSortDir]);

  const loadPatterns = async () => {
    setLoadingPatterns(true);
    try {
      const response = await api.getAdminAccountPatterns();
      setPatterns(response.items);
    } catch (error) {
      showToast('error', t('failedToLoadPatterns'));
    } finally {
      setLoadingPatterns(false);
    }
  };

  const loadLicenses = async () => {
    setLoadingLicenses(true);
    try {
      const response = await api.getAdminAccountLicenses({
        page: licensesPage,
        page_size: 50,
        search: licensesSearch || undefined,
        provider_id: licensesProviderId !== 'all' ? licensesProviderId : undefined,
        sort_by: licensesSortColumn,
        sort_dir: licensesSortDir,
      });
      setLicenses(response.items);
      setLicensesTotal(response.total);
    } catch (error) {
      showToast('error', t('failedToLoadLicenses'));
    } finally {
      setLoadingLicenses(false);
    }
  };

  const loadEmployees = async (search?: string) => {
    setLoadingEmployees(true);
    try {
      const response = await api.getEmployees({
        page_size: 50,
        status: 'active',
        search: search || undefined,
      });
      setEmployees(response.items);
    } catch (error) {
      // Silent fail for employee loading
    } finally {
      setLoadingEmployees(false);
    }
  };

  // Debounce employee search
  useEffect(() => {
    if (!editOwnerAccount) return;

    const timer = setTimeout(() => {
      loadEmployees(ownerSearchQuery.trim() || undefined);
    }, 300);

    return () => clearTimeout(timer);
  }, [ownerSearchQuery, editOwnerAccount]);

  // -- Handlers --

  const handleShowMatches = async (pattern: AdminAccountPattern) => {
    setMatchesDialog(pattern);
    setLoadingMatches(true);
    setMatchesLicenses([]);
    try {
      // Use the pattern as search query to find matching licenses
      const response = await api.getAdminAccountLicenses({
        search: pattern.email_pattern.replace('*', ''),  // Remove wildcard for search
        page_size: 200,
      });
      // Filter client-side to get exact matches for this pattern
      const patternRegex = new RegExp(
        '^' + pattern.email_pattern.replace(/\*/g, '.*').replace(/\?/g, '.') + '$',
        'i'
      );
      const filtered = response.items.filter(license =>
        patternRegex.test(license.external_user_id)
      );
      setMatchesLicenses(filtered);
    } catch (error) {
      showToast('error', t('failedToLoadMatching'));
    } finally {
      setLoadingMatches(false);
    }
  };

  const handleCreatePattern = async () => {
    if (!newPattern.email_pattern.trim()) {
      showToast('error', t('emailPatternRequired'));
      return;
    }

    setCreatingPattern(true);
    try {
      await api.createAdminAccountPattern({
        email_pattern: newPattern.email_pattern.trim(),
        name: newPattern.name.trim() || undefined,
        notes: newPattern.notes.trim() || undefined,
      });
      showToast('success', t('patternCreated'));
      setShowAddPattern(false);
      setNewPattern({ email_pattern: '', name: '', notes: '' });
      loadPatterns();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToCreatePattern'));
    } finally {
      setCreatingPattern(false);
    }
  };

  const handleDeletePattern = async (patternId: string) => {
    setDeletingPatternId(patternId);
    try {
      await api.deleteAdminAccountPattern(patternId);
      showToast('success', t('patternDeleted'));
      loadPatterns();
    } catch (error) {
      showToast('error', t('failedToDeletePattern'));
    } finally {
      setDeletingPatternId(null);
    }
  };

  const handleApplyPatterns = async () => {
    setApplyingPatterns(true);
    try {
      const result = await api.applyAdminAccountPatterns();
      if (result.updated_count > 0) {
        showToast('success', t('patternsApplied', { count: result.updated_count }));
        loadLicenses();
        loadPatterns();
      } else {
        showToast('info', t('noNewMatches'));
      }
    } catch (error) {
      showToast('error', t('failedToApply'));
    } finally {
      setApplyingPatterns(false);
    }
  };

  const handleLicenseSort = (column: string) => {
    if (licensesSortColumn === column) {
      setLicensesSortDir(licensesSortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setLicensesSortColumn(column);
      setLicensesSortDir('asc');
    }
  };

  // Check if email already has a global pattern
  const isEmailGlobal = (email: string): boolean => {
    return patterns.some((p) => {
      if (p.email_pattern === email) return true;
      // Check wildcard pattern match
      if (p.email_pattern.includes('*')) {
        const regex = new RegExp('^' + p.email_pattern.replace(/\*/g, '.*') + '$', 'i');
        return regex.test(email);
      }
      return false;
    });
  };

  const handleMakeGlobal = async () => {
    if (!makeGlobalLicense) return;

    setMakingGlobal(true);
    try {
      await api.createAdminAccountPattern({
        email_pattern: makeGlobalLicense.external_user_id,
        name: makeGlobalLicense.admin_account_name || undefined,
      });
      showToast('success', t('patternCreated'));
      setMakeGlobalLicense(null);
      loadPatterns();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToCreatePattern'));
    } finally {
      setMakingGlobal(false);
    }
  };

  const handleOpenEditOwner = (account: GroupedAdminAccount) => {
    setEditOwnerAccount(account);
    setSelectedOwnerId(account.owner_id || '');
    setOwnerSearchQuery(account.owner_name || '');
    setShowOwnerResults(false);
    // Load initial employees
    loadEmployees(account.owner_name || undefined);
  };

  const handleSelectOwner = (emp: Employee) => {
    setSelectedOwnerId(emp.id);
    setOwnerSearchQuery(emp.full_name);
    setShowOwnerResults(false);
  };

  const handleClearOwner = () => {
    setSelectedOwnerId('');
    setOwnerSearchQuery('');
    setShowOwnerResults(false);
  };

  const handleSaveOwner = async () => {
    if (!editOwnerAccount) return;

    setSavingOwner(true);
    try {
      // Update all licenses for this admin account
      for (const license of editOwnerAccount.licenses) {
        await api.updateLicenseAdminAccount(license.id, {
          is_admin_account: true,
          admin_account_name: editOwnerAccount.name || undefined,
          admin_account_owner_id: selectedOwnerId || undefined,
        });
      }
      showToast('success', t('ownerUpdated'));
      setEditOwnerAccount(null);
      loadLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUpdateOwner'));
    } finally {
      setSavingOwner(false);
    }
  };

  // -- Computed values --

  const licensesPageSize = 50;
  const licensesTotalPages = Math.ceil(licensesTotal / licensesPageSize);

  // Group licenses by email
  const groupedAccounts: GroupedAdminAccount[] = (() => {
    const grouped = new Map<string, GroupedAdminAccount>();

    for (const license of licenses) {
      const email = license.external_user_id;
      const existing = grouped.get(email);

      if (existing) {
        existing.licenses.push(license);
        existing.providers.push({
          id: license.provider_id,
          name: license.provider_name,
          status: license.status,
        });
        if (license.status === 'suspended' || license.status === 'inactive') {
          existing.hasSuspended = true;
          existing.suspendedCount++;
        } else if (license.status === 'active') {
          existing.activeCount++;
        }
      } else {
        grouped.set(email, {
          email,
          name: license.admin_account_name || null,
          owner_id: license.admin_account_owner_id || null,
          owner_name: license.admin_account_owner_name || null,
          owner_status: license.admin_account_owner_status || null,
          licenses: [license],
          providers: [{
            id: license.provider_id,
            name: license.provider_name,
            status: license.status,
          }],
          hasGlobalPattern: isEmailGlobal(email),
          hasSuspended: license.status === 'suspended' || license.status === 'inactive',
          activeCount: license.status === 'active' ? 1 : 0,
          suspendedCount: (license.status === 'suspended' || license.status === 'inactive') ? 1 : 0,
        });
      }
    }

    return Array.from(grouped.values());
  })();

  // Calculate summary statistics
  const summaryStats: AdminAccountsSummaryStats = {
    uniqueAdmins: groupedAccounts.length,
    totalLicenses: licenses.length,
    uniqueProviders: new Set(licenses.map(l => l.provider_id)).size,
    suspendedLicenses: licenses.filter(l => l.status === 'suspended' || l.status === 'inactive').length,
    adminsWithSuspended: groupedAccounts.filter(a => a.hasSuspended).length,
  };

  return {
    // Patterns
    patterns,
    loadingPatterns,
    showAddPattern,
    setShowAddPattern,
    newPattern,
    setNewPattern,
    creatingPattern,
    deletingPatternId,
    applyingPatterns,
    handleCreatePattern,
    handleDeletePattern,
    handleApplyPatterns,

    // Make Global
    makeGlobalLicense,
    setMakeGlobalLicense,
    makingGlobal,
    handleMakeGlobal,

    // Pattern Matches Dialog
    matchesDialog,
    setMatchesDialog,
    matchesLicenses,
    loadingMatches,
    handleShowMatches,

    // Edit Owner Dialog
    editOwnerAccount,
    setEditOwnerAccount,
    selectedOwnerId,
    setSelectedOwnerId,
    ownerSearchQuery,
    setOwnerSearchQuery,
    showOwnerResults,
    setShowOwnerResults,
    savingOwner,
    handleOpenEditOwner,
    handleSelectOwner,
    handleClearOwner,
    handleSaveOwner,

    // Licenses
    licenses,
    loadingLicenses,
    licensesTotal,
    licensesPage,
    setLicensesPage,
    licensesSearch,
    setLicensesSearch,
    licensesProviderId,
    setLicensesProviderId,
    licensesSortColumn,
    licensesSortDir,
    handleLicenseSort,

    // Employees
    employees,
    loadingEmployees,

    // Computed values
    licensesPageSize,
    licensesTotalPages,
    groupedAccounts,
    summaryStats,
  };
}
