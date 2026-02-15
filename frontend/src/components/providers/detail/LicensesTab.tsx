'use client';

import { Button } from '@/components/ui/button';
import { ThreeTableLayout } from '@/components/licenses';
import { Plus, Key } from 'lucide-react';
import type { License, CategorizedLicensesResponse, Provider } from '@/lib/api';

export interface LicensesTabProps {
  provider: Provider;
  categorizedLicenses: CategorizedLicensesResponse | null;
  isManual: boolean;
  onAddLicense: (mode: 'single' | 'bulk' | 'seats') => void;
  onAssign: (license: License) => void;
  onDelete: (license: License) => void;
  onServiceAccount: (license: License) => void;
  onAdminAccount: (license: License) => void;
  onLicenseType?: (license: License) => void;
  onConfirmMatch: (license: License) => void;
  onRejectMatch: (license: License) => void;
  t: (key: string) => string;
}

/**
 * Licenses tab component for provider detail page.
 * Displays categorized license tables with actions.
 */
export function LicensesTab({
  provider,
  categorizedLicenses,
  isManual,
  onAddLicense,
  onAssign,
  onDelete,
  onServiceAccount,
  onAdminAccount,
  onLicenseType,
  onConfirmMatch,
  onRejectMatch,
  t,
}: LicensesTabProps) {
  return (
    <div className="space-y-4">
      {isManual && (
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => onAddLicense('single')}>
            <Plus className="h-4 w-4 mr-1.5" />
            Single License
          </Button>
          <Button variant="outline" size="sm" onClick={() => onAddLicense('bulk')}>
            <Plus className="h-4 w-4 mr-1.5" />
            Bulk Keys
          </Button>
          <Button variant="outline" size="sm" onClick={() => onAddLicense('seats')}>
            <Plus className="h-4 w-4 mr-1.5" />
            Add Seats
          </Button>
        </div>
      )}

      {categorizedLicenses ? (
        <ThreeTableLayout
          assigned={categorizedLicenses.assigned}
          unassigned={categorizedLicenses.unassigned}
          notInHris={categorizedLicenses.not_in_hris}
          external={categorizedLicenses.external}
          serviceAccounts={categorizedLicenses.service_accounts}
          suggested={categorizedLicenses.suggested}
          stats={categorizedLicenses.stats}
          showProvider={false}
          showStats={true}
          maxUsers={provider?.config?.provider_license_info?.max_users}
          onServiceAccountClick={onServiceAccount}
          onAdminAccountClick={onAdminAccount}
          onLicenseTypeClick={onLicenseType}
          onAssignClick={onAssign}
          onDeleteClick={onDelete}
          onConfirmMatch={onConfirmMatch}
          onRejectMatch={onRejectMatch}
        />
      ) : (
        <div className="border rounded-lg bg-white p-8 text-center text-muted-foreground">
          <Key className="h-8 w-8 mx-auto mb-2 opacity-30" />
          <p className="text-sm">{t('noLicensesYet')}</p>
        </div>
      )}
    </div>
  );
}
