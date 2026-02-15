'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth, Permissions } from '@/components/auth-provider';
import { api, AuditLogEntry } from '@/lib/api';
import { useDebounce } from '@/hooks/use-debounce';
import { DatePreset } from '@/app/admin/audit/components/DateRangePicker';

/**
 * Translation functions required by the useAuditLog hook.
 */
interface AuditLogTranslations {
  t: (key: string) => string;
}

/**
 * Return type for the useAuditLog hook.
 */
export interface UseAuditLogReturn {
  // Data
  logs: AuditLogEntry[];
  isLoading: boolean;
  error: string;
  total: number;
  authLoading: boolean;

  // Pagination
  page: number;
  setPage: (page: number | ((prev: number) => number)) => void;
  totalPages: number;

  // Search
  searchInput: string;
  setSearchInput: (value: string) => void;

  // Date filters
  datePreset: DatePreset;
  dateFrom: string;
  dateTo: string;
  setDateFrom: (value: string) => void;
  setDateTo: (value: string) => void;
  handleDatePresetChange: (preset: DatePreset) => void;

  // Filters
  actionFilter: string;
  setActionFilter: (value: string) => void;
  resourceTypeFilter: string;
  setResourceTypeFilter: (value: string) => void;
  userFilter: string;
  setUserFilter: (value: string) => void;

  // Filter options
  availableActions: string[];
  availableResourceTypes: string[];
  availableUsers: Array<{ id: string; email: string }>;

  // Detail dialog
  selectedLog: AuditLogEntry | null;
  detailDialogOpen: boolean;
  setDetailDialogOpen: (open: boolean) => void;

  // Export
  isExporting: boolean;
  exportDialogOpen: boolean;
  setExportDialogOpen: (open: boolean) => void;

  // Handlers
  loadLogs: () => Promise<void>;
  handleViewDetails: (log: AuditLogEntry) => void;
  handleClearFilters: () => void;
  handleExport: (limit: number, format: 'csv' | 'json') => Promise<void>;
}

// Date helper functions
function getDateFromPreset(preset: DatePreset): { from: string; to: string } {
  const now = new Date();
  const today = now.toISOString().split('T')[0];

  switch (preset) {
    case 'today': {
      return { from: today, to: today };
    }
    case 'last7Days': {
      const from = new Date(now);
      from.setDate(from.getDate() - 7);
      return { from: from.toISOString().split('T')[0], to: today };
    }
    case 'last30Days': {
      const from = new Date(now);
      from.setDate(from.getDate() - 30);
      return { from: from.toISOString().split('T')[0], to: today };
    }
    default:
      return { from: '', to: '' };
  }
}

/**
 * Custom hook that encapsulates all business logic for the Audit Log page.
 * Manages audit log data, filters, pagination, detail view, and export.
 */
export function useAuditLog(
  { t }: AuditLogTranslations,
): UseAuditLogReturn {
  const router = useRouter();
  const { hasPermission, isLoading: authLoading } = useAuth();

  // Data state
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 25;

  // Search state
  const [searchInput, setSearchInput] = useState('');
  const debouncedSearch = useDebounce(searchInput, 300);

  // Date filter state
  const [datePreset, setDatePreset] = useState<DatePreset>('custom');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Filter state
  const [actionFilter, setActionFilter] = useState('');
  const [resourceTypeFilter, setResourceTypeFilter] = useState('');
  const [userFilter, setUserFilter] = useState('');

  // Filter options
  const [availableActions, setAvailableActions] = useState<string[]>([]);
  const [availableResourceTypes, setAvailableResourceTypes] = useState<string[]>([]);
  const [availableUsers, setAvailableUsers] = useState<Array<{ id: string; email: string }>>([]);

  // Detail dialog state
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // Export state
  const [isExporting, setIsExporting] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);

  // Auth check
  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.AUDIT_VIEW)) {
      router.push('/unauthorized');
    }
  }, [authLoading, hasPermission, router]);

  // Load filter options
  useEffect(() => {
    loadFilterOptions();
  }, []);

  // Handle date preset changes
  useEffect(() => {
    if (datePreset !== 'custom') {
      const { from, to } = getDateFromPreset(datePreset);
      setDateFrom(from);
      setDateTo(to);
    }
  }, [datePreset]);

  // Load logs when filters change
  useEffect(() => {
    loadLogs();
  }, [page, actionFilter, resourceTypeFilter, userFilter, debouncedSearch, dateFrom, dateTo]);

  const loadFilterOptions = async () => {
    try {
      const [actions, resourceTypes, users] = await Promise.all([
        api.getAuditActions(),
        api.getAuditResourceTypes(),
        api.getAuditUsers(),
      ]);
      setAvailableActions(actions);
      setAvailableResourceTypes(resourceTypes);
      setAvailableUsers(users);
    } catch {
      // Silent fail for filter options
    }
  };

  const loadLogs = async () => {
    setIsLoading(true);
    setError('');
    try {
      // Build date params
      let dateFromParam: string | undefined;
      let dateToParam: string | undefined;

      if (dateFrom) {
        dateFromParam = new Date(dateFrom).toISOString();
      }
      if (dateTo) {
        // Set to end of day
        const toDate = new Date(dateTo);
        toDate.setHours(23, 59, 59, 999);
        dateToParam = toDate.toISOString();
      }

      const response = await api.getAuditLogs({
        page,
        page_size: pageSize,
        action: actionFilter || undefined,
        resource_type: resourceTypeFilter || undefined,
        admin_user_id: userFilter || undefined,
        date_from: dateFromParam,
        date_to: dateToParam,
        search: debouncedSearch || undefined,
      });
      setLogs(response.items);
      setTotalPages(response.total_pages);
      setTotal(response.total);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('failedToLoad');
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewDetails = (log: AuditLogEntry) => {
    setSelectedLog(log);
    setDetailDialogOpen(true);
  };

  const handleClearFilters = () => {
    setSearchInput('');
    setDatePreset('custom');
    setDateFrom('');
    setDateTo('');
    setActionFilter('');
    setResourceTypeFilter('');
    setUserFilter('');
    setPage(1);
  };

  const handleDatePresetChange = (preset: DatePreset) => {
    setDatePreset(preset);
    setPage(1);
  };

  const handleExport = async (limit: number, format: 'csv' | 'json') => {
    setIsExporting(true);
    try {
      // Build date params
      let dateFromParam: string | undefined;
      let dateToParam: string | undefined;

      if (dateFrom) {
        dateFromParam = new Date(dateFrom).toISOString();
      }
      if (dateTo) {
        const toDate = new Date(dateTo);
        toDate.setHours(23, 59, 59, 999);
        dateToParam = toDate.toISOString();
      }

      const blob = await api.exportAuditLogs({
        format,
        limit,
        action: actionFilter || undefined,
        resource_type: resourceTypeFilter || undefined,
        admin_user_id: userFilter || undefined,
        date_from: dateFromParam,
        date_to: dateToParam,
        search: debouncedSearch || undefined,
      });

      // Download the blob
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_log_${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  };

  return {
    // Data
    logs,
    isLoading,
    error,
    total,
    authLoading,

    // Pagination
    page,
    setPage,
    totalPages,

    // Search
    searchInput,
    setSearchInput,

    // Date filters
    datePreset,
    dateFrom,
    dateTo,
    setDateFrom,
    setDateTo,
    handleDatePresetChange,

    // Filters
    actionFilter,
    setActionFilter,
    resourceTypeFilter,
    setResourceTypeFilter,
    userFilter,
    setUserFilter,

    // Filter options
    availableActions,
    availableResourceTypes,
    availableUsers,

    // Detail dialog
    selectedLog,
    detailDialogOpen,
    setDetailDialogOpen,

    // Export
    isExporting,
    exportDialogOpen,
    setExportDialogOpen,

    // Handlers
    loadLogs,
    handleViewDetails,
    handleClearFilters,
    handleExport,
  };
}
