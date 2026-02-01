'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { AppLayout } from '@/components/layout/app-layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { api, Employee, License, Provider, AdminAccountLicenseListResponse } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { CopyableText } from '@/components/ui/copy-button';
import {
  ArrowLeft,
  Key,
  User,
  Mail,
  Building2,
  Calendar,
  Loader2,
  CheckCircle2,
  XCircle,
  UserMinus,
  Trash2,
  Plus,
  DollarSign,
  Clock,
  Globe,
  Shield,
} from 'lucide-react';
import { formatMonthlyCost } from '@/lib/format';
import Link from 'next/link';
import { getLocale } from '@/lib/locale';

const REMOVABLE_PROVIDERS = ['cursor'];

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const employeeId = params.id as string;
  const t = useTranslations('licenses');
  const tCommon = useTranslations('common');
  const tEmployees = useTranslations('employees');

  const [employee, setEmployee] = useState<Employee | null>(null);
  const [licenses, setLicenses] = useState<License[]>([]);
  const [ownedAdminAccounts, setOwnedAdminAccounts] = useState<License[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Assign License Dialog
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [availableLicenses, setAvailableLicenses] = useState<License[]>([]);
  const [selectedLicenseId, setSelectedLicenseId] = useState('');
  const [loadingAvailable, setLoadingAvailable] = useState(false);

  // Remove Dialog
  const [removeDialog, setRemoveDialog] = useState<License | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Unassign Dialog
  const [unassignDialog, setUnassignDialog] = useState<License | null>(null);

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  };

  const fetchEmployee = useCallback(async () => {
    try {
      const data = await api.getEmployee(employeeId);
      setEmployee(data);
    } catch (error) {
      handleSilentError('fetchEmployee', error);
    }
  }, [employeeId]);

  const fetchLicenses = useCallback(async () => {
    try {
      const data = await api.getLicenses({ employee_id: employeeId, page_size: 100 });
      setLicenses(data.items);
    } catch (error) {
      handleSilentError('fetchLicenses', error);
    }
  }, [employeeId]);

  const fetchProviders = useCallback(async () => {
    try {
      const data = await api.getProviders();
      setProviders(data.items);
    } catch (error) {
      handleSilentError('fetchProviders', error);
    }
  }, []);

  const fetchOwnedAdminAccounts = useCallback(async () => {
    try {
      const data = await api.getAdminAccountLicenses({ owner_id: employeeId, page_size: 100 });
      setOwnedAdminAccounts(data.items);
    } catch (error) {
      handleSilentError('fetchOwnedAdminAccounts', error);
    }
  }, [employeeId]);

  useEffect(() => {
    Promise.all([fetchEmployee(), fetchLicenses(), fetchProviders(), fetchOwnedAdminAccounts()]).finally(() =>
      setLoading(false)
    );
  }, [fetchEmployee, fetchLicenses, fetchProviders, fetchOwnedAdminAccounts]);

  const openAssignDialog = async () => {
    setAssignDialogOpen(true);
    setLoadingAvailable(true);
    try {
      // Get unassigned licenses from all providers
      const data = await api.getLicenses({ unassigned: true, page_size: 200 });
      setAvailableLicenses(data.items);
    } catch (error) {
      handleSilentError('fetchAvailableLicenses', error);
    } finally {
      setLoadingAvailable(false);
    }
  };

  const handleAssignLicense = async () => {
    if (!selectedLicenseId) return;
    setActionLoading(true);
    try {
      await api.assignManualLicense(selectedLicenseId, employeeId);
      showToast('success', t('licenseAssigned'));
      setAssignDialogOpen(false);
      setSelectedLicenseId('');
      await fetchLicenses();
      await fetchEmployee();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToAssign'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnassignLicense = async () => {
    if (!unassignDialog) return;
    setActionLoading(true);
    try {
      // Check if it's a manual license
      const license = unassignDialog;
      const provider = providers.find(p => p.id === license.provider_id);
      const isManual = provider?.config?.provider_type === 'manual' || provider?.name === 'manual';

      if (isManual) {
        await api.unassignManualLicense(license.id);
      } else {
        await api.bulkUnassignLicenses([license.id]);
      }
      showToast('success', t('licenseUnassigned'));
      setUnassignDialog(null);
      await fetchLicenses();
      await fetchEmployee();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUnassign'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRemoveFromProvider = async () => {
    if (!removeDialog) return;
    setActionLoading(true);
    try {
      const result = await api.removeLicenseFromProvider(removeDialog.id);
      if (result.success) {
        showToast('success', t('removedFromProvider'));
        setRemoveDialog(null);
        await fetchLicenses();
        await fetchEmployee();
      } else {
        showToast('error', result.message);
      }
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToRemove'));
    } finally {
      setActionLoading(false);
    }
  };

  // Stats
  const licenseMonthlyCost = licenses.reduce((sum, l) => sum + (parseFloat(l.monthly_cost || '0') || 0), 0);
  const adminAccountsMonthlyCost = ownedAdminAccounts.reduce((sum, l) => sum + (parseFloat(l.monthly_cost || '0') || 0), 0);
  const totalMonthlyCost = licenseMonthlyCost + adminAccountsMonthlyCost;
  const manualProviders = providers.filter(p => p.config?.provider_type === 'manual' || p.name === 'manual');

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
        </div>
      </AppLayout>
    );
  }

  if (!employee) {
    return (
      <AppLayout>
        <div className="max-w-4xl mx-auto py-12 text-center">
          <p className="text-muted-foreground">{tEmployees('employeeNotFound')}</p>
          <Link href="/users">
            <Button variant="outline" className="mt-4">{tEmployees('backToEmployees')}</Button>
          </Link>
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

        {/* Breadcrumbs */}
        <Breadcrumbs
          items={[
            { label: tEmployees('title'), href: '/users' },
            { label: employee.full_name },
          ]}
          className="pt-2"
        />

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
              {employee.avatar ? (
                <img
                  src={employee.avatar}
                  alt=""
                  className="h-12 w-12 rounded-full object-cover"
                />
              ) : (
                <div className="h-12 w-12 rounded-full bg-zinc-100 flex items-center justify-center">
                  <span className="text-lg font-medium text-zinc-600">{employee.full_name.charAt(0)}</span>
                </div>
              )}
              <div>
                <h1 className="text-xl font-semibold">{employee.full_name}</h1>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="secondary" className={employee.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-0' : 'bg-red-50 text-red-700 border-0'}>
                    {employee.status === 'active' ? tEmployees('active') : tEmployees('offboarded')}
                  </Badge>
                  {employee.department && (
                    <>
                      <span className="text-zinc-300">•</span>
                      <span className="text-sm text-muted-foreground">{employee.department}</span>
                    </>
                  )}
                  {employee.manager && (
                    <>
                      <span className="text-zinc-300">•</span>
                      <Link
                        href={`/users/${employee.manager.id}`}
                        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {employee.manager.avatar ? (
                          <img
                            src={employee.manager.avatar}
                            alt=""
                            className="h-5 w-5 rounded-full object-cover flex-shrink-0"
                          />
                        ) : (
                          <div className="h-5 w-5 rounded-full bg-zinc-200 flex items-center justify-center flex-shrink-0">
                            <span className="text-[10px] font-medium text-zinc-600">{employee.manager.full_name.charAt(0)}</span>
                          </div>
                        )}
                        <span className="hover:underline">{employee.manager.full_name}</span>
                        <span className="text-xs text-zinc-400">({employee.manager.email})</span>
                      </Link>
                    </>
                  )}
                </div>
              </div>
            </div>
          <Button size="sm" onClick={openAssignDialog}>
            <Plus className="h-4 w-4 mr-1.5" />
            {tEmployees('assignLicense')}
          </Button>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Mail className="h-4 w-4" />
                <span className="text-xs font-medium uppercase">{tCommon('email')}</span>
              </div>
              <CopyableText className="text-sm font-medium truncate block">
                {employee.email}
              </CopyableText>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Key className="h-4 w-4" />
                <span className="text-xs font-medium uppercase">{t('title')}</span>
              </div>
              <div className="flex items-baseline gap-2">
                <p className="text-2xl font-semibold">{licenses.length}</p>
                {ownedAdminAccounts.length > 0 && (
                  <span className="text-sm text-muted-foreground">
                    + {ownedAdminAccounts.length} {tEmployees('adminAccounts')}
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <DollarSign className="h-4 w-4" />
                <span className="text-xs font-medium uppercase">{t('monthlyCost')}</span>
              </div>
              <p className="text-2xl font-semibold">EUR {totalMonthlyCost.toFixed(2)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Calendar className="h-4 w-4" />
                <span className="text-xs font-medium uppercase">{tEmployees('startDate')}</span>
              </div>
              <p className="text-sm font-medium">
                {employee.start_date ? new Date(employee.start_date).toLocaleDateString(getLocale()) : '-'}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Licenses Table */}
        <div>
          <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
            <Key className="h-4 w-4 text-muted-foreground" />
            {tEmployees('assignedLicenses')}
          </h2>
          <div className="border rounded-lg bg-white">
            {licenses.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                <Key className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <p className="text-sm">{tEmployees('noLicensesAssigned')}</p>
                <Button variant="link" size="sm" onClick={openAssignDialog} className="mt-2">
                  {tEmployees('assignALicense')}
                </Button>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-zinc-50/50">
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('provider')}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tEmployees('licenseUserId')}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('type')}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tEmployees('lastActive')}</th>
                    <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('cost')}</th>
                    <th className="text-right px-4 py-3 font-medium text-muted-foreground">{tCommon('actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {licenses.map((license) => {
                    const provider = providers.find(p => p.id === license.provider_id);
                    const isManual = provider?.config?.provider_type === 'manual' || provider?.name === 'manual';
                    const isRemovable = provider && REMOVABLE_PROVIDERS.includes(provider.name);

                    return (
                      <tr key={license.id} className="border-b last:border-0 hover:bg-zinc-50/50">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <Link href={`/providers/${license.provider_id}`} className="font-medium hover:underline">
                              {license.provider_name}
                            </Link>
                            {isManual && (
                              <span className="text-[10px] px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded">{tEmployees('manual')}</span>
                            )}
                            {isRemovable && (
                              <span className="text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded">{tEmployees('api')}</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className="text-muted-foreground font-mono text-xs">{license.external_user_id}</span>
                            {license.is_external_email && (
                              <Badge variant="outline" className="text-orange-600 border-orange-200 bg-orange-50 text-[10px] px-1.5">
                                <Globe className="h-3 w-3 mr-1" />
                                {tEmployees('external')}
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">{license.license_type || '-'}</td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {license.last_activity_at ? (
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {new Date(license.last_activity_at).toLocaleDateString(getLocale())}
                            </span>
                          ) : '-'}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-sm">
                          {license.monthly_cost ? formatMonthlyCost(license.monthly_cost, license.currency) : '-'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => setUnassignDialog(license)}
                              title={t('unassignLicense')}
                            >
                              <UserMinus className="h-3.5 w-3.5" />
                            </Button>
                            {isRemovable && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-red-600"
                                onClick={() => setRemoveDialog(license)}
                                title={t('removeFromProvider')}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Owned Admin Accounts */}
        {ownedAdminAccounts.length > 0 && (
          <div>
            <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
              <Shield className="h-4 w-4 text-muted-foreground" />
              {tEmployees('ownedAdminAccounts')}
            </h2>
            <div className="border rounded-lg bg-white">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-zinc-50/50">
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('provider')}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tEmployees('adminAccount')}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('type')}</th>
                    <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('cost')}</th>
                  </tr>
                </thead>
                <tbody>
                  {ownedAdminAccounts.map((license) => (
                    <tr key={license.id} className="border-b last:border-0 hover:bg-zinc-50/50">
                      <td className="px-4 py-3">
                        <Link href={`/providers/${license.provider_id}`} className="font-medium hover:underline">
                          {license.provider_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="text-muted-foreground font-mono text-xs">{license.external_user_id}</span>
                          {license.admin_account_name && (
                            <span className="text-xs text-zinc-500">{license.admin_account_name}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{license.license_type || '-'}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-sm">
                        {license.monthly_cost ? formatMonthlyCost(license.monthly_cost, license.currency) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {tEmployees('adminAccountsCostNote')}
            </p>
          </div>
        )}

        {/* Employee Info */}
        {employee.termination_date && (
          <Card className="border-red-200">
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-50 rounded-lg">
                  <UserMinus className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <p className="font-medium text-red-600">{tEmployees('offboarded')}</p>
                  <p className="text-sm text-muted-foreground">
                    {tEmployees('terminationDate')}: {new Date(employee.termination_date).toLocaleDateString(getLocale())}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Assign License Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{tEmployees('assignLicense')}</DialogTitle>
            <DialogDescription>
              {tEmployees('selectLicenseToAssign')}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            {loadingAvailable ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
              </div>
            ) : availableLicenses.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                {tEmployees('noUnassignedLicenses')}
              </p>
            ) : (
              <Select value={selectedLicenseId} onValueChange={setSelectedLicenseId}>
                <SelectTrigger>
                  <SelectValue placeholder={t('assignLicense')} />
                </SelectTrigger>
                <SelectContent>
                  {availableLicenses.map((lic) => (
                    <SelectItem key={lic.id} value={lic.id}>
                      {lic.provider_name} - {lic.external_user_id} {lic.license_type ? `(${lic.license_type})` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAssignDialogOpen(false)}>{tCommon('cancel')}</Button>
            <Button onClick={handleAssignLicense} disabled={!selectedLicenseId || actionLoading}>
              {actionLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              {t('confirmMatch')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Unassign Dialog */}
      <Dialog open={!!unassignDialog} onOpenChange={() => setUnassignDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{tEmployees('unassignLicense')}</DialogTitle>
            <DialogDescription>
              {tEmployees('confirmUnassign', { name: employee.full_name })}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              {tEmployees('unassignDescription')}
            </p>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setUnassignDialog(null)}>{tCommon('cancel')}</Button>
            <Button onClick={handleUnassignLicense} disabled={actionLoading}>
              {actionLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              {t('unassignLicense')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove from Provider Dialog */}
      <Dialog open={!!removeDialog} onOpenChange={() => setRemoveDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <div className="p-1.5 bg-red-100 rounded-md">
                <Trash2 className="h-4 w-4 text-red-600" />
              </div>
              {tEmployees('removeFromProviderTitle', { provider: removeDialog?.provider_name || '' })}
            </DialogTitle>
            <DialogDescription asChild>
              <div className="space-y-4 pt-2">
                <p>
                  {tEmployees('removeFromProviderQuestion', { user: removeDialog?.external_user_id || '', provider: removeDialog?.provider_name || '' })}
                </p>

                <div className="bg-zinc-50 rounded-lg p-4 space-y-3 text-sm">
                  <p className="font-medium text-foreground">{tEmployees('thisWill')}</p>
                  <ul className="space-y-2 text-muted-foreground">
                    <li className="flex items-start gap-2">
                      <span className="text-red-500 mt-0.5">-</span>
                      {tEmployees('revokeAccessTo', { provider: removeDialog?.provider_name || '' })}
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-green-500 mt-0.5">+</span>
                      {tEmployees('freeUpLicenseSeat')}
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-green-500 mt-0.5">+</span>
                      {tEmployees('saveCostPerMonth', { currency: 'EUR', amount: Number(removeDialog?.monthly_cost || 0).toFixed(2) })}
                    </li>
                  </ul>
                </div>

                <p className="text-xs text-muted-foreground">
                  {tEmployees('apiActionCannotBeUndone', { provider: removeDialog?.provider_name || '' })}
                </p>
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0 mt-4">
            <Button variant="ghost" onClick={() => setRemoveDialog(null)}>{tCommon('cancel')}</Button>
            <Button variant="destructive" onClick={handleRemoveFromProvider} disabled={actionLoading}>
              {actionLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              {t('removeFromProvider')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
