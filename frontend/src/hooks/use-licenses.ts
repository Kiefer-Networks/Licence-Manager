'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import { api, License, Provider, CategorizedLicensesResponse } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import { isRemovableProvider } from '@/lib/constants';

export type LicenseTab = 'assigned' | 'not_in_hris' | 'unassigned' | 'external';

export interface UseLicensesOptions {
  initialProvider?: string;
  initialTab?: LicenseTab;
}

export interface UseLicensesReturn {
  // Data
  categorizedData: CategorizedLicensesResponse | null;
  providers: Provider[];
  departments: string[];
  filteredLicenses: License[];
  activeLicenses: License[];
  inactiveLicenses: License[];
  licenseProviders: Provider[];

  // Loading states
  loading: boolean;

  // Filters
  search: string;
  setSearch: (value: string) => void;
  debouncedSearch: string;
  selectedProvider: string;
  setSelectedProvider: (value: string) => void;
  selectedDepartment: string;
  setSelectedDepartment: (value: string) => void;
  activeTab: LicenseTab;
  setActiveTab: (tab: LicenseTab) => void;

  // Sorting
  sortColumn: string;
  sortDirection: 'asc' | 'desc';
  handleSort: (column: string) => void;

  // Pagination
  page: number;
  setPage: (page: number) => void;
  pageSize: number;
  totalPages: number;
  paginatedLicenses: License[];
  showSplitTables: boolean;

  // Selection
  selectedIds: Set<string>;
  setSelectedIds: (ids: Set<string>) => void;
  toggleSelect: (id: string) => void;
  toggleSelectAll: () => void;
  selectedLicenses: License[];
  removableLicenses: License[];
  assignedLicenses: License[];
  clearSelection: () => void;

  // Actions
  loadLicenses: () => Promise<void>;
  clearFilters: () => void;

  // Bulk actions
  bulkActionDialog: 'remove' | 'delete' | 'unassign' | null;
  setBulkActionDialog: (dialog: 'remove' | 'delete' | 'unassign' | null) => void;
  bulkActionLoading: boolean;
  handleBulkRemove: () => Promise<void>;
  handleBulkDelete: () => Promise<void>;
  handleBulkUnassign: () => Promise<void>;

  // Toast
  toast: { message: string; type: 'success' | 'error' } | null;
  showToast: (message: string, type: 'success' | 'error') => void;

  // Mark as / Link dialogs
  markAsDialog: { license: License; type: 'service' | 'admin' } | null;
  setMarkAsDialog: (dialog: { license: License; type: 'service' | 'admin' } | null) => void;
  linkDialog: License | null;
  setLinkDialog: (license: License | null) => void;

  // Tab counts
  assignedActiveCount: number;
  notInHrisActiveCount: number;
  unassignedActiveCount: number;
  externalActiveCount: number;
}

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

export function useLicenses(options: UseLicensesOptions = {}): UseLicensesReturn {
  const { initialProvider = 'all', initialTab = 'assigned' } = options;

  // Data state
  const [categorizedData, setCategorizedData] = useState<CategorizedLicensesResponse | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  // Filter state
  const [search, setSearch] = useState('');
  const [selectedProvider, setSelectedProvider] = useState<string>(initialProvider);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<LicenseTab>(initialTab);

  // Sorting state
  const [sortColumn, setSortColumn] = useState<string>('external_user_id');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Pagination state
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const debouncedSearch = useDebounce(search, 300);

  // Derived data
  const licenseProviders = useMemo(
    () => providers.filter((p) => p.name !== 'hibob').sort((a, b) => a.display_name.localeCompare(b.display_name)),
    [providers]
  );

  // Load providers and departments once
  useEffect(() => {
    Promise.all([
      api.getProviders(),
      api.getDepartments(),
    ]).then(([providersData, departmentsData]) => {
      setProviders(providersData.items);
      setDepartments(departmentsData);
    }).catch((e) => handleSilentError('getProviders', e));
  }, []);

  // Load categorized licenses when filters change
  const loadLicenses = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getCategorizedLicenses({
        provider_id: selectedProvider !== 'all' ? selectedProvider : undefined,
        sort_by: sortColumn,
        sort_dir: sortDirection,
      });
      setCategorizedData(data);
      setSelectedIds(new Set());
    } catch (e) {
      handleSilentError('loadLicenses', e);
    } finally {
      setLoading(false);
    }
  }, [selectedProvider, sortColumn, sortDirection]);

  useEffect(() => {
    loadLicenses();
  }, [loadLicenses]);

  // Get licenses for current tab
  const getCurrentTabLicenses = useCallback((): License[] => {
    if (!categorizedData) return [];
    switch (activeTab) {
      case 'assigned':
        return categorizedData.assigned;
      case 'not_in_hris':
        return categorizedData.not_in_hris || [];
      case 'unassigned':
        return categorizedData.unassigned;
      case 'external':
        return categorizedData.external;
    }
  }, [categorizedData, activeTab]);

  // Filter licenses by search and department
  const filteredLicenses = useMemo(() => {
    let licenses = getCurrentTabLicenses();

    if (debouncedSearch) {
      const searchLower = debouncedSearch.toLowerCase();
      licenses = licenses.filter(
        (l) =>
          l.external_user_id.toLowerCase().includes(searchLower) ||
          l.employee_name?.toLowerCase().includes(searchLower) ||
          l.employee_email?.toLowerCase().includes(searchLower) ||
          l.provider_name.toLowerCase().includes(searchLower) ||
          l.license_type?.toLowerCase().includes(searchLower)
      );
    }

    return licenses;
  }, [getCurrentTabLicenses, debouncedSearch]);

  // Split licenses into active and inactive
  const activeLicenses = useMemo(
    () => filteredLicenses.filter(l => l.status === 'active'),
    [filteredLicenses]
  );

  const inactiveLicenses = useMemo(
    () => filteredLicenses.filter(l => l.status !== 'active'),
    [filteredLicenses]
  );

  // Pagination
  const showSplitTables = activeTab === 'not_in_hris' || activeTab === 'unassigned' || activeTab === 'external';
  const totalPages = showSplitTables ? 1 : Math.ceil(filteredLicenses.length / pageSize);
  const paginatedLicenses = showSplitTables
    ? filteredLicenses
    : filteredLicenses.slice((page - 1) * pageSize, page * pageSize);

  // Selection handlers
  const toggleSelectAll = useCallback(() => {
    if (selectedIds.size === paginatedLicenses.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(paginatedLicenses.map(l => l.id)));
    }
  }, [selectedIds.size, paginatedLicenses]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // Selected licenses info
  const selectedLicenses = useMemo(
    () => paginatedLicenses.filter(l => selectedIds.has(l.id)),
    [paginatedLicenses, selectedIds]
  );

  const removableLicenses = useMemo(
    () => selectedLicenses.filter(l => {
      const provider = providers.find(p => p.id === l.provider_id);
      return provider && isRemovableProvider(provider.name);
    }),
    [selectedLicenses, providers]
  );

  const assignedLicenses = useMemo(
    () => selectedLicenses.filter(l => l.employee_id),
    [selectedLicenses]
  );

  // Sort handler
  const handleSort = useCallback((column: string) => {
    if (sortColumn === column) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  }, [sortColumn]);

  // Clear filters
  const clearFilters = useCallback(() => {
    setSelectedProvider('all');
    setSelectedDepartment('all');
  }, []);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [activeTab, debouncedSearch, selectedDepartment]);

  // Tab counts
  const assignedActiveCount = categorizedData?.assigned.filter(l => l.status === 'active').length || 0;
  const notInHrisActiveCount = categorizedData?.not_in_hris?.filter(l => l.status === 'active').length || 0;
  const unassignedActiveCount = categorizedData?.unassigned.filter(l => l.status === 'active').length || 0;
  const externalActiveCount = categorizedData?.external.filter(l => l.status === 'active').length || 0;

  // Bulk action dialog state
  const [bulkActionDialog, setBulkActionDialog] = useState<'remove' | 'delete' | 'unassign' | null>(null);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);

  // Toast state
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Mark as dialog state
  const [markAsDialog, setMarkAsDialog] = useState<{ license: License; type: 'service' | 'admin' } | null>(null);

  // Link dialog state
  const [linkDialog, setLinkDialog] = useState<License | null>(null);

  // Toast handler
  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }, []);

  // Bulk action handlers
  const handleBulkRemove = useCallback(async () => {
    if (removableLicenses.length === 0) return;
    setBulkActionLoading(true);
    try {
      const result = await api.bulkRemoveFromProvider(removableLicenses.map(l => l.id));
      showToast(`Bulk removed: ${result.successful}/${result.total}`, result.failed > 0 ? 'error' : 'success');
      setBulkActionDialog(null);
      loadLicenses();
    } catch {
      showToast('Failed to remove licenses', 'error');
    } finally {
      setBulkActionLoading(false);
    }
  }, [removableLicenses, showToast, loadLicenses]);

  const handleBulkDelete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    setBulkActionLoading(true);
    try {
      const result = await api.bulkDeleteLicenses(Array.from(selectedIds));
      showToast(`Bulk deleted: ${result.successful}/${result.total}`, result.failed > 0 ? 'error' : 'success');
      setBulkActionDialog(null);
      loadLicenses();
    } catch {
      showToast('Failed to delete licenses', 'error');
    } finally {
      setBulkActionLoading(false);
    }
  }, [selectedIds, showToast, loadLicenses]);

  const handleBulkUnassign = useCallback(async () => {
    if (assignedLicenses.length === 0) return;
    setBulkActionLoading(true);
    try {
      const result = await api.bulkUnassignLicenses(assignedLicenses.map(l => l.id));
      showToast(`Bulk unassigned: ${result.successful}/${result.total}`, result.failed > 0 ? 'error' : 'success');
      setBulkActionDialog(null);
      loadLicenses();
    } catch {
      showToast('Failed to unassign licenses', 'error');
    } finally {
      setBulkActionLoading(false);
    }
  }, [assignedLicenses, showToast, loadLicenses]);

  return {
    // Data
    categorizedData,
    providers,
    departments,
    filteredLicenses,
    activeLicenses,
    inactiveLicenses,
    licenseProviders,

    // Loading states
    loading,

    // Filters
    search,
    setSearch,
    debouncedSearch,
    selectedProvider,
    setSelectedProvider,
    selectedDepartment,
    setSelectedDepartment,
    activeTab,
    setActiveTab,

    // Sorting
    sortColumn,
    sortDirection,
    handleSort,

    // Pagination
    page,
    setPage,
    pageSize,
    totalPages,
    paginatedLicenses,
    showSplitTables,

    // Selection
    selectedIds,
    setSelectedIds,
    toggleSelect,
    toggleSelectAll,
    selectedLicenses,
    removableLicenses,
    assignedLicenses,
    clearSelection,

    // Actions
    loadLicenses,
    clearFilters,

    // Bulk actions
    bulkActionDialog,
    setBulkActionDialog,
    bulkActionLoading,
    handleBulkRemove,
    handleBulkDelete,
    handleBulkUnassign,

    // Toast
    toast,
    showToast,

    // Mark as / Link dialogs
    markAsDialog,
    setMarkAsDialog,
    linkDialog,
    setLinkDialog,

    // Tab counts
    assignedActiveCount,
    notInHrisActiveCount,
    unassignedActiveCount,
    externalActiveCount,
  };
}
