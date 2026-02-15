'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { AppLayout } from '@/components/layout/app-layout';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ExpiringLicense, CancelledLicense } from '@/lib/api';
import { SkeletonCard } from '@/components/ui/skeleton';
import {
  Clock,
  XCircle,
  CheckCircle2,
  RefreshCw,
  Ban,
  ShoppingCart,
} from 'lucide-react';
import { CancellationDialog } from '@/components/licenses/CancellationDialog';
import { RenewDialog } from '@/components/licenses/RenewDialog';
import { useLocale } from '@/components/locale-provider';
import { useLifecycle } from '@/hooks/use-lifecycle';

export default function LifecyclePage() {
  const t = useTranslations('lifecycle');
  const tLicenses = useTranslations('licenses');
  const tProviders = useTranslations('providers');
  const tCommon = useTranslations('common');
  const { formatDate, formatCurrency } = useLocale();

  const {
    overview,
    needsReorderLicenses,
    loading,
    toast,
    activeTab,
    setActiveTab,
    cancelDialogOpen,
    setCancelDialogOpen,
    renewDialogOpen,
    setRenewDialogOpen,
    selectedLicense,
    setSelectedLicense,
    handleCancel,
    handleRenew,
    handleToggleNeedsReorder,
  } = useLifecycle(t);

  if (loading) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto space-y-6">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Toast */}
        {toast && (
          <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'success' ? 'bg-zinc-900 text-white' : 'bg-red-600 text-white'
          }`}>
            {toast.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            {toast.text}
          </div>
        )}

        {/* Header */}
        <div className="pt-2">
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            {t('subtitle')}
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('active')}</p>
                  <p className="text-2xl font-semibold mt-1 tabular-nums text-emerald-600">
                    {overview?.total_active || 0}
                  </p>
                </div>
                <CheckCircle2 className="h-8 w-8 text-emerald-200" />
              </div>
            </CardContent>
          </Card>

          <Card className={overview?.total_expiring_soon ? 'border-amber-200 bg-amber-50/30' : ''}>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('expiringSoon')}</p>
                  <p className={`text-2xl font-semibold mt-1 tabular-nums ${overview?.total_expiring_soon ? 'text-amber-600' : ''}`}>
                    {overview?.total_expiring_soon || 0}
                  </p>
                </div>
                <Clock className="h-8 w-8 text-amber-200" />
              </div>
            </CardContent>
          </Card>

          <Card className={overview?.total_expired ? 'border-red-200 bg-red-50/30' : ''}>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('expired')}</p>
                  <p className={`text-2xl font-semibold mt-1 tabular-nums ${overview?.total_expired ? 'text-red-600' : ''}`}>
                    {overview?.total_expired || 0}
                  </p>
                </div>
                <XCircle className="h-8 w-8 text-red-200" />
              </div>
            </CardContent>
          </Card>

          <Card className={overview?.total_cancelled ? 'border-zinc-300' : ''}>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('cancelled')}</p>
                  <p className="text-2xl font-semibold mt-1 tabular-nums">
                    {overview?.total_cancelled || 0}
                  </p>
                </div>
                <Ban className="h-8 w-8 text-zinc-200" />
              </div>
            </CardContent>
          </Card>

          <Card className={overview?.total_needs_reorder ? 'border-blue-200 bg-blue-50/30' : ''}>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('needsReorder')}</p>
                  <p className={`text-2xl font-semibold mt-1 tabular-nums ${overview?.total_needs_reorder ? 'text-blue-600' : ''}`}>
                    {overview?.total_needs_reorder || 0}
                  </p>
                </div>
                <ShoppingCart className="h-8 w-8 text-blue-200" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="expiring" className="gap-1.5">
              <Clock className="h-4 w-4" />
              {t('expiringLicenses')}
              {(overview?.total_expiring_soon || 0) > 0 && (
                <Badge variant="secondary" className="ml-1 bg-amber-100 text-amber-700">
                  {overview?.total_expiring_soon}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="cancelled" className="gap-1.5">
              <Ban className="h-4 w-4" />
              {t('cancelled')}
              {(overview?.total_cancelled || 0) > 0 && (
                <Badge variant="secondary" className="ml-1">
                  {overview?.total_cancelled}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="reorder" className="gap-1.5">
              <ShoppingCart className="h-4 w-4" />
              {t('needsReorder')}
              {needsReorderLicenses.length > 0 && (
                <Badge variant="secondary" className="ml-1 bg-blue-100 text-blue-700">
                  {needsReorderLicenses.length}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          {/* Expiring Tab */}
          <TabsContent value="expiring" className="mt-4">
            {overview?.expiring_licenses && overview.expiring_licenses.length > 0 ? (
              <div className="border rounded-lg bg-white overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-zinc-50/50">
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tLicenses('license')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tProviders('provider')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('expires')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('daysLeft')}</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">{tLicenses('cost')}</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">{tCommon('actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.expiring_licenses.map((license) => (
                      <tr key={license.license_id} className="border-b last:border-0 hover:bg-zinc-50/50">
                        <td className="px-4 py-3">
                          <div>
                            <p className="font-medium">{license.external_user_id}</p>
                            {license.employee_name && (
                              <p className="text-xs text-muted-foreground">{license.employee_name}</p>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Link href={`/providers/${license.provider_id}`} className="hover:underline">
                            {license.provider_name}
                          </Link>
                          {license.license_type && (
                            <p className="text-xs text-muted-foreground">{license.license_type}</p>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {formatDate(license.expires_at)}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={license.days_until_expiry <= 7 ? 'destructive' : license.days_until_expiry <= 30 ? 'default' : 'secondary'}
                            className={license.days_until_expiry <= 7 ? '' : license.days_until_expiry <= 30 ? 'bg-amber-100 text-amber-700 hover:bg-amber-100' : ''}
                          >
                            {license.days_until_expiry} {t('days')}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums">
                          {license.monthly_cost ? formatCurrency(license.monthly_cost) : '-'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedLicense(license);
                                setRenewDialogOpen(true);
                              }}
                              title={t('renewLicense')}
                            >
                              <RefreshCw className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleNeedsReorder(license)}
                              title={license.needs_reorder ? t('removeFromReorder') : t('markForReorder')}
                              className={license.needs_reorder ? 'text-blue-600' : ''}
                            >
                              <ShoppingCart className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedLicense(license);
                                setCancelDialogOpen(true);
                              }}
                              title={t('cancelLicense')}
                            >
                              <Ban className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground border rounded-lg bg-white">
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-30 text-emerald-500" />
                <p className="text-sm">{t('noExpiringLicenses')}</p>
              </div>
            )}
          </TabsContent>

          {/* Cancelled Tab */}
          <TabsContent value="cancelled" className="mt-4">
            {overview?.cancelled_licenses && overview.cancelled_licenses.length > 0 ? (
              <div className="border rounded-lg bg-white overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-zinc-50/50">
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tLicenses('license')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tProviders('provider')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('cancelled')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('effectiveDate')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('reason')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('status')}</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">{tCommon('actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.cancelled_licenses.map((license) => (
                      <tr key={license.license_id} className="border-b last:border-0 hover:bg-zinc-50/50">
                        <td className="px-4 py-3">
                          <div>
                            <p className="font-medium">{license.external_user_id}</p>
                            {license.employee_name && (
                              <p className="text-xs text-muted-foreground">{license.employee_name}</p>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Link href={`/providers/${license.provider_id}`} className="hover:underline">
                            {license.provider_name}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-xs">
                          {formatDate(license.cancelled_at)}
                          {license.cancelled_by_name && (
                            <p className="text-muted-foreground">{t('cancelledBy')} {license.cancelled_by_name}</p>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {formatDate(license.cancellation_effective_date)}
                        </td>
                        <td className="px-4 py-3 text-xs text-muted-foreground max-w-[200px] truncate">
                          {license.cancellation_reason || '-'}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={license.is_effective ? 'secondary' : 'outline'}>
                            {license.is_effective ? t('effective') : t('pending')}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {!license.is_effective && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedLicense(license);
                                setRenewDialogOpen(true);
                              }}
                              title={t('undoCancellation')}
                            >
                              <RefreshCw className="h-4 w-4" />
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground border rounded-lg bg-white">
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-30 text-emerald-500" />
                <p className="text-sm">{t('noCancelledLicenses')}</p>
              </div>
            )}
          </TabsContent>

          {/* Needs Reorder Tab */}
          <TabsContent value="reorder" className="mt-4">
            {needsReorderLicenses.length > 0 ? (
              <div className="border rounded-lg bg-white overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-zinc-50/50">
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tLicenses('license')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tProviders('provider')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('expires')}</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">{tLicenses('cost')}</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">{tCommon('actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {needsReorderLicenses.map((license) => (
                      <tr key={license.license_id} className="border-b last:border-0 hover:bg-zinc-50/50">
                        <td className="px-4 py-3">
                          <div>
                            <p className="font-medium">{license.external_user_id}</p>
                            {license.employee_name && (
                              <p className="text-xs text-muted-foreground">{license.employee_name}</p>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Link href={`/providers/${license.provider_id}`} className="hover:underline">
                            {license.provider_name}
                          </Link>
                        </td>
                        <td className="px-4 py-3">
                          {license.expires_at ? formatDate(license.expires_at) : '-'}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums">
                          {license.monthly_cost ? formatCurrency(license.monthly_cost) : '-'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedLicense(license);
                                setRenewDialogOpen(true);
                              }}
                              title={t('renewLicense')}
                            >
                              <RefreshCw className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleNeedsReorder(license)}
                              title={t('removeFromReorder')}
                              className="text-blue-600"
                            >
                              <ShoppingCart className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground border rounded-lg bg-white">
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-30 text-emerald-500" />
                <p className="text-sm">{t('noReorderLicenses')}</p>
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Dialogs */}
        <CancellationDialog
          open={cancelDialogOpen}
          onOpenChange={setCancelDialogOpen}
          onConfirm={handleCancel}
          title={t('cancelLicense')}
          description={t('cancelDescription')}
          itemName={selectedLicense?.external_user_id || ''}
        />

        <RenewDialog
          open={renewDialogOpen}
          onOpenChange={setRenewDialogOpen}
          onConfirm={handleRenew}
          title={t('renewLicense')}
          description={t('renewDescription')}
          itemName={selectedLicense?.external_user_id || ''}
          currentExpiration={(selectedLicense as ExpiringLicense)?.expires_at}
          hasPendingCancellation={!!(selectedLicense as CancelledLicense)?.cancelled_at}
        />
      </div>
    </AppLayout>
  );
}
