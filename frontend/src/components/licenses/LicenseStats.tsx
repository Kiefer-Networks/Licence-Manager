'use client';

import { useTranslations } from 'next-intl';
import { Card, CardContent } from '@/components/ui/card';
import { LicenseStats as LicenseStatsType } from '@/lib/api';
import { formatMonthlyCost } from '@/lib/format';
import { Key, Users, Package, UserMinus, Wallet, Bot } from 'lucide-react';

interface ExtendedStats extends LicenseStatsType {
  available_seats?: number | null;
}

interface LicenseStatsProps {
  stats: ExtendedStats;
}

export function LicenseStatsCards({ stats }: LicenseStatsProps) {
  const t = useTranslations('licenses');
  const hasNotInHris = (stats.total_not_in_hris ?? 0) > 0;
  const hasUnassigned = stats.total_unassigned > 0;
  const hasAvailableSeats = stats.available_seats !== undefined && stats.available_seats !== null;

  return (
    <div className={`grid grid-cols-2 ${hasAvailableSeats ? 'lg:grid-cols-5' : 'lg:grid-cols-4'} gap-4`}>
      <Card>
        <CardContent className="pt-5 pb-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Key className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">{t('active')}</span>
          </div>
          <p className="text-2xl font-semibold">{stats.total_active}</p>
        </CardContent>
      </Card>

      <Card className={hasNotInHris || hasUnassigned ? 'border-red-200 bg-red-50/30' : ''}>
        <CardContent className="pt-5 pb-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Users className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">{t('assigned')}</span>
          </div>
          <div className="flex items-baseline gap-1 flex-wrap">
            <span className="text-2xl font-semibold">{stats.total_assigned}</span>
            {stats.total_external > 0 && (
              <span className="text-sm text-muted-foreground">+ {stats.total_external} <span className="text-xs">({t('ext')})</span></span>
            )}
            {(stats.total_service_accounts ?? 0) > 0 && (
              <span className="text-sm text-blue-600">+ {stats.total_service_accounts} <span className="text-xs">({t('svc')})</span></span>
            )}
            {hasNotInHris && (
              <span className="text-sm text-red-600 font-medium">+ {stats.total_not_in_hris} <span className="text-xs">(⚠ {t('notInHRISShort')})</span></span>
            )}
            {hasUnassigned && (
              <span className="text-sm text-amber-600 font-medium">+ {stats.total_unassigned} <span className="text-xs">({t('unassignedShort')})</span></span>
            )}
          </div>
        </CardContent>
      </Card>

      {hasAvailableSeats && (
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Package className="h-4 w-4" />
              <span className="text-xs font-medium uppercase">{t('available')}</span>
            </div>
            <p className="text-2xl font-semibold text-emerald-600">{stats.available_seats}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="pt-5 pb-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <UserMinus className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">{t('inactive')}</span>
          </div>
          <p className="text-2xl font-semibold text-zinc-400">{stats.total_inactive}</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-5 pb-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Wallet className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">{t('monthlyCost')}</span>
          </div>
          <p className="text-lg font-semibold">
            {formatMonthlyCost(stats.monthly_cost, stats.currency).replace(' / month', '')}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
