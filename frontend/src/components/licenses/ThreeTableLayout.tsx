'use client';

import { useState, useMemo } from 'react';
import { License, LicenseStats } from '@/lib/api';
import { LicenseTable } from './LicenseTable';
import { LicenseStatsCards } from './LicenseStats';
import { Users, Package, Globe, AlertTriangle, Bot } from 'lucide-react';

interface ThreeTableLayoutProps {
  assigned: License[];
  unassigned: License[];
  external: License[];
  serviceAccounts?: License[];
  stats: LicenseStats;
  showProvider?: boolean;
  showStats?: boolean;
  maxUsers?: number | null; // For package providers
  onServiceAccountClick?: (license: License) => void;
  onAdminAccountClick?: (license: License) => void;
  onAssignClick?: (license: License) => void;
  onDeleteClick?: (license: License) => void;
}

type Tab = 'assigned' | 'unassigned' | 'external' | 'service_accounts';

// Sort by email alphabetically
// Use metadata.email if available (e.g., JetBrains), otherwise external_user_id
const sortByEmail = (a: License, b: License) => {
  const emailA = (a.metadata?.email || a.external_user_id || '').toLowerCase();
  const emailB = (b.metadata?.email || b.external_user_id || '').toLowerCase();
  return emailA.localeCompare(emailB);
};

export function ThreeTableLayout({
  assigned,
  unassigned,
  external,
  serviceAccounts = [],
  stats,
  showProvider = false,
  showStats = true,
  maxUsers = null,
  onServiceAccountClick,
  onAdminAccountClick,
  onAssignClick,
  onDeleteClick,
}: ThreeTableLayoutProps) {
  const [activeTab, setActiveTab] = useState<Tab>('assigned');

  // Calculate ACTIVE-only stats for consistency with Overview
  const activeStats = useMemo(() => {
    const activeAssigned = assigned.filter(l => l.status === 'active').length;
    const activeUnassigned = unassigned.filter(l => l.status === 'active').length;
    const activeExternal = external.filter(l => l.status === 'active').length;
    const activeServiceAccounts = serviceAccounts.filter(l => l.status === 'active').length;
    const totalActive = activeAssigned + activeUnassigned + activeExternal + activeServiceAccounts;

    // For package providers: available = max_users - total_active
    const available = maxUsers ? Math.max(0, maxUsers - totalActive) : null;

    return {
      ...stats,
      total_active: totalActive,
      total_assigned: activeAssigned,
      total_unassigned: activeUnassigned,
      total_external: activeExternal,
      total_service_accounts: activeServiceAccounts,
      available_seats: available,
    };
  }, [assigned, unassigned, external, serviceAccounts, stats, maxUsers]);

  // Split unassigned into active and inactive, sorted alphabetically
  const unassignedActive = useMemo(() =>
    unassigned.filter(l => l.status === 'active').sort(sortByEmail),
    [unassigned]
  );
  const unassignedInactive = useMemo(() =>
    unassigned.filter(l => l.status !== 'active').sort(sortByEmail),
    [unassigned]
  );

  // Split external into active and inactive, sorted alphabetically
  const externalActive = useMemo(() =>
    external.filter(l => l.status === 'active').sort(sortByEmail),
    [external]
  );
  const externalInactive = useMemo(() =>
    external.filter(l => l.status !== 'active').sort(sortByEmail),
    [external]
  );

  // Split service accounts into active and inactive, sorted alphabetically
  const serviceAccountsActive = useMemo(() =>
    serviceAccounts.filter(l => l.status === 'active').sort(sortByEmail),
    [serviceAccounts]
  );
  const serviceAccountsInactive = useMemo(() =>
    serviceAccounts.filter(l => l.status !== 'active').sort(sortByEmail),
    [serviceAccounts]
  );

  const tabs: { id: Tab; label: string; count: number; icon: React.ReactNode; warning?: boolean }[] = [
    { id: 'assigned', label: 'Assigned', count: assigned.filter(l => l.status === 'active').length, icon: <Users className="h-4 w-4" /> },
    { id: 'unassigned', label: 'Not in HRIS', count: unassignedActive.length, icon: <AlertTriangle className="h-4 w-4" />, warning: unassignedActive.length > 0 },
    { id: 'external', label: 'External', count: external.filter(l => l.status === 'active').length, icon: <Globe className="h-4 w-4" /> },
    ...(serviceAccounts.length > 0 ? [{ id: 'service_accounts' as Tab, label: 'Service Accounts', count: serviceAccountsActive.length, icon: <Bot className="h-4 w-4" /> }] : []),
  ];

  const getLicenses = () => {
    switch (activeTab) {
      case 'assigned':
        return assigned.sort(sortByEmail);
      case 'unassigned':
        return unassigned; // Handled separately with two tables
      case 'external':
        return external.sort(sortByEmail);
      case 'service_accounts':
        return serviceAccounts.sort(sortByEmail);
    }
  };

  const getEmptyMessage = () => {
    switch (activeTab) {
      case 'assigned':
        return 'No assigned licenses';
      case 'unassigned':
        return 'No licenses outside HRIS';
      case 'external':
        return 'No external licenses';
      case 'service_accounts':
        return 'No service accounts';
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
                  ? 'border-zinc-900 text-zinc-900'
                  : 'border-transparent text-muted-foreground hover:text-zinc-900'
              }`}
            >
              <span className={tab.warning ? 'text-red-500' : ''}>{tab.icon}</span>
              <span className={tab.warning ? 'text-red-600' : ''}>{tab.label}</span>
              <span
                className={`px-2 py-0.5 text-xs rounded-full ${
                  activeTab === tab.id
                    ? tab.warning ? 'bg-red-600 text-white' : 'bg-zinc-900 text-white'
                    : tab.warning ? 'bg-red-100 text-red-700' : 'bg-zinc-100 text-zinc-600'
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tables */}
      {activeTab === 'unassigned' ? (
        // Special handling for "Not in HRIS": Two tables - Active first, then Inactive
        <div className="space-y-8">
          {/* Active - Critical! */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              <h3 className="text-sm font-medium text-red-600">
                Active Licenses - Not in HRIS ({unassignedActive.length})
              </h3>
            </div>
            {unassignedActive.length > 0 ? (
              <div className="border border-red-200 rounded-lg overflow-hidden">
                <LicenseTable
                  licenses={unassignedActive}
                  showProvider={showProvider}
                  showEmployee={true}
                  emptyMessage="No active licenses outside HRIS"
                  onServiceAccountClick={onServiceAccountClick}
                  onAdminAccountClick={onAdminAccountClick}
                  onAssignClick={onAssignClick}
                  onDeleteClick={onDeleteClick}
                />
              </div>
            ) : (
              <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground bg-emerald-50/50 border-emerald-200">
                <p className="text-sm text-emerald-600">All active licenses are matched to HRIS</p>
              </div>
            )}
          </div>

          {/* Inactive */}
          {unassignedInactive.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                Inactive Licenses - Not in HRIS ({unassignedInactive.length})
              </h3>
              <LicenseTable
                licenses={unassignedInactive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage="No inactive licenses"
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onAssignClick={onAssignClick}
                onDeleteClick={onDeleteClick}
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
                Active External Licenses ({externalActive.length})
              </h3>
            </div>
            {externalActive.length > 0 ? (
              <LicenseTable
                licenses={externalActive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage="No active external licenses"
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onAssignClick={onAssignClick}
                onDeleteClick={onDeleteClick}
              />
            ) : (
              <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground">
                <p className="text-sm">No active external licenses</p>
              </div>
            )}
          </div>

          {/* Inactive External */}
          {externalInactive.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                Inactive External Licenses ({externalInactive.length})
              </h3>
              <LicenseTable
                licenses={externalInactive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage="No inactive external licenses"
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onAssignClick={onAssignClick}
                onDeleteClick={onDeleteClick}
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
                Active Service Accounts ({serviceAccountsActive.length})
              </h3>
            </div>
            {serviceAccountsActive.length > 0 ? (
              <LicenseTable
                licenses={serviceAccountsActive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage="No active service accounts"
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onDeleteClick={onDeleteClick}
              />
            ) : (
              <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground">
                <p className="text-sm">No active service accounts</p>
              </div>
            )}
          </div>

          {/* Inactive Service Accounts */}
          {serviceAccountsInactive.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                Inactive Service Accounts ({serviceAccountsInactive.length})
              </h3>
              <LicenseTable
                licenses={serviceAccountsInactive}
                showProvider={showProvider}
                showEmployee={true}
                emptyMessage="No inactive service accounts"
                onServiceAccountClick={onServiceAccountClick}
                onAdminAccountClick={onAdminAccountClick}
                onDeleteClick={onDeleteClick}
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
          onAssignClick={onAssignClick}
          onDeleteClick={onDeleteClick}
        />
      )}
    </div>
  );
}
