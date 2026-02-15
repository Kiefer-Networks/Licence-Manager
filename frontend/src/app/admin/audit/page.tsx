'use client';

import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { AppLayout } from '@/components/layout/app-layout';
import { Loader2, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { AuditFilters } from './components/AuditFilters';
import { AuditTable } from './components/AuditTable';
import { AuditDetails } from './components/AuditDetails';
import { ExportDialog } from './components/ExportDialog';
import { useAuditLog } from '@/hooks/use-audit-log';

export default function AuditLogPage() {
  const t = useTranslations('audit');
  const tCommon = useTranslations('common');

  const {
    logs,
    isLoading,
    error,
    total,
    authLoading,
    page,
    setPage,
    totalPages,
    searchInput,
    setSearchInput,
    datePreset,
    dateFrom,
    dateTo,
    setDateFrom,
    setDateTo,
    handleDatePresetChange,
    actionFilter,
    setActionFilter,
    resourceTypeFilter,
    setResourceTypeFilter,
    userFilter,
    setUserFilter,
    availableActions,
    availableResourceTypes,
    availableUsers,
    selectedLog,
    detailDialogOpen,
    setDetailDialogOpen,
    isExporting,
    exportDialogOpen,
    setExportDialogOpen,
    loadLogs,
    handleViewDetails,
    handleClearFilters,
    handleExport,
  } = useAuditLog({ t });

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
