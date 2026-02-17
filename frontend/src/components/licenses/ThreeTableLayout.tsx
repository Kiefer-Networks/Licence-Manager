'use client';

import { useState, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { License, LicenseStats } from '@/lib/api';
import { LicenseTable } from './LicenseTable';
import { LicenseStatsCards } from './LicenseStats';
import { Users, Package, Globe, AlertTriangle, Bot, Lightbulb } from 'lucide-react';

interface ThreeTableLayoutProps {
  assigned: License[];
  unassigned: License[];  // Licenses with no user assigned (empty external_user_id)
  notInHris?: License[];  // Has user (internal email) but not found in HRIS
  external: License[];
  serviceAccounts?: License[];
  suggested?: License[];  // Licenses with suggested matches needing confirmation
  stats: LicenseStats;
  showProvider?: boolean;
  showStats?: boolean;
  maxUsers?: number | null; // For package providers
  onServiceAccountClick?: (license: License) => void;
  onAdminAccountClick?: (license: License) => void;
  onLicenseTypeClick?: (license: License) => void;
  onAssignClick?: (license: License) => void;
  onDeleteClick?: (license: License) => void;
  onCancelClick?: (license: License) => void;
  onConfirmMatch?: (license: License) => void;
  onRejectMatch?: (license: License) => void;
}

type Tab = 'assigned' | 'unassigned' | 'not_in_hris' | 'external' | 'service_accounts' | 'suggested';

// Sort by email alphabetically
// Use metadata.email if available (e.g., JetBrains), otherwise external_user_id
const sortByEmail = (a: License, b: License) => {
  const emailA = (a.metadata?.email || a.external_user_id || '').toLowerCase();
  const emailB = (b.metadata?.email || b.external_user_id || '').toLowerCase();
  return emailA.localeCompare(emailB);
};

/**
 * Group licenses by user (same external_user_id/email) into single display rows.
 * Combines license_type with " + " and sums monthly costs.
 * Used for providers like Google Workspace where a user can have multiple SKUs.
 */
const groupLicensesByUser = (licenses: License[]): License[] => {
  const grouped = new Map<string, License[]>();
  for (const lic of licenses) {
    const key = (lic.metadata?.email || lic.external_user_id || lic.id).toLowerCase();
    const existing = grouped.get(key);
    if (existing) {
      existing.push(lic);
    } else {
      grouped.set(key, [lic]);
    }
  }

  return Array.from(grouped.values()).map(group => {
    if (group.length === 1) return group[0];

    const primary = group[0];
    const types = group.map(l => l.license_type_display_name || l.license_type || '').filter(Boolean);
    const totalCost = group.reduce((sum, l) => sum + (parseFloat(l.monthly_cost || '0') || 0), 0);

    return {
      ...primary,
      license_type: types.join(', '),
      license_type_display_name: undefined,
      monthly_cost: totalCost > 0 ? String(totalCost) : primary.monthly_cost,
    };
  });
};

export function ThreeTableLayout({
  assigned,
  unassigned,
  notInHris = [],
  external,
  serviceAccounts = [],
  suggested = [],
  stats,
  showProvider = false,
  showStats = true,
  maxUsers = null,
  onServiceAccountClick,
  onAdminAccountClick,
  onLicenseTypeClick,
  onAssignClick,
  onDeleteClick,
  onCancelClick,
  onConfirmMatch,
  onRejectMatch,
}: ThreeTableLayoutProps) {
  const t = useTranslations('licenses');
  // Default to suggested tab if there are suggestions to review
  const [activeTab, setActiveTab] = useState<Tab>(suggested.length > 0 ? 'suggested' : 'assigned');

  // Calculate ACTIVE-only stats for consistency with Overview
  const activeStats = useMemo(() => {
    const activeAssigned = assigned.filter(l => l.status === 'active').length;
    const activeUnassigned = unassigned.filter(l => l.status === 'active').length;
    const activeNotInHris = notInHris.filter(l => l.status === 'active').length;
    const activeExternal = external.filter(l => l.status === 'active').length;
    const activeServiceAccounts = serviceAccounts.filter(l => l.status === 'active').length;
    const activeSuggested = suggested.filter(l => l.status === 'active').length;
    const totalActive = activeAssigned + activeUnassigned + activeNotInHris + activeExternal + activeServiceAccounts + activeSuggested;

    // For package providers: available = max_users - total_active
    const available = maxUsers ? Math.max(0, maxUsers - totalActive) : null;

    return {
      ...stats,
      total_active: totalActive,
      total_assigned: activeAssigned,
      total_unassigned: activeUnassigned,
      total_not_in_hris: activeNotInHris,
      total_external: activeExternal,
      total_service_accounts: activeServiceAccounts,
      total_suggested: activeSuggested,
      available_seats: available,
    };
  }, [assigned, unassigned, notInHris, external, serviceAccounts, suggested, stats, maxUsers]);

  // Group licenses by user for display (combine multiple SKUs per user)
  const groupedAssigned = useMemo(() => groupLicensesByUser(assigned), [assigned]);
  const groupedUnassigned = useMemo(() => groupLicensesByUser(unassigned), [unassigned]);
  const groupedNotInHris = useMemo(() => groupLicensesByUser(notInHris), [notInHris]);
  const groupedExternal = useMemo(() => groupLicensesByUser(external), [external]);
  const groupedServiceAccounts = useMemo(() => groupLicensesByUser(serviceAccounts), [serviceAccounts]);
  const groupedSuggested = useMemo(() => groupLicensesByUser(suggested), [suggested]);

  // Split unassigned into active and inactive, sorted alphabetically
  const unassignedActive = useMemo(() =>
    groupedUnassigned.filter(l => l.status === 'active').sort(sortByEmail),
    [groupedUnassigned]
  );
  const unassignedInactive = useMemo(() =>
    groupedUnassigned.filter(l => l.status !== 'active').sort(sortByEmail),
    [groupedUnassigned]
  );

  // Split notInHris into active and inactive, sorted alphabetically
  const notInHrisActive = useMemo(() =>
    groupedNotInHris.filter(l => l.status === 'active').sort(sortByEmail),
    [groupedNotInHris]
  );
  const notInHrisInactive = useMemo(() =>
    groupedNotInHris.filter(l => l.status !== 'active').sort(sortByEmail),
    [groupedNotInHris]
  );

  // Split external into active and inactive, sorted alphabetically
  const externalActive = useMemo(() =>
    groupedExternal.filter(l => l.status === 'active').sort(sortByEmail),
    [groupedExternal]
  );
  const externalInactive = useMemo(() =>
    groupedExternal.filter(l => l.status !== 'active').sort(sortByEmail),
    [groupedExternal]
  );

  // Split service accounts into active and inactive, sorted alphabetically
  const serviceAccountsActive = useMemo(() =>
    groupedServiceAccounts.filter(l => l.status === 'active').sort(sortByEmail),
    [groupedServiceAccounts]
  );
  const serviceAccountsInactive = useMemo(() =>
    groupedServiceAccounts.filter(l => l.status !== 'active').sort(sortByEmail),
    [groupedServiceAccounts]
  );

  // Split suggested into active and inactive, sorted alphabetically
  const suggestedActive = useMemo(() =>
    groupedSuggested.filter(l => l.status === 'active').sort(sortByEmail),
    [groupedSuggested]
  );
  const suggestedInactive = useMemo(() =>
    groupedSuggested.filter(l => l.status !== 'active').sort(sortByEmail),
    [groupedSuggested]
  );

  const tabs: { id: Tab; label: string; count: number; icon: React.ReactNode; warning?: boolean; highlight?: boolean }[] = [
    { id: 'assigned', label: t('assigned'), count: groupedAssigned.filter(l => l.status === 'active').length, icon: <Users className="h-4 w-4" /> },
    ...(suggestedActive.length > 0 ? [{ id: 'suggested' as Tab, label: t('suggested'), count: suggestedActive.length, icon: <Lightbulb className="h-4 w-4" />, highlight: true }] : []),
    ...(notInHrisActive.length > 0 ? [{ id: 'not_in_hris' as Tab, label: t('notInHRIS'), count: notInHrisActive.length, icon: <AlertTriangle className="h-4 w-4" />, warning: true }] : []),
    ...(unassignedActive.length > 0 ? [{ id: 'unassigned' as Tab, label: t('unassigned'), count: unassignedActive.length, icon: <Package className="h-4 w-4" />, warning: true }] : []),
    { id: 'external', label: t('external'), count: groupedExternal.filter(l => l.status === 'active').length, icon: <Globe className="h-4 w-4" /> },
    ...(serviceAccounts.length > 0 ? [{ id: 'service_accounts' as Tab, label: t('serviceAccount'), count: serviceAccountsActive.length, icon: <Bot className="h-4 w-4" /> }] : []),
  ];

  const getLicenses = () => {
    switch (activeTab) {
      case 'assigned':
        return groupedAssigned.sort(sortByEmail);
      case 'suggested':
        return groupedSuggested; // Handled separately with two tables
      case 'not_in_hris':
        return groupedNotInHris; // Handled separately with two tables
      case 'unassigned':
        return groupedUnassigned; // Handled separately with two tables
      case 'external':
        return groupedExternal.sort(sortByEmail);
      case 'service_accounts':
        return groupedServiceAccounts.sort(sortByEmail);
    }
  };

  const getEmptyMessage = () => {
    switch (activeTab) {
      case 'assigned':
        return t('noAssignedLicenses');
      case 'suggested':
        return t('noSuggestedMatches');
      case 'not_in_hris':
        return t('noLicensesNotInHRIS');
      case 'unassigned':
        return t('noUnassignedLicenses');
      case 'external':
        return t('noExternalLicenses');
      case 'service_accounts':
        return t('noServiceAccountsFound');
    }
  };

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      {showStats && <LicenseStatsCards stats={activeStats} />}

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? tab.highlight ? 'border-amber-500 text-amber-700 dark:text-amber-400' : 'border-foreground text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <span className={tab.warning ? 'text-red-500 dark:text-red-400' : tab.highlight ? 'text-amber-500 dark:text-amber-400' : ''}>{tab.icon}</span>
              <span className={tab.warning ? 'text-red-600 dark:text-red-400' : tab.highlight ? 'text-amber-600 dark:text-amber-400' : ''}>{tab.label}</span>
              <span
                className={`px-2 py-0.5 text-xs rounded-full ${
                  activeTab === tab.id
                    ? tab.warning ? 'bg-red-600 text-white' : tab.highlight ? 'bg-amber-500 text-white' : 'bg-primary text-primary-foreground'
                    : tab.warning ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300' : tab.highlight ? 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300' : 'bg-muted text-muted-foreground'
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tables */}
      {activeTab === 'suggested' ? (
        // "Suggested": Licenses with suggested matches needing confirmation
        <div className="space-y-8">
          {/* Active */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="h-4 w-4 text-amber-500 dark:text-amber-400" />
              <h3 className="text-sm font-medium text-amber-600 dark:text-amber-400">
                {t('activeSuggested', { count: suggestedActive.length })}
              </h3>
            </div>
            {suggestedActive.length > 0 ? (
              <div className="border border-amber-200 dark:border-amber-800 rounded-lg overflow-hidden bg-amber-50/30 dark:bg-amber-950/30">
                <LicenseTable
                  licenses={suggestedActive}
                  showProvider={showProvider}
                  showEmployee={true}
                  showSuggestion={true}
                  emptyMessage={t('noSuggestedMatches')}
                  onServiceAccountClick={onServiceAccountClick}
                  onAdminAccountClick={onAdminAccountClick}
                  onLicenseTypeClick={onLicenseTypeClick}
                  onAssignClick={onAssignClick}
                  onDeleteClick={onDeleteClick}
                  onCancelClick={onCancelClick}
                  onConfirmMatch={onConfirmMatch}
                  onRejectMatch={onRejectMatch}
                />
              </div>
            ) : (
              <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground bg-emerald-50/50 dark:bg-emerald-950/50 border-emerald-200 dark:border-emerald-800">
                <p className="text-sm text-emerald-600 dark:text-emerald-400">{t('allSuggestionsReviewed')}</p>
              </div>
            )}
          </div>

          {/* Inactive */}
          {suggestedInactive.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                {t('inactiveSuggested', { count: suggestedInactive.length })}
              </h3>
              <LicenseTable
                licenses={suggestedInactive}
                showProvider={showProvider}
                showEmployee={true}
                showSuggestion={true}
                emptyMessage={t('noInactiveLicenses')}
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onLicenseTypeClick={onLicenseTypeClick}
                onAssignClick={onAssignClick}
                onDeleteClick={onDeleteClick}
                onCancelClick={onCancelClick}
                onConfirmMatch={onConfirmMatch}
                onRejectMatch={onRejectMatch}
              />
            </div>
          )}
        </div>
      ) : activeTab === 'not_in_hris' ? (
        // "Not in HRIS": Has user email but not found in HRIS
        <div className="space-y-8">
          {/* Active - Critical! */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-4 w-4 text-red-500 dark:text-red-400" />
              <h3 className="text-sm font-medium text-red-600 dark:text-red-400">
                {t('activeNotInHRIS', { count: notInHrisActive.length })}
              </h3>
            </div>
            {notInHrisActive.length > 0 ? (
              <div className="border border-red-200 dark:border-red-800 rounded-lg overflow-hidden">
                <LicenseTable
                  licenses={notInHrisActive}
                  showProvider={showProvider}
                  showEmployee={true}
                  emptyMessage={t('noLicensesNotInHRIS')}
                  onServiceAccountClick={onServiceAccountClick}
                  onAdminAccountClick={onAdminAccountClick}
                  onLicenseTypeClick={onLicenseTypeClick}
                  onAssignClick={onAssignClick}
                  onDeleteClick={onDeleteClick}
                  onCancelClick={onCancelClick}
                />
              </div>
            ) : (
              <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground bg-emerald-50/50 dark:bg-emerald-950/50 border-emerald-200 dark:border-emerald-800">
                <p className="text-sm text-emerald-600 dark:text-emerald-400">{t('allLicensesMatchedToHRIS')}</p>
              </div>
            )}
          </div>

          {/* Inactive */}
          {notInHrisInactive.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                {t('inactiveLicensesNotInHRIS', { count: notInHrisInactive.length })}
              </h3>
              <LicenseTable
                licenses={notInHrisInactive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage={t('noInactiveLicenses')}
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onLicenseTypeClick={onLicenseTypeClick}
                onAssignClick={onAssignClick}
                onDeleteClick={onDeleteClick}
                onCancelClick={onCancelClick}
              />
            </div>
          )}
        </div>
      ) : activeTab === 'unassigned' ? (
        // "Unassigned": No user assigned (empty or non-email external_user_id)
        <div className="space-y-8">
          {/* Active */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Package className="h-4 w-4 text-amber-500 dark:text-amber-400" />
              <h3 className="text-sm font-medium text-amber-600 dark:text-amber-400">
                {t('activeUnassigned', { count: unassignedActive.length })}
              </h3>
            </div>
            {unassignedActive.length > 0 ? (
              <div className="border border-amber-200 dark:border-amber-800 rounded-lg overflow-hidden">
                <LicenseTable
                  licenses={unassignedActive}
                  showProvider={showProvider}
                  showEmployee={true}
                  emptyMessage={t('noUnassignedLicenses')}
                  onServiceAccountClick={onServiceAccountClick}
                  onAdminAccountClick={onAdminAccountClick}
                  onLicenseTypeClick={onLicenseTypeClick}
                  onAssignClick={onAssignClick}
                  onDeleteClick={onDeleteClick}
                  onCancelClick={onCancelClick}
                />
              </div>
            ) : (
              <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground bg-emerald-50/50 dark:bg-emerald-950/50 border-emerald-200 dark:border-emerald-800">
                <p className="text-sm text-emerald-600 dark:text-emerald-400">{t('allLicensesAssigned')}</p>
              </div>
            )}
          </div>

          {/* Inactive */}
          {unassignedInactive.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                {t('inactiveUnassigned', { count: unassignedInactive.length })}
              </h3>
              <LicenseTable
                licenses={unassignedInactive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage={t('noInactiveLicenses')}
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onLicenseTypeClick={onLicenseTypeClick}
                onAssignClick={onAssignClick}
                onDeleteClick={onDeleteClick}
                onCancelClick={onCancelClick}
              />
            </div>
          )}
        </div>
      ) : activeTab === 'external' ? (
        // External: Two tables - Active first, then Inactive
        <div className="space-y-8">
          {/* Active External */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Globe className="h-4 w-4 text-orange-500" />
              <h3 className="text-sm font-medium">
                {t('activeExternalLicenses', { count: externalActive.length })}
              </h3>
            </div>
            {externalActive.length > 0 ? (
              <LicenseTable
                licenses={externalActive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage={t('noActiveExternalLicenses')}
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onLicenseTypeClick={onLicenseTypeClick}
                onAssignClick={onAssignClick}
                onDeleteClick={onDeleteClick}
                onCancelClick={onCancelClick}
              />
            ) : (
              <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground">
                <p className="text-sm">{t('noActiveExternalLicenses')}</p>
              </div>
            )}
          </div>

          {/* Inactive External */}
          {externalInactive.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                {t('inactiveExternalLicenses', { count: externalInactive.length })}
              </h3>
              <LicenseTable
                licenses={externalInactive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage={t('noInactiveExternalLicenses')}
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onLicenseTypeClick={onLicenseTypeClick}
                onAssignClick={onAssignClick}
                onDeleteClick={onDeleteClick}
                onCancelClick={onCancelClick}
              />
            </div>
          )}
        </div>
      ) : activeTab === 'service_accounts' ? (
        // Service Accounts: Two tables - Active first, then Inactive
        <div className="space-y-8">
          {/* Active Service Accounts */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Bot className="h-4 w-4 text-blue-500" />
              <h3 className="text-sm font-medium">
                {t('activeServiceAccounts', { count: serviceAccountsActive.length })}
              </h3>
            </div>
            {serviceAccountsActive.length > 0 ? (
              <LicenseTable
                licenses={serviceAccountsActive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage={t('noActiveServiceAccounts')}
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onLicenseTypeClick={onLicenseTypeClick}
                onDeleteClick={onDeleteClick}
                onCancelClick={onCancelClick}
              />
            ) : (
              <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground">
                <p className="text-sm">{t('noActiveServiceAccounts')}</p>
              </div>
            )}
          </div>

          {/* Inactive Service Accounts */}
          {serviceAccountsInactive.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                {t('inactiveServiceAccounts', { count: serviceAccountsInactive.length })}
              </h3>
              <LicenseTable
                licenses={serviceAccountsInactive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage={t('noInactiveServiceAccounts')}
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onLicenseTypeClick={onLicenseTypeClick}
                onDeleteClick={onDeleteClick}
                onCancelClick={onCancelClick}
              />
            </div>
          )}
        </div>
      ) : (
        // Standard single table for Assigned tab
        <LicenseTable
          licenses={getLicenses()}
          showProvider={showProvider}
          showEmployee={true}
          emptyMessage={getEmptyMessage()}
          onServiceAccountClick={onServiceAccountClick}
          onAdminAccountClick={onAdminAccountClick}
          onLicenseTypeClick={onLicenseTypeClick}
          onAssignClick={onAssignClick}
          onDeleteClick={onDeleteClick}
          onCancelClick={onCancelClick}
        />
      )}
    </div>
  );
}
