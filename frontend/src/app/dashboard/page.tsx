'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { AppLayout } from '@/components/layout/app-layout';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { api, DashboardData, PaymentMethod, LicenseLifecycleOverview } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import { SkeletonDashboard } from '@/components/ui/skeleton';
import {
  Users,
  Key,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  UserMinus,
  AlertTriangle,
  Building2,
  Wallet,
  ChevronRight,
  Package,
  CreditCard,
  Globe,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { getLocale } from '@/lib/locale';

export default function DashboardPage() {
  const t = useTranslations('dashboard');
  const tCommon = useTranslations('common');
  const tLicenses = useTranslations('licenses');
  const tProviders = useTranslations('providers');
  const tEmployees = useTranslations('employees');

  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [departments, setDepartments] = useState<string[]>([]);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [expiringPaymentMethods, setExpiringPaymentMethods] = useState<PaymentMethod[]>([]);
  const [lifecycleOverview, setLifecycleOverview] = useState<LicenseLifecycleOverview | null>(null);

  useEffect(() => {
    api.getDepartments().then(setDepartments).catch((e) => handleSilentError('getDepartments', e));
    api.getPaymentMethods().then((data) => {
      setExpiringPaymentMethods(data.items.filter((m) => m.is_expiring));
    }).catch((e) => handleSilentError('getPaymentMethods', e));
    api.getLicenseLifecycleOverview().then(setLifecycleOverview).catch((e) => handleSilentError('getLifecycleOverview', e));
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [selectedDepartment]);

  async function fetchDashboard() {
    try {
      const dept = selectedDepartment !== 'all' ? selectedDepartment : undefined;
      const data = await api.getDashboard(dept);
      setDashboard(data);
    } catch (error) {
      handleSilentError('fetchDashboard', error);
    } finally {
      setLoading(false);
    }
  }

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 4000);
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await api.triggerSync();
      await fetchDashboard();
      showToast(result.success ? 'success' : 'error', result.success ? tProviders('syncSuccess') : tProviders('syncFailed'));
    } catch {
      showToast('error', tProviders('syncFailed'));
    } finally {
      setSyncing(false);
    }
  };

  const hrisProviders = dashboard?.providers.filter((p) => p.name === 'hibob') || [];
  const licenseProviders = dashboard?.providers
    .filter((p) => p.name !== 'hibob')
    .sort((a, b) => a.display_name.localeCompare(b.display_name)) || [];

  const totalLicenses = dashboard?.total_licenses || 0;
  const unassignedCount = dashboard?.unassigned_licenses || 0;
  const externalCount = dashboard?.external_licenses || 0;
  const potentialSavings = Number(dashboard?.potential_savings || 0);
  const totalCost = Number(dashboard?.total_monthly_cost || 0);

  if (loading) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto">
          <SkeletonDashboard />
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

        {/* Expiring Licenses Warning */}
        {lifecycleOverview && lifecycleOverview.total_expiring_soon > 0 && (
          <Link href="/lifecycle">
            <div className="border border-amber-200 bg-amber-50 rounded-lg p-4 flex items-center gap-3 hover:bg-amber-100 transition-colors">
              <div className="h-10 w-10 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
                <Clock className="h-5 w-5 text-amber-600" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  <p className="font-medium text-amber-800">{t('expiringLicenses')}</p>
                </div>
                <p className="text-sm text-amber-700 mt-0.5">
                  {lifecycleOverview.total_expiring_soon} {tLicenses('license')}{lifecycleOverview.total_expiring_soon !== 1 ? 's' : ''}
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-amber-400 flex-shrink-0" />
            </div>
          </Link>
        )}

        {/* Expiring Payment Methods Warning */}
        {expiringPaymentMethods.length > 0 && (
          <Link href="/settings">
            <div className="border border-amber-200 bg-amber-50 rounded-lg p-4 flex items-center gap-3 hover:bg-amber-100 transition-colors">
              <div className="h-10 w-10 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
                <CreditCard className="h-5 w-5 text-amber-600" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  <p className="font-medium text-amber-800">{tCommon('warning')}</p>
                </div>
                <p className="text-sm text-amber-700 mt-0.5">
                  {expiringPaymentMethods.length === 1
                    ? expiringPaymentMethods[0].name
                    : t('paymentMethodsExpiring', { count: expiringPaymentMethods.length })}
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-amber-400 flex-shrink-0" />
            </div>
          </Link>
        )}

        {/* Header */}
        <div className="flex items-center justify-between pt-2">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
            <p className="text-muted-foreground text-sm mt-0.5">{t('overview')}</p>
          </div>
          <div className="flex items-center gap-3">
            <Select value={selectedDepartment} onValueChange={setSelectedDepartment}>
              <SelectTrigger className="w-48 h-8 bg-zinc-50 border-zinc-200 text-xs">
                <Building2 className="h-3.5 w-3.5 mr-2 text-zinc-400" />
                <SelectValue placeholder={tEmployees('department')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{tCommon('all')} {tEmployees('department')}</SelectItem>
                {departments.map((dept) => (
                  <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={handleSync} disabled={syncing} variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
              <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
              {t('syncAll')}
            </Button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Link href="/users">
            <Card className="hover:border-zinc-300 transition-colors cursor-pointer h-full">
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{tEmployees('title')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">{dashboard?.total_employees || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      <span className="text-emerald-600">{dashboard?.active_employees || 0} {tEmployees('active').toLowerCase()}</span>
                      {(dashboard?.offboarded_employees || 0) > 0 && (
                        <span className="text-zinc-400"> · {dashboard?.offboarded_employees} {tEmployees('offboarded').toLowerCase()}</span>
                      )}
                    </p>
                  </div>
                  <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
                    <Users className="h-5 w-5 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href="/licenses">
            <Card className="hover:border-zinc-300 transition-colors cursor-pointer h-full">
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('totalLicenses')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">{totalLicenses}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {licenseProviders.length} {tProviders('provider')}{licenseProviders.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <div className="h-10 w-10 rounded-lg bg-zinc-100 flex items-center justify-center">
                    <Key className="h-5 w-5 text-zinc-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href="/reports">
            <Card className="hover:border-zinc-300 transition-colors cursor-pointer h-full">
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('monthlyCost')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">
                      EUR {totalCost.toLocaleString(getLocale(), { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {tLicenses('allLicenses')}
                    </p>
                  </div>
                  <div className="h-10 w-10 rounded-lg bg-emerald-50 flex items-center justify-center">
                    <Wallet className="h-5 w-5 text-emerald-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href={hrisProviders.length > 0 ? "/providers" : "/settings"}>
            <Card className="hover:border-zinc-300 transition-colors cursor-pointer h-full">
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      {hrisProviders.length > 0 ? t('hibob') : t('hris')}
                    </p>
                    {hrisProviders.length > 0 ? (
                      <>
                        <p className="text-3xl font-semibold mt-1 tabular-nums">{dashboard?.active_employees || 0}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          <span className="text-emerald-600">{tEmployees('active')}</span>
                        </p>
                      </>
                    ) : (
                      <>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="h-3 w-3 rounded-full bg-zinc-300" />
                          <span className="text-lg font-semibold text-zinc-400">{tCommon('disabled')}</span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">{tCommon('required')}</p>
                      </>
                    )}
                  </div>
                  <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${hrisProviders.length > 0 ? 'bg-purple-50' : 'bg-zinc-100'}`}>
                    <Building2 className={`h-5 w-5 ${hrisProviders.length > 0 ? 'text-purple-600' : 'text-zinc-400'}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>

        {/* Alert Cards */}
        <div className="grid lg:grid-cols-3 gap-4">
          {/* Unassigned Licenses */}
          <Link href="/licenses">
            <Card className={`hover:border-zinc-300 transition-colors cursor-pointer h-full ${unassignedCount > 0 ? 'border-amber-200 bg-amber-50/30' : ''}`}>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${unassignedCount > 0 ? 'bg-amber-100' : 'bg-zinc-100'}`}>
                      <Package className={`h-5 w-5 ${unassignedCount > 0 ? 'text-amber-600' : 'text-zinc-400'}`} />
                    </div>
                    <div>
                      <p className="font-medium">{t('unassignedLicenses')}</p>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        {tLicenses('unassigned')}
                      </p>
                      {unassignedCount > 0 && (
                        <div className="flex items-center gap-4 mt-3">
                          <div>
                            <p className="text-2xl font-semibold text-amber-600">{unassignedCount}</p>
                            <p className="text-xs text-muted-foreground">{tLicenses('license')}s</p>
                          </div>
                          <div className="h-8 w-px bg-zinc-200" />
                          <div>
                            <p className="text-2xl font-semibold text-emerald-600">
                              EUR {potentialSavings.toLocaleString(getLocale(), { minimumFractionDigits: 0 })}
                            </p>
                            <p className="text-xs text-muted-foreground">{t('perMonth')}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-zinc-300" />
                </div>
                {unassignedCount === 0 && (
                  <div className="flex items-center gap-2 mt-3 text-emerald-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="text-sm font-medium">{tLicenses('assigned')}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </Link>

          {/* Offboarded with Licenses */}
          <Link href="/reports">
            <Card className={`hover:border-zinc-300 transition-colors cursor-pointer h-full ${(dashboard?.recent_offboardings?.length || 0) > 0 ? 'border-red-200 bg-red-50/30' : ''}`}>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${(dashboard?.recent_offboardings?.length || 0) > 0 ? 'bg-red-100' : 'bg-zinc-100'}`}>
                      <UserMinus className={`h-5 w-5 ${(dashboard?.recent_offboardings?.length || 0) > 0 ? 'text-red-600' : 'text-zinc-400'}`} />
                    </div>
                    <div>
                      <p className="font-medium">{t('offboardedEmployees')}</p>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        {tLicenses('license')}s
                      </p>
                      {(dashboard?.recent_offboardings?.length || 0) > 0 && (
                        <div className="mt-3">
                          <p className="text-2xl font-semibold text-red-600">{dashboard?.recent_offboardings?.length || 0}</p>
                          <p className="text-xs text-muted-foreground">{tEmployees('employee')}s</p>
                        </div>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-zinc-300" />
                </div>
                {(dashboard?.recent_offboardings?.length || 0) === 0 && (
                  <div className="flex items-center gap-2 mt-3 text-emerald-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="text-sm font-medium">{tCommon('noResults')}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </Link>

          {/* External Licenses */}
          <Link href="/licenses">
            <Card className={`hover:border-zinc-300 transition-colors cursor-pointer h-full ${externalCount > 0 ? 'border-orange-200 bg-orange-50/30' : ''}`}>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${externalCount > 0 ? 'bg-orange-100' : 'bg-zinc-100'}`}>
                      <Globe className={`h-5 w-5 ${externalCount > 0 ? 'text-orange-600' : 'text-zinc-400'}`} />
                    </div>
                    <div>
                      <p className="font-medium">{tLicenses('external')}</p>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        {tLicenses('license')}s
                      </p>
                      {externalCount > 0 && (
                        <div className="mt-3">
                          <p className="text-2xl font-semibold text-orange-600">{externalCount}</p>
                          <p className="text-xs text-muted-foreground">{tLicenses('external').toLowerCase()}</p>
                        </div>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-zinc-300" />
                </div>
                {externalCount === 0 && (
                  <div className="flex items-center gap-2 mt-3 text-emerald-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="text-sm font-medium">{tCommon('noResults')}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </Link>
        </div>

        {/* Providers and Recent Activity */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Providers List */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium flex items-center gap-2">
                <Key className="h-4 w-4 text-muted-foreground" />
                {tProviders('title')}
              </h2>
              <Link href="/settings" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
                {tCommon('edit')}
              </Link>
            </div>
            <div className="space-y-2">
              {licenseProviders.length > 0 ? (
                licenseProviders.map((provider) => (
                  <Link key={provider.id} href={`/providers/${provider.id}`}>
                    <div className="flex items-center justify-between p-4 rounded-lg border bg-white hover:border-zinc-300 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-lg bg-zinc-100 flex items-center justify-center">
                          <Key className="h-4 w-4 text-zinc-600" />
                        </div>
                        <div>
                          <p className="font-medium text-sm">{provider.display_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {provider.total_licenses} {tLicenses('license')}{provider.total_licenses !== 1 ? 's' : ''}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-sm tabular-nums">
                          EUR {Number(provider.monthly_cost || 0).toLocaleString(getLocale(), { minimumFractionDigits: 2 })}
                        </p>
                        <p className="text-xs text-muted-foreground flex items-center justify-end gap-1">
                          <Clock className="h-3 w-3" />
                          {provider.last_sync_at
                            ? new Date(provider.last_sync_at).toLocaleDateString(getLocale())
                            : tCommon('none')}
                        </p>
                      </div>
                    </div>
                  </Link>
                ))
              ) : (
                <div className="text-center py-12 text-muted-foreground border rounded-lg">
                  <Key className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">{tCommon('noData')}</p>
                  <Link href="/settings" className="text-xs text-primary hover:underline">
                    {tProviders('addProvider')}
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Recent Offboardings / Activity */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium flex items-center gap-2">
                <UserMinus className="h-4 w-4 text-muted-foreground" />
                {t('offboardedEmployees')}
                {(dashboard?.recent_offboardings?.length || 0) > 0 && (
                  <Badge variant="secondary" className="ml-1 text-xs bg-red-50 text-red-700 border-0">
                    {dashboard?.recent_offboardings?.length}
                  </Badge>
                )}
              </h2>
              <Link href="/reports" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
                {tCommon('view')}
              </Link>
            </div>
            {dashboard?.recent_offboardings && dashboard.recent_offboardings.length > 0 ? (
              <div className="space-y-2">
                {dashboard.recent_offboardings.slice(0, 4).map((employee) => (
                  <Link key={employee.employee_id} href={`/users/${employee.employee_id}`}>
                    <div className="flex items-center justify-between p-3 rounded-lg border bg-white hover:border-zinc-300 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-zinc-100 flex items-center justify-center">
                          <span className="text-xs font-medium text-zinc-600">
                            {employee.employee_name.charAt(0)}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-sm">{employee.employee_name}</p>
                          <p className="text-xs text-muted-foreground">{employee.employee_email}</p>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {employee.pending_licenses} {tLicenses('license')}{employee.pending_licenses !== 1 ? 's' : ''}
                      </Badge>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground border rounded-lg">
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-30 text-emerald-500" />
                <p className="text-sm">{tCommon('noResults')}</p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions / Samples */}
        {dashboard?.unassigned_license_samples && dashboard.unassigned_license_samples.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                {t('unassignedLicenses')}
              </h2>
              <Link href="/licenses?unassigned=true" className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">
                {tCommon('view')} {unassignedCount}
                <ChevronRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="border rounded-lg bg-white overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-zinc-50/50">
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">{tCommon('user')}</th>
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">{tProviders('provider')}</th>
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">{tCommon('type')}</th>
                    <th className="text-right px-4 py-2.5 font-medium text-muted-foreground">{tLicenses('cost')}</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.unassigned_license_samples.slice(0, 5).map((license) => (
                    <tr key={license.id} className="border-b last:border-0 hover:bg-zinc-50/50">
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <div className="h-6 w-6 rounded-full bg-zinc-100 flex items-center justify-center">
                            <span className="text-xs font-medium text-zinc-600">
                              {license.external_user_id.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <span className="truncate max-w-[200px]">{license.external_user_id}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-muted-foreground">{license.provider_name}</td>
                      <td className="px-4 py-2.5 text-muted-foreground">{license.license_type || '-'}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">
                        EUR {Number(license.monthly_cost || 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
