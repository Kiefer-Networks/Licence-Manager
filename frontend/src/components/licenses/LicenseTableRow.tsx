'use client';

import Link from 'next/link';
import { memo } from 'react';
import { useTranslations } from 'next-intl';
import { License, Provider } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { MoreHorizontal, Link2, Bot, ShieldCheck } from 'lucide-react';
import { formatMonthlyCost } from '@/lib/format';
import { REMOVABLE_PROVIDERS } from '@/lib/constants';
import { LicenseStatusBadge } from './LicenseStatusBadge';

interface LicenseTableRowProps {
  license: License;
  provider?: Provider;
  isSelected: boolean;
  onToggleSelect: () => void;
  onMarkAsService?: () => void;
  onMarkAsAdmin?: () => void;
  onLinkToEmployee?: () => void;
  showActions?: boolean;
}

export const LicenseTableRow = memo(function LicenseTableRow({
  license,
  provider,
  isSelected,
  onToggleSelect,
  onMarkAsService,
  onMarkAsAdmin,
  onLinkToEmployee,
  showActions = true,
}: LicenseTableRowProps) {
  const t = useTranslations('licenses');
  const tServiceAccounts = useTranslations('serviceAccounts');
  const tAdminAccounts = useTranslations('adminAccounts');

  const isRemovable = provider && REMOVABLE_PROVIDERS.includes(provider.name);

  return (
    <tr className={`border-b last:border-0 hover:bg-zinc-50/50 transition-colors ${isSelected ? 'bg-zinc-50' : ''}`}>
      <td className="px-4 py-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelect}
          className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-500"
        />
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <Link href={`/providers/${license.provider_id}`} className="font-medium hover:underline">
            {license.provider_name}
          </Link>
          {isRemovable && (
            <span className="text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded">
              {t('api')}
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-muted-foreground">{license.external_user_id}</td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2 flex-wrap">
          {license.employee_id && license.employee_status !== 'offboarded' && (
            <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-zinc-900 group">
              <div className="h-6 w-6 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0 group-hover:bg-zinc-200 transition-colors">
                <span className="text-xs font-medium text-zinc-600">
                  {license.employee_name?.charAt(0)}
                </span>
              </div>
              <span className="truncate hover:underline">{license.employee_name}</span>
            </Link>
          )}
          {license.employee_id && license.employee_status === 'offboarded' && (
            <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-zinc-900 group">
              <div className="h-6 w-6 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-medium text-red-600">
                  {license.employee_name?.charAt(0)}
                </span>
              </div>
              <span className="truncate text-muted-foreground line-through">{license.employee_name}</span>
            </Link>
          )}
          <LicenseStatusBadge license={license} showUnassigned={!license.employee_id} />
        </div>
      </td>
      <td className="px-4 py-3 text-muted-foreground">
        <div>
          <span>{license.license_type_display_name || license.license_type || '-'}</span>
          {license.license_type_display_name && license.license_type && (
            <span className="block text-xs text-muted-foreground/60 font-mono">{license.license_type}</span>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-right tabular-nums text-sm">
        {license.monthly_cost ? formatMonthlyCost(license.monthly_cost, license.currency) : '-'}
      </td>
      {showActions && (
        <td className="px-4 py-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {!license.employee_id && onLinkToEmployee && (
                <DropdownMenuItem onClick={onLinkToEmployee}>
                  <Link2 className="h-4 w-4 mr-2" />
                  {t('linkToEmployee')}
                </DropdownMenuItem>
              )}
              {onMarkAsService && (
                <DropdownMenuItem onClick={onMarkAsService}>
                  <Bot className="h-4 w-4 mr-2" />
                  {tServiceAccounts('markAsServiceAccount')}
                </DropdownMenuItem>
              )}
              {onMarkAsAdmin && (
                <DropdownMenuItem onClick={onMarkAsAdmin}>
                  <ShieldCheck className="h-4 w-4 mr-2" />
                  {tAdminAccounts('markAsAdminAccount')}
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </td>
      )}
    </tr>
  );
});
