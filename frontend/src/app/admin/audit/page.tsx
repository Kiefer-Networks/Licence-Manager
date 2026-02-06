'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth, Permissions } from '@/components/auth-provider';
import { api, AuditLogEntry } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { AppLayout } from '@/components/layout/app-layout';
import { Loader2, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { AuditFilters } from './components/AuditFilters';
import { AuditTable } from './components/AuditTable';
import { AuditDetails } from './components/AuditDetails';
import { ExportDialog } from './components/ExportDialog';
import { DatePreset } from './components/DateRangePicker';

// Debounce helper
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
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

export default function AuditLogPage() {
  const t = useTranslations('audit');
  const tCommon = useTranslations('common');
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

  if (authLoading || (isLoading && logs.length === 0)) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
            <p className="text-muted-foreground text-sm mt-0.5">
              {t('details')}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={loadLogs} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            {tCommon('refresh')}
          </Button>
        </div>

        {/* Filters */}
        <AuditFilters
          search={searchInput}
          onSearchChange={(v) => { setSearchInput(v); setPage(1); }}
          datePreset={datePreset}
          dateFrom={dateFrom}
          dateTo={dateTo}
          onDatePresetChange={handleDatePresetChange}
          onDateFromChange={(v) => { setDateFrom(v); setPage(1); }}
          onDateToChange={(v) => { setDateTo(v); setPage(1); }}
          actionFilter={actionFilter}
          resourceTypeFilter={resourceTypeFilter}
          userFilter={userFilter}
          onActionFilterChange={(v) => { setActionFilter(v); setPage(1); }}
          onResourceTypeFilterChange={(v) => { setResourceTypeFilter(v); setPage(1); }}
          onUserFilterChange={(v) => { setUserFilter(v); setPage(1); }}
          availableActions={availableActions}
          availableResourceTypes={availableResourceTypes}
          availableUsers={availableUsers}
          onClearFilters={handleClearFilters}
          onExport={() => setExportDialogOpen(true)}
          isExporting={isExporting}
          totalEntries={total}
        />

        {/* Error */}
        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Table */}
        <AuditTable logs={logs} onViewDetails={handleViewDetails} />

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-2">
            <p className="text-sm text-muted-foreground">
              {t('pageOf', { page, total: totalPages })}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1 || isLoading}
              >
                <ChevronLeft className="h-4 w-4" />
                {t('previous')}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages || isLoading}
              >
                {tCommon('next')}
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Dialog */}
      <AuditDetails
        log={selectedLog}
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
      />

      {/* Export Dialog */}
      <ExportDialog
        open={exportDialogOpen}
        onOpenChange={setExportDialogOpen}
        totalRecords={total}
        onExport={handleExport}
      />
    </AppLayout>
  );
}
