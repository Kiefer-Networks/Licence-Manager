'use client';

import { useEffect, useState } from 'react';
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
import { api, DashboardData, PaymentMethod } from '@/lib/api';
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

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [departments, setDepartments] = useState<string[]>([]);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [expiringPaymentMethods, setExpiringPaymentMethods] = useState<PaymentMethod[]>([]);

  useEffect(() => {
    api.getDepartments().then(setDepartments).catch((e) => handleSilentError('getDepartments', e));
    api.getPaymentMethods().then((data) => {
      setExpiringPaymentMethods(data.items.filter((m) => m.is_expiring));
    }).catch((e) => handleSilentError('getPaymentMethods', e));
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
      showToast(result.success ? 'success' : 'error', result.success ? 'Sync completed' : 'Sync failed');
    } catch (error) {
      showToast('error', 'Sync failed');
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
                  <p className="font-medium text-amber-800">Payment Method Expiring Soon</p>
                </div>
                <p className="text-sm text-amber-700 mt-0.5">
                  {expiringPaymentMethods.length === 1
                    ? `${expiringPaymentMethods[0].name} expires ${expiringPaymentMethods[0].days_until_expiry !== null && expiringPaymentMethods[0].days_until_expiry !== undefined && expiringPaymentMethods[0].days_until_expiry > 0 ? `in ${expiringPaymentMethods[0].days_until_expiry} days` : 'soon'}`
                    : `${expiringPaymentMethods.length} payment methods are expiring soon`}
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-amber-400 flex-shrink-0" />
            </div>
          </Link>
        )}

        {/* Header */}
        <div className="flex items-center justify-between pt-2">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground text-sm mt-0.5">License management overview</p>
          </div>
          <div className="flex items-center gap-3">
            <Select value={selectedDepartment} onValueChange={setSelectedDepartment}>
              <SelectTrigger className="w-48 h-8 bg-zinc-50 border-zinc-200 text-xs">
                <Building2 className="h-3.5 w-3.5 mr-2 text-zinc-400" />
                <SelectValue placeholder="Department" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {departments.map((dept) => (
                  <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={handleSync} disabled={syncing} variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
              <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
              Sync All
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
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Employees</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">{dashboard?.total_employees || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      <span className="text-emerald-600">{dashboard?.active_employees || 0} active</span>
                      {(dashboard?.offboarded_employees || 0) > 0 && (
                        <span className="text-zinc-400"> · {dashboard?.offboarded_employees} offboarded</span>
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
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Total Licenses</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">{totalLicenses}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Across {licenseProviders.length} provider{licenseProviders.length !== 1 ? 's' : ''}
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
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Monthly Cost</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">
                      EUR {totalCost.toLocaleString('de-DE', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      All active licenses
                    </p>
                  </div>
                  <div className="h-10 w-10 rounded-lg bg-emerald-50 flex items-center justify-center">
                    <Wallet className="h-5 w-5 text-emerald-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href="/settings">
            <Card className="hover:border-zinc-300 transition-colors cursor-pointer h-full">
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">HRIS Status</p>
                    <div className="flex items-center gap-2 mt-1">
                      {hrisProviders.length > 0 ? (
                        <>
                          <span className="h-3 w-3 rounded-full bg-emerald-500" />
                          <span className="text-lg font-semibold text-emerald-600">Connected</span>
                        </>
                      ) : (
                        <>
                          <span className="h-3 w-3 rounded-full bg-zinc-300" />
                          <span className="text-lg font-semibold text-zinc-400">Not connected</span>
                        </>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {hrisProviders.length > 0 ? hrisProviders[0].display_name : 'Setup required'}
                    </p>
                  </div>
                  <div className="h-10 w-10 rounded-lg bg-purple-50 flex items-center justify-center">
                    <Building2 className="h-5 w-5 text-purple-600" />
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
                      <p className="font-medium">Unassigned Licenses</p>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        Licenses not linked to any employee
                      </p>
                      {unassignedCount > 0 && (
                        <div className="flex items-center gap-4 mt-3">
                          <div>
                            <p className="text-2xl font-semibold text-amber-600">{unassignedCount}</p>
                            <p className="text-xs text-muted-foreground">licenses</p>
                          </div>
                          <div className="h-8 w-px bg-zinc-200" />
                          <div>
                            <p className="text-2xl font-semibold text-emerald-600">
                              EUR {potentialSavings.toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                            </p>
                            <p className="text-xs text-muted-foreground">potential savings/mo</p>
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
                    <span className="text-sm font-medium">All licenses assigned</span>
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
                      <p className="font-medium">Offboarded with Licenses</p>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        Former employees still consuming licenses
                      </p>
                      {(dashboard?.recent_offboardings?.length || 0) > 0 && (
                        <div className="mt-3">
                          <p className="text-2xl font-semibold text-red-600">{dashboard?.recent_offboardings?.length || 0}</p>
                          <p className="text-xs text-muted-foreground">employees need attention</p>
                        </div>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-zinc-300" />
                </div>
                {(dashboard?.recent_offboardings?.length || 0) === 0 && (
                  <div className="flex items-center gap-2 mt-3 text-emerald-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="text-sm font-medium">No pending offboardings</span>
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
                      <p className="font-medium">External Licenses</p>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        Non-company email addresses
                      </p>
                      {externalCount > 0 && (
                        <div className="mt-3">
                          <p className="text-2xl font-semibold text-orange-600">{externalCount}</p>
                          <p className="text-xs text-muted-foreground">external licenses</p>
                        </div>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-zinc-300" />
                </div>
                {externalCount === 0 && (
                  <div className="flex items-center gap-2 mt-3 text-emerald-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="text-sm font-medium">No external licenses</span>
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
                License Providers
              </h2>
              <Link href="/settings" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
                Manage
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
                            {provider.total_licenses} license{provider.total_licenses !== 1 ? 's' : ''}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-sm tabular-nums">
                          EUR {Number(provider.monthly_cost || 0).toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                        </p>
                        <p className="text-xs text-muted-foreground flex items-center justify-end gap-1">
                          <Clock className="h-3 w-3" />
                          {provider.last_sync_at
                            ? new Date(provider.last_sync_at).toLocaleDateString('de-DE')
                            : 'Never'}
                        </p>
                      </div>
                    </div>
                  </Link>
                ))
              ) : (
                <div className="text-center py-12 text-muted-foreground border rounded-lg">
                  <Key className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No providers configured</p>
                  <Link href="/settings" className="text-xs text-primary hover:underline">
                    Add provider
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
                Recent Offboardings
                {(dashboard?.recent_offboardings?.length || 0) > 0 && (
                  <Badge variant="secondary" className="ml-1 text-xs bg-red-50 text-red-700 border-0">
                    {dashboard?.recent_offboardings?.length}
                  </Badge>
                )}
              </h2>
              <Link href="/reports" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
                View all
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
                        {employee.pending_licenses} license{employee.pending_licenses !== 1 ? 's' : ''}
                      </Badge>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground border rounded-lg">
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-30 text-emerald-500" />
                <p className="text-sm">No offboarded employees with licenses</p>
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
                Unassigned License Samples
              </h2>
              <Link href="/licenses?unassigned=true" className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">
                View all {unassignedCount}
                <ChevronRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="border rounded-lg bg-white overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-zinc-50/50">
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">User</th>
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Provider</th>
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Type</th>
                    <th className="text-right px-4 py-2.5 font-medium text-muted-foreground">Cost</th>
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
