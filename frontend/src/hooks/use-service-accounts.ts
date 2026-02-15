'use client';

import { useState, useEffect } from 'react';
import {
  api,
  ServiceAccountPattern,
  ServiceAccountLicenseType,
  License,
  Provider,
  Employee,
} from '@/lib/api';

/**
 * Return type for the useServiceAccounts hook.
 */
export interface UseServiceAccountsReturn {
  // Patterns
  patterns: ServiceAccountPattern[];
  loadingPatterns: boolean;
  showAddPattern: boolean;
  setShowAddPattern: (show: boolean) => void;
  newPattern: { email_pattern: string; name: string; owner_id: string; notes: string };
  setNewPattern: (pattern: { email_pattern: string; name: string; owner_id: string; notes: string }) => void;
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
  matchesDialog: ServiceAccountPattern | null;
  setMatchesDialog: (pattern: ServiceAccountPattern | null) => void;
  matchesLicenses: License[];
  loadingMatches: boolean;
  handleShowMatches: (pattern: ServiceAccountPattern) => Promise<void>;

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

  // License Types
  licenseTypes: ServiceAccountLicenseType[];
  loadingLicenseTypes: boolean;
  showAddLicenseType: boolean;
  setShowAddLicenseType: (show: boolean) => void;
  newLicenseType: { license_type: string; name: string; owner_id: string; notes: string };
  setNewLicenseType: (lt: { license_type: string; name: string; owner_id: string; notes: string }) => void;
  creatingLicenseType: boolean;
  deletingLicenseTypeId: string | null;
  applyingLicenseTypes: boolean;
  handleCreateLicenseType: () => Promise<void>;
  handleDeleteLicenseType: (entryId: string) => Promise<void>;
  handleApplyLicenseTypes: () => Promise<void>;

  // Computed values
  licensesPageSize: number;
  licensesTotalPages: number;
  isEmailGlobal: (email: string) => boolean;
}

/**
 * Custom hook that encapsulates all business logic for the ServiceAccountsTab component.
 * Manages service account patterns, license types, licenses, and related actions.
 */
export function useServiceAccounts(
  providers: Provider[],
  showToast: (type: 'success' | 'error' | 'info', text: string) => void,
  t: (key: string, params?: Record<string, string | number>) => string,
  tCommon: (key: string) => string,
  tLicenses: (key: string, params?: Record<string, string | number>) => string,
): UseServiceAccountsReturn {
  // Patterns state
  const [patterns, setPatterns] = useState<ServiceAccountPattern[]>([]);
  const [loadingPatterns, setLoadingPatterns] = useState(true);
  const [showAddPattern, setShowAddPattern] = useState(false);
  const [newPattern, setNewPattern] = useState({
    email_pattern: '',
    name: '',
    owner_id: '',
    notes: '',
  });
  const [creatingPattern, setCreatingPattern] = useState(false);
  const [deletingPatternId, setDeletingPatternId] = useState<string | null>(null);
  const [applyingPatterns, setApplyingPatterns] = useState(false);
  const [makeGlobalLicense, setMakeGlobalLicense] = useState<License | null>(null);
  const [makingGlobal, setMakingGlobal] = useState(false);

  // Pattern matches dialog state
  const [matchesDialog, setMatchesDialog] = useState<ServiceAccountPattern | null>(null);
  const [matchesLicenses, setMatchesLicenses] = useState<License[]>([]);
  const [loadingMatches, setLoadingMatches] = useState(false);

  // Service Account Licenses state
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

  // License Types state
  const [licenseTypes, setLicenseTypes] = useState<ServiceAccountLicenseType[]>([]);
  const [loadingLicenseTypes, setLoadingLicenseTypes] = useState(true);
  const [showAddLicenseType, setShowAddLicenseType] = useState(false);
  const [newLicenseType, setNewLicenseType] = useState({
    license_type: '',
    name: '',
    owner_id: '',
    notes: '',
  });
  const [creatingLicenseType, setCreatingLicenseType] = useState(false);
  const [deletingLicenseTypeId, setDeletingLicenseTypeId] = useState<string | null>(null);
  const [applyingLicenseTypes, setApplyingLicenseTypes] = useState(false);

  // -- Data loading --

  // Load patterns and license types
  useEffect(() => {
    loadPatterns();
    loadLicenseTypes();
    loadEmployees();
  }, []);

  // Load service account licenses
  useEffect(() => {
    loadLicenses();
  }, [licensesPage, licensesSearch, licensesProviderId, licensesSortColumn, licensesSortDir]);

  const loadPatterns = async () => {
    setLoadingPatterns(true);
    try {
      const response = await api.getServiceAccountPatterns();
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
      const response = await api.getServiceAccountLicenses({
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

  const loadEmployees = async () => {
    try {
      const response = await api.getEmployees({ page_size: 200, status: 'active' });
      setEmployees(response.items);
    } catch (error) {
      // Silent fail for employee loading
    }
  };

  const loadLicenseTypes = async () => {
    setLoadingLicenseTypes(true);
    try {
      const response = await api.getServiceAccountLicenseTypes();
      setLicenseTypes(response.items);
    } catch (error) {
      showToast('error', t('failedToLoadLicenseTypes'));
    } finally {
      setLoadingLicenseTypes(false);
    }
  };

  // -- Handlers --

  const handleCreateLicenseType = async () => {
    if (!newLicenseType.license_type.trim()) {
      showToast('error', t('licenseTypeRequired'));
      return;
    }

    setCreatingLicenseType(true);
    try {
      await api.createServiceAccountLicenseType({
        license_type: newLicenseType.license_type.trim(),
        name: newLicenseType.name.trim() || undefined,
        owner_id: newLicenseType.owner_id || undefined,
        notes: newLicenseType.notes.trim() || undefined,
      });
      showToast('success', t('licenseTypeCreated'));
      setShowAddLicenseType(false);
      setNewLicenseType({ license_type: '', name: '', owner_id: '', notes: '' });
      loadLicenseTypes();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToCreateLicenseType'));
    } finally {
      setCreatingLicenseType(false);
    }
  };

  const handleDeleteLicenseType = async (entryId: string) => {
    setDeletingLicenseTypeId(entryId);
    try {
      await api.deleteServiceAccountLicenseType(entryId);
      showToast('success', t('licenseTypeDeleted'));
      loadLicenseTypes();
    } catch (error) {
      showToast('error', t('failedToDeleteLicenseType'));
    } finally {
      setDeletingLicenseTypeId(null);
    }
  };

  const handleApplyLicenseTypes = async () => {
    setApplyingLicenseTypes(true);
    try {
      const result = await api.applyServiceAccountLicenseTypes();
      if (result.updated_count > 0) {
        showToast('success', t('licenseTypesApplied', { count: result.updated_count }));
        loadLicenses();
        loadLicenseTypes();
      } else {
        showToast('info', t('noLicenseTypeMatches'));
      }
    } catch (error) {
      showToast('error', t('failedToApplyLicenseTypes'));
    } finally {
      setApplyingLicenseTypes(false);
    }
  };

  const handleShowMatches = async (pattern: ServiceAccountPattern) => {
    setMatchesDialog(pattern);
    setLoadingMatches(true);
    setMatchesLicenses([]);
    try {
      // Use the pattern as search query to find matching licenses
      const response = await api.getServiceAccountLicenses({
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
      await api.createServiceAccountPattern({
        email_pattern: newPattern.email_pattern.trim(),
        name: newPattern.name.trim() || undefined,
        owner_id: newPattern.owner_id || undefined,
        notes: newPattern.notes.trim() || undefined,
      });
      showToast('success', t('patternCreated'));
      setShowAddPattern(false);
      setNewPattern({ email_pattern: '', name: '', owner_id: '', notes: '' });
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
      await api.deleteServiceAccountPattern(patternId);
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
      const result = await api.applyServiceAccountPatterns();
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
      await api.createServiceAccountPattern({
        email_pattern: makeGlobalLicense.external_user_id,
        name: makeGlobalLicense.service_account_name || undefined,
        owner_id: makeGlobalLicense.service_account_owner_id || undefined,
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

  // -- Computed values --

  const licensesPageSize = 50;
  const licensesTotalPages = Math.ceil(licensesTotal / licensesPageSize);

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

    // License Types
    licenseTypes,
    loadingLicenseTypes,
    showAddLicenseType,
    setShowAddLicenseType,
    newLicenseType,
    setNewLicenseType,
    creatingLicenseType,
    deletingLicenseTypeId,
    applyingLicenseTypes,
    handleCreateLicenseType,
    handleDeleteLicenseType,
    handleApplyLicenseTypes,

    // Computed values
    licensesPageSize,
    licensesTotalPages,
    isEmailGlobal,
  };
}
