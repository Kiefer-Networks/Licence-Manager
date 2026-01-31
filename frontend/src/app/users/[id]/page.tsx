'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
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
import { api, Employee, License, Provider } from '@/lib/api';
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
} from 'lucide-react';
import { formatMonthlyCost } from '@/lib/format';
import Link from 'next/link';
import { getLocale } from '@/lib/locale';

const REMOVABLE_PROVIDERS = ['cursor'];

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const employeeId = params.id as string;

  const [employee, setEmployee] = useState<Employee | null>(null);
  const [licenses, setLicenses] = useState<License[]>([]);
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

  useEffect(() => {
    Promise.all([fetchEmployee(), fetchLicenses(), fetchProviders()]).finally(() =>
      setLoading(false)
    );
  }, [fetchEmployee, fetchLicenses, fetchProviders]);

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
      showToast('success', 'License assigned');
      setAssignDialogOpen(false);
      setSelectedLicenseId('');
      await fetchLicenses();
      await fetchEmployee();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to assign');
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
      showToast('success', 'License unassigned');
      setUnassignDialog(null);
      await fetchLicenses();
      await fetchEmployee();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to unassign');
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
        showToast('success', 'Removed from provider');
        setRemoveDialog(null);
        await fetchLicenses();
        await fetchEmployee();
      } else {
        showToast('error', result.message);
      }
    } catch (error: any) {
      showToast('error', error.message || 'Failed to remove');
    } finally {
      setActionLoading(false);
    }
  };

  // Stats
  const totalMonthlyCost = licenses.reduce((sum, l) => sum + (parseFloat(l.monthly_cost || '0') || 0), 0);
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
          <p className="text-muted-foreground">Employee not found</p>
          <Link href="/users">
            <Button variant="outline" className="mt-4">Back to Employees</Button>
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
            { label: 'Employees', href: '/users' },
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
                <div className="flex items-center gap-2 mt-0.5">
                  <Badge variant="secondary" className={employee.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-0' : 'bg-red-50 text-red-700 border-0'}>
                    {employee.status === 'active' ? 'Active' : 'Offboarded'}
                  </Badge>
                  {employee.department && (
                    <span className="text-xs text-muted-foreground">{employee.department}</span>
                  )}
                </div>
              </div>
            </div>
          <Button size="sm" onClick={openAssignDialog}>
            <Plus className="h-4 w-4 mr-1.5" />
            Assign License
          </Button>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Mail className="h-4 w-4" />
                <span className="text-xs font-medium uppercase">Email</span>
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
                <span className="text-xs font-medium uppercase">Licenses</span>
              </div>
              <p className="text-2xl font-semibold">{licenses.length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <DollarSign className="h-4 w-4" />
                <span className="text-xs font-medium uppercase">Monthly Cost</span>
              </div>
              <p className="text-2xl font-semibold">EUR {totalMonthlyCost.toFixed(2)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Calendar className="h-4 w-4" />
                <span className="text-xs font-medium uppercase">Start Date</span>
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
            Assigned Licenses
          </h2>
          <div className="border rounded-lg bg-white">
            {licenses.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                <Key className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No licenses assigned</p>
                <Button variant="link" size="sm" onClick={openAssignDialog} className="mt-2">
                  Assign a license
                </Button>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-zinc-50/50">
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Provider</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">License / User ID</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Type</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Last Active</th>
                    <th className="text-right px-4 py-3 font-medium text-muted-foreground">Cost</th>
                    <th className="text-right px-4 py-3 font-medium text-muted-foreground">Actions</th>
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
                              <span className="text-[10px] px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded">Manual</span>
                            )}
                            {isRemovable && (
                              <span className="text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded">API</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className="text-muted-foreground font-mono text-xs">{license.external_user_id}</span>
                            {license.is_external_email && (
                              <Badge variant="outline" className="text-orange-600 border-orange-200 bg-orange-50 text-[10px] px-1.5">
                                <Globe className="h-3 w-3 mr-1" />
                                External
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
                              title="Unassign"
                            >
                              <UserMinus className="h-3.5 w-3.5" />
                            </Button>
                            {isRemovable && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-red-600"
                                onClick={() => setRemoveDialog(license)}
                                title="Remove from Provider"
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

        {/* Employee Info */}
        {employee.termination_date && (
          <Card className="border-red-200">
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-50 rounded-lg">
                  <UserMinus className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <p className="font-medium text-red-600">Offboarded</p>
                  <p className="text-sm text-muted-foreground">
                    Termination date: {new Date(employee.termination_date).toLocaleDateString(getLocale())}
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
            <DialogTitle>Assign License</DialogTitle>
            <DialogDescription>
              Select an unassigned license to assign to {employee.full_name}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            {loadingAvailable ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
              </div>
            ) : availableLicenses.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No unassigned licenses available
              </p>
            ) : (
              <Select value={selectedLicenseId} onValueChange={setSelectedLicenseId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a license..." />
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
            <Button variant="ghost" onClick={() => setAssignDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAssignLicense} disabled={!selectedLicenseId || actionLoading}>
              {actionLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Assign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Unassign Dialog */}
      <Dialog open={!!unassignDialog} onOpenChange={() => setUnassignDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Unassign License</DialogTitle>
            <DialogDescription>
              Remove <strong>{unassignDialog?.provider_name}</strong> license from {employee.full_name}?
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              The license will be marked as unassigned and can be reassigned to another employee.
              The user will keep access in the provider system until removed.
            </p>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setUnassignDialog(null)}>Cancel</Button>
            <Button onClick={handleUnassignLicense} disabled={actionLoading}>
              {actionLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Unassign
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
              Remove from {removeDialog?.provider_name}
            </DialogTitle>
            <DialogDescription asChild>
              <div className="space-y-4 pt-2">
                <p>
                  Remove <span className="font-medium text-foreground">{removeDialog?.external_user_id}</span> from {removeDialog?.provider_name}?
                </p>

                <div className="bg-zinc-50 rounded-lg p-4 space-y-3 text-sm">
                  <p className="font-medium text-foreground">This will:</p>
                  <ul className="space-y-2 text-muted-foreground">
                    <li className="flex items-start gap-2">
                      <span className="text-red-500 mt-0.5">-</span>
                      Immediately revoke access to {removeDialog?.provider_name}
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-green-500 mt-0.5">+</span>
                      Free up the license seat
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-green-500 mt-0.5">+</span>
                      Save EUR {Number(removeDialog?.monthly_cost || 0).toFixed(2)} per month
                    </li>
                  </ul>
                </div>

                <p className="text-xs text-muted-foreground">
                  This action is executed via the {removeDialog?.provider_name} API and cannot be undone.
                </p>
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0 mt-4">
            <Button variant="ghost" onClick={() => setRemoveDialog(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleRemoveFromProvider} disabled={actionLoading}>
              {actionLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Remove License
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
