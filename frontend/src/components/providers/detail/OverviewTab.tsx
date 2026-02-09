'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Key,
  Users,
  Package,
  UserMinus,
  DollarSign,
  AlertTriangle,
} from 'lucide-react';
import type { OverviewTabProps } from './types';

/**
 * Overview tab component for provider detail page.
 * Displays license statistics and provider information.
 */
export function OverviewTab({
  provider,
  stats,
  isManual,
  isSeatBased,
  formatDate,
  formatDateTimeWithSeconds,
  t,
  tCommon,
  tLicenses,
}: OverviewTabProps) {
  const {
    totalLicenses,
    assignedLicenses,
    unassignedLicenses,
    notInHrisLicenses,
    externalLicenses,
    inactiveLicenses,
    totalMonthlyCost,
    availableSeats,
  } = stats;

  // Determine billing cycle from package pricing or license pricing
  const packagePricing = provider.config?.package_pricing;
  const licensePricing = provider.config?.license_pricing || {};
  const firstPricing = Object.values(licensePricing)[0] as { billing_cycle?: string } | undefined;
  const billingCycle = packagePricing?.billing_cycle || firstPricing?.billing_cycle || 'monthly';
  const isYearly = billingCycle === 'yearly';
  const costLabel = isYearly ? 'Yearly Cost' : 'Monthly Cost';
  const displayCost = isYearly ? totalMonthlyCost * 12 : totalMonthlyCost;

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className={`grid grid-cols-2 ${availableSeats !== null ? 'lg:grid-cols-5' : 'lg:grid-cols-4'} gap-4`}>
        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Key className="h-4 w-4" />
              <span className="text-xs font-medium uppercase">{t('active')}</span>
            </div>
            <p className="text-2xl font-semibold">{totalLicenses}</p>
          </CardContent>
        </Card>

        <Card className={notInHrisLicenses > 0 || unassignedLicenses > 0 ? 'border-red-200 bg-red-50/30' : ''}>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Users className="h-4 w-4" />
              <span className="text-xs font-medium uppercase">{t('assigned')}</span>
            </div>
            <div className="flex items-baseline gap-1 flex-wrap">
              <span className="text-2xl font-semibold">{assignedLicenses}</span>
              {externalLicenses > 0 && (
                <span className="text-sm text-muted-foreground">+ {externalLicenses} <span className="text-xs">(ext)</span></span>
              )}
              {notInHrisLicenses > 0 && (
                <span className="text-sm text-red-600 font-medium">+ {notInHrisLicenses} <span className="text-xs">(⚠ {tLicenses('notInHRISShort')})</span></span>
              )}
              {unassignedLicenses > 0 && (
                <span className="text-sm text-amber-600 font-medium">+ {unassignedLicenses} <span className="text-xs">({tLicenses('unassignedShort')})</span></span>
              )}
            </div>
          </CardContent>
        </Card>

        {availableSeats !== null && (
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Package className="h-4 w-4" />
                <span className="text-xs font-medium uppercase">{t('available')}</span>
              </div>
              <p className="text-2xl font-semibold text-emerald-600">{availableSeats}</p>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <UserMinus className="h-4 w-4" />
              <span className="text-xs font-medium uppercase">{t('inactive')}</span>
            </div>
            <p className="text-2xl font-semibold text-zinc-400">{inactiveLicenses}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-5 pb-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <DollarSign className="h-4 w-4" />
              <span className="text-xs font-medium uppercase">{costLabel}</span>
            </div>
            <p className="text-xl font-semibold">
              {provider.config?.currency || 'EUR'} {displayCost.toFixed(2)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Provider Information Card */}
      <ProviderInfoCard
        provider={provider}
        isManual={isManual}
        isSeatBased={isSeatBased}
        formatDateTimeWithSeconds={formatDateTimeWithSeconds}
        t={t}
        tCommon={tCommon}
      />

      {/* Provider License Info (from API) */}
      {provider.config?.provider_license_info && (
        <ProviderLicenseCard
          provider={provider}
          totalLicenses={totalLicenses}
          formatDate={formatDate}
          t={t}
        />
      )}
    </div>
  );
}

/**
 * Provider information card sub-component.
 */
function ProviderInfoCard({
  provider,
  isManual,
  isSeatBased,
  formatDateTimeWithSeconds,
  t,
  tCommon,
}: {
  provider: OverviewTabProps['provider'];
  isManual: boolean;
  isSeatBased: boolean;
  formatDateTimeWithSeconds: OverviewTabProps['formatDateTimeWithSeconds'];
  t: OverviewTabProps['t'];
  tCommon: OverviewTabProps['tCommon'];
}) {
  const licensePricing = provider.config?.license_pricing || {};
  const pricingEntries = Object.values(licensePricing) as Array<{ billing_cycle?: string; cost?: string; currency?: string }>;
  const firstPricing = pricingEntries[0];
  const billingCycle = provider.config?.billing_cycle || firstPricing?.billing_cycle;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{t('providerInformation')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">{tCommon('type')}</span>
          <span>{isManual ? t('manualEntry') : t('apiIntegration')}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('licenseModel')}</span>
          <span>{isSeatBased ? t('seatBased') : t('licenseBased')}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('billingCycle')}</span>
          <span className="capitalize">{billingCycle || tCommon('notSet')}</span>
        </div>
        {firstPricing?.cost && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('costPerLicense')}</span>
            <span>
              {firstPricing.currency || 'EUR'} {firstPricing.cost}/
              {firstPricing.billing_cycle === 'yearly' ? t('perYear') : firstPricing.billing_cycle === 'quarterly' ? t('perQuarter') : t('perMonth')}
            </span>
          </div>
        )}
        {!isManual && provider.last_sync_at && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('lastSync')}</span>
            <span>{formatDateTimeWithSeconds(provider.last_sync_at)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Provider license card sub-component (for API-provided license info).
 */
function ProviderLicenseCard({
  provider,
  totalLicenses,
  formatDate,
  t,
}: {
  provider: OverviewTabProps['provider'];
  totalLicenses: number;
  formatDate: OverviewTabProps['formatDate'];
  t: OverviewTabProps['t'];
}) {
  const licenseInfo = provider.config!.provider_license_info!;
  const expiresAt = licenseInfo.expires_at ? new Date(licenseInfo.expires_at) : null;
  const isExpiringSoon = expiresAt && (expiresAt.getTime() - Date.now()) < 30 * 24 * 60 * 60 * 1000;
  const usedSeats = totalLicenses;
  const maxSeats = licenseInfo.max_users || 0;
  const availableSeats = maxSeats - usedSeats;
  const usagePercent = maxSeats > 0 ? (usedSeats / maxSeats) * 100 : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Key className="h-4 w-4" />
          Provider License
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('licenseType')}</span>
          <Badge variant="outline" className="capitalize">
            {licenseInfo.sku_name || t('standard')}
            {licenseInfo.is_trial && <span className="ml-1 text-amber-600">({t('trial')})</span>}
          </Badge>
        </div>

        {licenseInfo.company && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('licensedTo')}</span>
            <span>{licenseInfo.company}</span>
          </div>
        )}

        {maxSeats > 0 && (
          <>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">{t('seatUsage')}</span>
              <span className={usagePercent > 90 ? 'text-red-600 font-medium' : usagePercent > 75 ? 'text-amber-600' : ''}>
                {usedSeats} / {maxSeats} ({Math.round(usagePercent)}%)
              </span>
            </div>
            <div className="w-full bg-zinc-100 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${usagePercent > 90 ? 'bg-red-500' : usagePercent > 75 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                style={{ width: `${Math.min(usagePercent, 100)}%` }}
              />
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t('availableSeats')}</span>
              <span className={availableSeats < 10 ? 'text-amber-600 font-medium' : 'text-emerald-600'}>
                {availableSeats > 0 ? availableSeats : t('noSeatsAvailable')}
              </span>
            </div>
          </>
        )}

        {expiresAt && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('expires')}</span>
            <span className={isExpiringSoon ? 'text-red-600 font-medium' : ''}>
              {formatDate(expiresAt)}
              {isExpiringSoon && (
                <Badge variant="outline" className="ml-2 text-red-600 border-red-200 bg-red-50">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  Expiring Soon
                </Badge>
              )}
            </span>
          </div>
        )}

        {licenseInfo.licensee_email && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('licenseContact')}</span>
            <span className="text-xs">{licenseInfo.licensee_email}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
