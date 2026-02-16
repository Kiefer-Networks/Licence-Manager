'use client';

import { Suspense, useCallback, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth, Permissions } from '@/components/auth-provider';
import { AppLayout } from '@/components/layout/app-layout';
import { Button } from '@/components/ui/button';
import { License, Provider } from '@/lib/api';
import { formatMonthlyCost } from '@/lib/format';
import {
  LicenseStatsCards,
  LicenseFilters,
  LicenseTabs,
  LicenseBulkToolbar,
  LicenseTableRow,
  BulkRemoveDialog,
  BulkDeleteDialog,
  BulkUnassignDialog,
  MarkAsAccountDialog,
  LinkToEmployeeDialog,
} from '@/components/licenses';
import { useLicenses, LicenseTab } from '@/hooks/use-licenses';
import {
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Loader2,
  Key,
  AlertTriangle,
  Globe,
} from 'lucide-react';
import Link from 'next/link';

function LicensesContent() {
  const t = useTranslations('licenses');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { hasPermission, isLoading: authLoading } = useAuth();
  const canCreate = hasPermission(Permissions.LICENSES_CREATE);
  const canUpdate = hasPermission(Permissions.LICENSES_UPDATE);
  const canDelete = hasPermission(Permissions.LICENSES_DELETE);
  const canAssign = hasPermission(Permissions.LICENSES_ASSIGN);
  const canBulk = hasPermission(Permissions.LICENSES_BULK);
  const canImport = hasPermission(Permissions.LICENSES_IMPORT);

  // Use custom hook for license data management
  const licenses = useLicenses();

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.LICENSES_VIEW)) {
      router.push('/unauthorized');
      return;
    }
  }, [authLoading, hasPermission, router]);

  // Tab change handler
  const handleTabChange = useCallback((tab: LicenseTab) => {
    licenses.setActiveTab(tab);
    licenses.clearSelection();
  }, [licenses]);

  // Sort icon component
  const SortIcon = ({ column }: { column: string }) => {
    if (licenses.sortColumn !== column) return <ChevronsUpDown className="h-3.5 w-3.5 text-zinc-400" />;
    return licenses.sortDirection === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />;
  };

  // Stats calculation
  const stats = useMemo(() => {
    if (!licenses.categorizedData) return null;
    const data = licenses.categorizedData;
    return {
      total_active: licenses.assignedActiveCount + licenses.notInHrisActiveCount + licenses.unassignedActiveCount + licenses.externalActiveCount +
                    (data.service_accounts?.filter(l => l.status === 'active').length || 0),
      total_assigned: licenses.assignedActiveCount,
      total_not_in_hris: licenses.notInHrisActiveCount,
      total_unassigned: licenses.unassignedActiveCount,
      total_external: licenses.externalActiveCount,
      total_service_accounts: data.service_accounts?.filter(l => l.status === 'active').length || 0,
      total_inactive: data.assigned.filter(l => l.status !== 'active').length +
                      (data.not_in_hris?.filter(l => l.status !== 'active').length || 0) +
                      data.unassigned.filter(l => l.status !== 'active').length +
                      data.external.filter(l => l.status !== 'active').length +
                      (data.service_accounts?.filter(l => l.status !== 'active').length || 0),
      total_suggested: 0,
      total_external_review: 0,
      total_external_guest: 0,
      monthly_cost: data.stats.monthly_cost,
      potential_savings: data.stats.potential_savings,
      currency: data.stats.currency,
      has_currency_mix: data.stats.has_currency_mix || false,
      currencies_found: data.stats.currencies_found || [],
    };
  }, [licenses.categorizedData, licenses.assignedActiveCount, licenses.notInHrisActiveCount, licenses.unassignedActiveCount, licenses.externalActiveCount]);

  // Provider lookup for table rows
  const getProvider = useCallback((providerId: string) => {
    return licenses.providers.find(p => p.id === providerId);
  }, [licenses.providers]);

  // Render table for split tables (not_in_hris, unassigned, external tabs)
  const renderSplitTable = (licenseList: License[], title: string, icon: React.ReactNode, isWarning: boolean = false) => (
    <div>
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h3 className={`text-sm font-medium ${isWarning ? 'text-red-600' : ''}`}>{title}</h3>
      </div>
      {licenseList.length > 0 ? (
        <div className={`border rounded-lg bg-white overflow-hidden ${isWarning ? 'border-red-200' : ''}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-zinc-50/50">
                <th className="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={licenseList.every(l => licenses.selectedIds.has(l.id)) && licenseList.length > 0}
                    onChange={() => {
                      const allSelected = licenseList.every(l => licenses.selectedIds.has(l.id));
                      const newSet = new Set(licenses.selectedIds);
                      licenseList.forEach(l => allSelected ? newSet.delete(l.id) : newSet.add(l.id));
                      licenses.setSelectedIds(newSet);
                    }}
                    className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-500"
                  />
                </th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('provider')}</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('user')}</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('employee')}</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('type')}</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('cost')}</th>
                <th className="w-10 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {licenseList.map((license) => (
                <LicenseTableRow
                  key={license.id}
                  license={license}
                  provider={getProvider(license.provider_id)}
                  isSelected={licenses.selectedIds.has(license.id)}
                  onToggleSelect={() => licenses.toggleSelect(license.id)}
                  onMarkAsService={() => licenses.setMarkAsDialog({ license, type: 'service' })}
                  onMarkAsAdmin={() => licenses.setMarkAsDialog({ license, type: 'admin' })}
                  onLinkToEmployee={!license.employee_id ? () => licenses.setLinkDialog(license) : undefined}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground bg-emerald-50/50 border-emerald-200">
          <p className="text-sm text-emerald-600">
            {licenses.activeTab === 'unassigned' ? t('allMatchedToHRIS') : t('noActiveExternalLicenses')}
          </p>
        </div>
      )}
    </div>
  );

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="pt-2">
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{t('description')}</p>
        </div>

        {/* Stats */}
        {stats && <LicenseStatsCards stats={stats} />}

        {/* Bulk Action Toolbar */}
        <LicenseBulkToolbar
          selectedCount={licenses.selectedIds.size}
          assignedCount={licenses.assignedLicenses.length}
          removableCount={licenses.removableLicenses.length}
          onUnassign={() => licenses.setBulkActionDialog('unassign')}
          onRemove={() => licenses.setBulkActionDialog('remove')}
          onDelete={() => licenses.setBulkActionDialog('delete')}
          onClear={licenses.clearSelection}
        />

        {/* Tabs */}
        <LicenseTabs
          activeTab={licenses.activeTab}
          onTabChange={handleTabChange}
          assignedCount={licenses.assignedActiveCount}
          notInHrisCount={licenses.notInHrisActiveCount}
          unassignedCount={licenses.unassignedActiveCount}
          externalCount={licenses.externalActiveCount}
        />

        {/* Filters */}
        <LicenseFilters
          search={licenses.search}
          onSearchChange={licenses.setSearch}
          selectedProvider={licenses.selectedProvider}
          onProviderChange={licenses.setSelectedProvider}
          selectedDepartment={licenses.selectedDepartment}
          onDepartmentChange={licenses.setSelectedDepartment}
          providers={licenses.licenseProviders}
          departments={licenses.departments}
          filteredCount={licenses.filteredLicenses.length}
          onClearFilters={licenses.clearFilters}
        />

        {/* Table */}
        {authLoading || licenses.loading ? (
          <div className="border rounded-lg bg-white flex items-center justify-center h-64">
            <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
          </div>
        ) : licenses.filteredLicenses.length === 0 ? (
          <div className="border rounded-lg bg-white flex flex-col items-center justify-center h-64 text-muted-foreground">
            <Key className="h-8 w-8 mb-2 opacity-30" />
            <p className="text-sm">{licenses.activeTab === 'unassigned' ? t('noLicensesOutsideHRIS') : t('noLicensesFound', { tab: licenses.activeTab })}</p>
          </div>
        ) : licenses.showSplitTables ? (
          <div className="space-y-8">
            {renderSplitTable(
              licenses.activeLicenses,
              licenses.activeTab === 'unassigned'
                ? t('activeNotInHRIS', { count: licenses.activeLicenses.length })
                : t('activeExternal', { count: licenses.activeLicenses.length }),
              licenses.activeTab === 'unassigned'
                ? <AlertTriangle className="h-4 w-4 text-red-500" />
                : <Globe className="h-4 w-4 text-orange-500" />,
              licenses.activeTab === 'unassigned'
            )}
            {licenses.inactiveLicenses.length > 0 && renderSplitTable(
              licenses.inactiveLicenses,
              licenses.activeTab === 'unassigned'
                ? t('inactiveNotInHRIS', { count: licenses.inactiveLicenses.length })
                : t('inactiveExternal', { count: licenses.inactiveLicenses.length }),
              <></>,
              false
            )}
          </div>
        ) : (
          <div className="border rounded-lg bg-white overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-zinc-50/50">
                  <th className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={licenses.selectedIds.size === licenses.paginatedLicenses.length && licenses.paginatedLicenses.length > 0}
                      onChange={licenses.toggleSelectAll}
                      className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-500"
                    />
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => licenses.handleSort('provider_name')} className="flex items-center gap-1.5 hover:text-foreground">
                      {t('provider')} <SortIcon column="provider_name" />
                    </button>
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => licenses.handleSort('external_user_id')} className="flex items-center gap-1.5 hover:text-foreground">
                      {t('user')} <SortIcon column="external_user_id" />
                    </button>
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => licenses.handleSort('employee_name')} className="flex items-center gap-1.5 hover:text-foreground">
                      {t('employee')} <SortIcon column="employee_name" />
                    </button>
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('type')}</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">
                    <button onClick={() => licenses.handleSort('monthly_cost')} className="flex items-center gap-1.5 justify-end hover:text-foreground ml-auto">
                      {t('cost')} <SortIcon column="monthly_cost" />
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                {licenses.paginatedLicenses.map((license) => (
                  <LicenseTableRow
                    key={license.id}
                    license={license}
                    provider={getProvider(license.provider_id)}
                    isSelected={licenses.selectedIds.has(license.id)}
                    onToggleSelect={() => licenses.toggleSelect(license.id)}
                    showActions={false}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!licenses.showSplitTables && licenses.totalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {t('pageOf', { page: licenses.page, total: licenses.totalPages })}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => licenses.setPage(licenses.page - 1)} disabled={licenses.page === 1}>
                {t('previous')}
              </Button>
              <Button variant="outline" size="sm" onClick={() => licenses.setPage(licenses.page + 1)} disabled={licenses.page === licenses.totalPages}>
                {tCommon('next')}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Dialogs */}
      <BulkRemoveDialog
        open={licenses.bulkActionDialog === 'remove'}
        onOpenChange={() => licenses.setBulkActionDialog(null)}
        removableCount={licenses.removableLicenses.length}
        totalSelected={licenses.selectedIds.size}
        loading={licenses.bulkActionLoading}
        onConfirm={licenses.handleBulkRemove}
      />

      <BulkDeleteDialog
        open={licenses.bulkActionDialog === 'delete'}
        onOpenChange={() => licenses.setBulkActionDialog(null)}
        selectedCount={licenses.selectedIds.size}
        loading={licenses.bulkActionLoading}
        onConfirm={licenses.handleBulkDelete}
      />

      <BulkUnassignDialog
        open={licenses.bulkActionDialog === 'unassign'}
        onOpenChange={() => licenses.setBulkActionDialog(null)}
        assignedCount={licenses.assignedLicenses.length}
        loading={licenses.bulkActionLoading}
        onConfirm={licenses.handleBulkUnassign}
      />

      <MarkAsAccountDialog
        open={!!licenses.markAsDialog}
        onOpenChange={() => licenses.setMarkAsDialog(null)}
        license={licenses.markAsDialog?.license || null}
        type={licenses.markAsDialog?.type || 'service'}
        onSuccess={licenses.loadLicenses}
        onToast={licenses.showToast}
      />

      <LinkToEmployeeDialog
        open={!!licenses.linkDialog}
        onOpenChange={() => licenses.setLinkDialog(null)}
        license={licenses.linkDialog}
        onSuccess={licenses.loadLicenses}
        onToast={licenses.showToast}
      />

      {/* Toast */}
      {licenses.toast && (
        <div className={`fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
          licenses.toast.type === 'success' ? 'bg-zinc-900 text-white' : 'bg-red-600 text-white'
        }`}>
          {licenses.toast.message}
        </div>
      )}
    </AppLayout>
  );
}

export default function LicensesPage() {
  return (
    <Suspense fallback={
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </AppLayout>
    }>
      <LicensesContent />
    </Suspense>
  );
}
