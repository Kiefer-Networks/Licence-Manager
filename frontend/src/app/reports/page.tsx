'use client';

import { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/app-layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { api, InactiveLicenseReport, OffboardingReport, CostReport, ExternalUsersReport } from '@/lib/api';
import { Clock, UserMinus, Wallet, Loader2, AlertCircle, Building2, AlertTriangle, Globe, Skull } from 'lucide-react';
import Link from 'next/link';

export default function ReportsPage() {
  const [inactiveReport, setInactiveReport] = useState<InactiveLicenseReport | null>(null);
  const [offboardingReport, setOffboardingReport] = useState<OffboardingReport | null>(null);
  const [costReport, setCostReport] = useState<CostReport | null>(null);
  const [externalUsersReport, setExternalUsersReport] = useState<ExternalUsersReport | null>(null);
  const [departments, setDepartments] = useState<string[]>([]);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  // Load departments once
  useEffect(() => {
    api.getDepartments().then(setDepartments).catch(console.error);
  }, []);

  // Load reports when department changes
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const dept = selectedDepartment !== 'all' ? selectedDepartment : undefined;

    Promise.all([
      api.getInactiveLicenseReport(30, dept),
      api.getOffboardingReport(dept),
      api.getCostReport(undefined, undefined, dept),
      api.getExternalUsersReport(dept),
    ]).then(([inactive, offboarding, cost, externalUsers]) => {
      if (!cancelled) {
        setInactiveReport(inactive);
        setOffboardingReport(offboarding);
        setCostReport(cost);
        setExternalUsersReport(externalUsers);
      }
    }).catch(console.error).finally(() => !cancelled && setLoading(false));

    return () => { cancelled = true; };
  }, [selectedDepartment]);

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between pt-2">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
            <p className="text-muted-foreground text-sm mt-0.5">License usage and cost analysis</p>
          </div>

          {/* Department Filter */}
          <Select value={selectedDepartment} onValueChange={setSelectedDepartment}>
            <SelectTrigger className="w-52 h-9 bg-zinc-50 border-zinc-200">
              <Building2 className="h-4 w-4 mr-2 text-zinc-400" />
              <SelectValue placeholder="Department" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Departments</SelectItem>
              {departments.map((dept) => (
                <SelectItem key={dept} value={dept}>{dept}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
          </div>
        ) : (
          <Tabs defaultValue="inactive" className="space-y-6">
            <TabsList className="bg-zinc-100/50 p-1">
              <TabsTrigger value="inactive" className="gap-1.5 data-[state=active]:bg-white">
                <Clock className="h-3.5 w-3.5" />
                Inactive
              </TabsTrigger>
              <TabsTrigger value="offboarding" className="gap-1.5 data-[state=active]:bg-white">
                <UserMinus className="h-3.5 w-3.5" />
                Offboarding
              </TabsTrigger>
              <TabsTrigger value="external" className="gap-1.5 data-[state=active]:bg-white">
                <AlertTriangle className="h-3.5 w-3.5" />
                External Users
              </TabsTrigger>
              <TabsTrigger value="costs" className="gap-1.5 data-[state=active]:bg-white">
                <Wallet className="h-3.5 w-3.5" />
                Costs
              </TabsTrigger>
            </TabsList>

            {/* Inactive Licenses */}
            <TabsContent value="inactive" className="space-y-6">
              {/* Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Inactive Licenses</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">{inactiveReport?.total_inactive || 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">No activity in {inactiveReport?.threshold_days || 30} days</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Potential Savings</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums text-emerald-600">
                    €{Number(inactiveReport?.potential_savings || 0).toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Per month if revoked</p>
                </div>
              </div>

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {inactiveReport && inactiveReport.licenses.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Provider</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">User</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Employee</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Days Inactive</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {inactiveReport.licenses.map((license) => (
                        <tr key={license.license_id} className="border-b last:border-0 hover:bg-zinc-50/50">
                          <td className="px-4 py-3 font-medium">{license.provider_name}</td>
                          <td className="px-4 py-3 text-muted-foreground">{license.external_user_id}</td>
                          <td className="px-4 py-3">
                            {license.employee_name ? (
                              <div className="flex items-center gap-2">
                                <div className="h-6 w-6 rounded-full bg-zinc-100 flex items-center justify-center">
                                  <span className="text-xs font-medium text-zinc-600">{license.employee_name.charAt(0)}</span>
                                </div>
                                {license.employee_name}
                              </div>
                            ) : (
                              <span className="text-muted-foreground">Unassigned</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={license.days_inactive > 60 ? 'destructive' : 'secondary'} className="tabular-nums">
                              {license.days_inactive}d
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {license.monthly_cost ? `€${Number(license.monthly_cost).toFixed(2)}` : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <Clock className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">No inactive licenses found</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Offboarding */}
            <TabsContent value="offboarding" className="space-y-6">
              {/* Stats */}
              <div className="border rounded-lg bg-white p-5">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-50 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-red-600" />
                  </div>
                  <div>
                    <p className="text-3xl font-semibold tabular-nums text-red-600">
                      {offboardingReport?.total_offboarded_with_licenses || 0}
                    </p>
                    <p className="text-sm text-muted-foreground">Offboarded employees with active licenses</p>
                  </div>
                </div>
              </div>

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {offboardingReport && offboardingReport.employees.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Employee</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Termination</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Days Since</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Pending Licenses</th>
                      </tr>
                    </thead>
                    <tbody>
                      {offboardingReport.employees.map((employee) => (
                        <tr key={employee.employee_email} className="border-b last:border-0 hover:bg-zinc-50/50">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="h-7 w-7 rounded-full bg-zinc-100 flex items-center justify-center">
                                <span className="text-xs font-medium text-zinc-600">{employee.employee_name.charAt(0)}</span>
                              </div>
                              <div>
                                <p className="font-medium">{employee.employee_name}</p>
                                <p className="text-xs text-muted-foreground">{employee.employee_email}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">
                            {employee.termination_date ? new Date(employee.termination_date).toLocaleDateString('de-DE') : '-'}
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant="destructive" className="tabular-nums">{employee.days_since_offboarding}d</Badge>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1">
                              {employee.pending_licenses.map((lic, i) => (
                                <Badge key={i} variant="outline">{lic.provider}</Badge>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <UserMinus className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">No offboarded employees with pending licenses</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* External Users */}
            <TabsContent value="external" className="space-y-6">
              {/* Stats */}
              <div className="border rounded-lg bg-white p-5">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-50 rounded-lg">
                    <AlertTriangle className="h-5 w-5 text-amber-600" />
                  </div>
                  <div>
                    <p className="text-3xl font-semibold tabular-nums text-amber-600">
                      {externalUsersReport?.total_external || 0}
                    </p>
                    <p className="text-sm text-muted-foreground">Licenses with external email addresses</p>
                  </div>
                </div>
              </div>

              {/* Info */}
              {externalUsersReport && externalUsersReport.total_external === 0 && (
                <div className="border rounded-lg bg-zinc-50/50 p-4 text-sm text-muted-foreground">
                  <p>No external users found. This report shows licenses assigned to email addresses that don't match your configured company domains.</p>
                  <p className="mt-1">Configure company domains in <Link href="/settings" className="underline hover:text-zinc-900">Settings</Link>.</p>
                </div>
              )}

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {externalUsersReport && externalUsersReport.licenses.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">External Email</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Provider</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Assigned Employee</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Type</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {externalUsersReport.licenses.map((license) => {
                        const isOffboarded = license.employee_status === 'offboarded';

                        return (
                          <tr key={license.license_id} className="border-b last:border-0 hover:bg-zinc-50/50">
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50 text-xs">
                                  <Globe className="h-3 w-3 mr-1" />
                                  External
                                </Badge>
                                <span className="font-medium">{license.external_user_id}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">{license.provider_name}</td>
                            <td className="px-4 py-3">
                              {license.employee_name && license.employee_id ? (
                                <div className="flex items-center gap-2">
                                  <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-zinc-900 group">
                                    <div className={`h-6 w-6 rounded-full flex items-center justify-center ${isOffboarded ? 'bg-red-100' : 'bg-zinc-100 group-hover:bg-zinc-200'} transition-colors`}>
                                      <span className={`text-xs font-medium ${isOffboarded ? 'text-red-600' : 'text-zinc-600'}`}>{license.employee_name.charAt(0)}</span>
                                    </div>
                                    <span className={`hover:underline ${isOffboarded ? 'text-muted-foreground line-through' : ''}`}>{license.employee_name}</span>
                                  </Link>
                                  {isOffboarded && (
                                    <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50 text-xs">
                                      <Skull className="h-3 w-3 mr-1" />
                                      Offboarded
                                    </Badge>
                                  )}
                                </div>
                              ) : (
                                <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50">
                                  Unassigned
                                </Badge>
                              )}
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">{license.license_type || '-'}</td>
                            <td className="px-4 py-3 text-right tabular-nums">
                              {license.monthly_cost ? `€${Number(license.monthly_cost).toFixed(2)}` : '-'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <AlertTriangle className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">No external users found</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Costs */}
            <TabsContent value="costs" className="space-y-6">
              {/* Stats */}
              <div className="border rounded-lg bg-white p-5">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-zinc-100 rounded-lg">
                    <Wallet className="h-5 w-5 text-zinc-600" />
                  </div>
                  <div>
                    <p className="text-3xl font-semibold tabular-nums">
                      €{Number(costReport?.total_cost || 0).toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-sm text-muted-foreground">Total monthly cost</p>
                  </div>
                </div>
              </div>

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {costReport && costReport.monthly_costs.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Provider</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Licenses</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Monthly Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {costReport.monthly_costs.map((entry, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-zinc-50/50">
                          <td className="px-4 py-3 font-medium">{entry.provider_name}</td>
                          <td className="px-4 py-3 tabular-nums">{entry.license_count}</td>
                          <td className="px-4 py-3 text-right tabular-nums font-medium">
                            €{Number(entry.cost).toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <Wallet className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">No cost data available</p>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </AppLayout>
  );
}
