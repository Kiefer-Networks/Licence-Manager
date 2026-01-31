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
import {
  api,
  InactiveLicenseReport,
  OffboardingReport,
  CostReport,
  ExternalUsersReport,
  ExpiringContractsReport,
  UtilizationReport,
  CostTrendReport,
  DuplicateAccountsReport,
  CostsByDepartmentReport,
  CostsByEmployeeReport,
} from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import {
  Clock,
  UserMinus,
  Wallet,
  Loader2,
  AlertCircle,
  Building2,
  AlertTriangle,
  Skull,
  Download,
  Package,
  CalendarClock,
  BarChart3,
  Users2,
  User,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { formatMonthlyCost } from '@/lib/format';
import { Button } from '@/components/ui/button';
import { exportInactiveLicenses, exportOffboarding, exportExternalUsers, exportCosts } from '@/lib/export';
import { LicenseStatusBadge } from '@/components/licenses';
import { CostTrendChart } from '@/components/charts';
import { ExportButton } from '@/components/exports';
import Link from 'next/link';

export default function ReportsPage() {
  const [inactiveReport, setInactiveReport] = useState<InactiveLicenseReport | null>(null);
  const [offboardingReport, setOffboardingReport] = useState<OffboardingReport | null>(null);
  const [costReport, setCostReport] = useState<CostReport | null>(null);
  const [externalUsersReport, setExternalUsersReport] = useState<ExternalUsersReport | null>(null);
  // Quick Win Reports
  const [expiringContractsReport, setExpiringContractsReport] = useState<ExpiringContractsReport | null>(null);
  const [utilizationReport, setUtilizationReport] = useState<UtilizationReport | null>(null);
  const [costTrendReport, setCostTrendReport] = useState<CostTrendReport | null>(null);
  const [duplicateAccountsReport, setDuplicateAccountsReport] = useState<DuplicateAccountsReport | null>(null);
  // Cost Breakdown Reports
  const [costsByDepartmentReport, setCostsByDepartmentReport] = useState<CostsByDepartmentReport | null>(null);
  const [costsByEmployeeReport, setCostsByEmployeeReport] = useState<CostsByEmployeeReport | null>(null);

  const [departments, setDepartments] = useState<string[]>([]);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  // Load departments once
  useEffect(() => {
    api.getDepartments().then(setDepartments).catch((e) => handleSilentError('getDepartments', e));
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
      // Quick Win Reports (not department-filtered)
      api.getExpiringContractsReport(90),
      api.getUtilizationReport(),
      api.getCostTrendReport(6),
      api.getDuplicateAccountsReport(),
      // Cost Breakdown Reports
      api.getCostsByDepartmentReport(),
      api.getCostsByEmployeeReport(dept, 100),
    ]).then(([inactive, offboarding, cost, externalUsers, expiring, utilization, costTrend, duplicates, costsByDept, costsByEmployee]) => {
      if (!cancelled) {
        setInactiveReport(inactive);
        setOffboardingReport(offboarding);
        setCostReport(cost);
        setExternalUsersReport(externalUsers);
        setExpiringContractsReport(expiring);
        setUtilizationReport(utilization);
        setCostTrendReport(costTrend);
        setDuplicateAccountsReport(duplicates);
        setCostsByDepartmentReport(costsByDept);
        setCostsByEmployeeReport(costsByEmployee);
      }
    }).catch((e) => handleSilentError('loadReports', e)).finally(() => !cancelled && setLoading(false));

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

          <div className="flex items-center gap-3">
            {/* Export Button */}
            <ExportButton
              department={selectedDepartment !== 'all' ? selectedDepartment : undefined}
            />

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
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
          </div>
        ) : (
          <Tabs defaultValue="utilization" className="space-y-6">
            <TabsList className="bg-zinc-100/50 p-1 flex-wrap h-auto gap-1">
              <TabsTrigger value="utilization" className="gap-1.5 data-[state=active]:bg-white">
                <BarChart3 className="h-3.5 w-3.5" />
                Utilization
              </TabsTrigger>
              <TabsTrigger value="expiring" className="gap-1.5 data-[state=active]:bg-white">
                <CalendarClock className="h-3.5 w-3.5" />
                Expiring
                {expiringContractsReport && expiringContractsReport.total_expiring > 0 && (
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs bg-amber-100 text-amber-700 border-0">
                    {expiringContractsReport.total_expiring}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="duplicates" className="gap-1.5 data-[state=active]:bg-white">
                <Users2 className="h-3.5 w-3.5" />
                Duplicates
                {duplicateAccountsReport && duplicateAccountsReport.total_duplicates > 0 && (
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs bg-amber-100 text-amber-700 border-0">
                    {duplicateAccountsReport.total_duplicates}
                  </Badge>
                )}
              </TabsTrigger>
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
                External
              </TabsTrigger>
              <TabsTrigger value="costs" className="gap-1.5 data-[state=active]:bg-white">
                <Wallet className="h-3.5 w-3.5" />
                Costs
              </TabsTrigger>
              <TabsTrigger value="costs-department" className="gap-1.5 data-[state=active]:bg-white">
                <Building2 className="h-3.5 w-3.5" />
                By Department
              </TabsTrigger>
              <TabsTrigger value="costs-employee" className="gap-1.5 data-[state=active]:bg-white">
                <User className="h-3.5 w-3.5" />
                By Employee
              </TabsTrigger>
            </TabsList>

            {/* Utilization Report */}
            <TabsContent value="utilization" className="space-y-6">
              {/* Stats Overview - Row 1 */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Active Licenses</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">{utilizationReport?.total_active || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">Across all providers</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Assigned</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums text-emerald-600">{utilizationReport?.total_assigned || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">Linked to employees</p>
                  </CardContent>
                </Card>
                <Card className="border-amber-200 bg-amber-50/30">
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Unassigned</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums text-amber-600">{utilizationReport?.total_unassigned || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">No employee linked</p>
                  </CardContent>
                </Card>
                <Card className="border-blue-200 bg-blue-50/30">
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">External</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums text-blue-600">{utilizationReport?.total_external || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">External emails</p>
                  </CardContent>
                </Card>
              </div>

              {/* Stats Overview - Row 2: Costs */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Monthly Cost</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">
                      EUR {Number(utilizationReport?.total_monthly_cost || 0).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">Total license costs</p>
                  </CardContent>
                </Card>
                <Card className="border-amber-200 bg-amber-50/30">
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Unassigned Cost</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums text-amber-600">
                      EUR {Number(utilizationReport?.total_monthly_waste || 0).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">No employee linked</p>
                  </CardContent>
                </Card>
                <Card className="border-blue-200 bg-blue-50/30">
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">External Cost</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums text-blue-600">
                      EUR {Number(utilizationReport?.total_external_cost || 0).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">External email licenses</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Utilization</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">
                      {utilizationReport?.overall_utilization || 0}%
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">Assigned / Active</p>
                  </CardContent>
                </Card>
              </div>

              {/* Cost Trend Chart */}
              <Card>
                <CardContent className="pt-5 pb-4">
                  {costTrendReport && costTrendReport.has_data && costTrendReport.months.length > 0 ? (
                    <CostTrendChart
                      data={costTrendReport.months}
                      trendDirection={costTrendReport.trend_direction}
                      percentChange={costTrendReport.percent_change}
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                      <BarChart3 className="h-8 w-8 mb-2 opacity-30" />
                      <p className="text-sm">No cost history available</p>
                      <p className="text-xs mt-1">Historical data will appear after the first monthly snapshot</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Utilization by Provider Table */}
              <div className="border rounded-lg bg-white overflow-hidden overflow-x-auto">
                {utilizationReport && utilizationReport.providers.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Provider</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground">Active</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground">Assigned</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground">Unassigned</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground">External</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground">Cost</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground text-amber-600">Unassigned €</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground text-blue-600">External €</th>
                      </tr>
                    </thead>
                    <tbody>
                      {utilizationReport.providers.map((provider, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-zinc-50/50">
                          <td className="px-4 py-3">
                            <div>
                              <Link href={`/providers/${provider.provider_id}`} className="font-medium hover:underline">
                                {provider.provider_name}
                              </Link>
                              {provider.license_type && (
                                <p className="text-xs text-muted-foreground">{provider.license_type}</p>
                              )}
                              {provider.purchased_seats > 0 && (
                                <p className="text-xs text-muted-foreground">{provider.purchased_seats} purchased</p>
                              )}
                            </div>
                          </td>
                          <td className="px-3 py-3 text-right tabular-nums">{provider.active_seats}</td>
                          <td className="px-3 py-3 text-right tabular-nums text-emerald-600">{provider.assigned_seats}</td>
                          <td className="px-3 py-3 text-right tabular-nums">
                            {provider.unassigned_seats > 0 ? (
                              <span className="text-amber-600">{provider.unassigned_seats}</span>
                            ) : (
                              <span className="text-muted-foreground">0</span>
                            )}
                          </td>
                          <td className="px-3 py-3 text-right tabular-nums">
                            {provider.external_seats > 0 ? (
                              <span className="text-blue-600">{provider.external_seats}</span>
                            ) : (
                              <span className="text-muted-foreground">0</span>
                            )}
                          </td>
                          <td className="px-3 py-3 text-right tabular-nums">
                            {provider.monthly_cost ? (
                              <span>€{Number(provider.monthly_cost).toLocaleString('de-DE', { minimumFractionDigits: 0 })}</span>
                            ) : '-'}
                          </td>
                          <td className="px-3 py-3 text-right tabular-nums">
                            {provider.monthly_waste ? (
                              <span className="text-amber-600">
                                €{Number(provider.monthly_waste).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                              </span>
                            ) : '-'}
                          </td>
                          <td className="px-3 py-3 text-right tabular-nums">
                            {provider.external_cost ? (
                              <span className="text-blue-600">
                                €{Number(provider.external_cost).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                              </span>
                            ) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <BarChart3 className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">No license data available</p>
                    <p className="text-xs mt-1">Sync providers to see utilization data</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Expiring Contracts */}
            <TabsContent value="expiring" className="space-y-6">
              {/* Stats */}
              <div className="border rounded-lg bg-white p-5">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${expiringContractsReport?.total_expiring ? 'bg-amber-50' : 'bg-zinc-100'}`}>
                    <CalendarClock className={`h-5 w-5 ${expiringContractsReport?.total_expiring ? 'text-amber-600' : 'text-zinc-400'}`} />
                  </div>
                  <div>
                    <p className={`text-3xl font-semibold tabular-nums ${expiringContractsReport?.total_expiring ? 'text-amber-600' : ''}`}>
                      {expiringContractsReport?.total_expiring || 0}
                    </p>
                    <p className="text-sm text-muted-foreground">Contracts expiring in the next 90 days</p>
                  </div>
                </div>
              </div>

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {expiringContractsReport && expiringContractsReport.contracts.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Provider</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">License Type</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Seats</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Expires</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Auto-Renew</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Total Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {expiringContractsReport.contracts.map((contract) => (
                        <tr key={contract.package_id} className="border-b last:border-0 hover:bg-zinc-50/50">
                          <td className="px-4 py-3">
                            <Link href={`/providers/${contract.provider_id}`} className="font-medium hover:underline">
                              {contract.provider_name}
                            </Link>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">
                            {contract.display_name || contract.license_type}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">{contract.total_seats}</td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span>{new Date(contract.contract_end).toLocaleDateString('de-DE')}</span>
                              <Badge variant={contract.days_until_expiry <= 30 ? 'destructive' : 'secondary'} className="tabular-nums">
                                {contract.days_until_expiry}d
                              </Badge>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={contract.auto_renew ? 'secondary' : 'outline'}>
                              {contract.auto_renew ? 'Yes' : 'No'}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {contract.total_cost ? (
                              <span>EUR {Number(contract.total_cost).toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
                            ) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <CalendarClock className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">No contracts expiring in the next 90 days</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Duplicate Accounts */}
            <TabsContent value="duplicates" className="space-y-6">
              {/* Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Duplicate Accounts</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">{duplicateAccountsReport?.total_duplicates || 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">Same email in same provider</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Potential Savings</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums text-emerald-600">
                    EUR {Number(duplicateAccountsReport?.potential_savings || 0).toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Per month if consolidated</p>
                </div>
              </div>

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {duplicateAccountsReport && duplicateAccountsReport.duplicates.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Email</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Occurrences</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Providers</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Total Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {duplicateAccountsReport.duplicates.map((dup, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-zinc-50/50">
                          <td className="px-4 py-3 font-medium">{dup.email}</td>
                          <td className="px-4 py-3">
                            <Badge variant="destructive" className="tabular-nums">{dup.occurrences}x</Badge>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1">
                              {dup.providers.map((p, j) => (
                                <Badge key={j} variant="outline">{p}</Badge>
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {dup.total_monthly_cost ? (
                              <span>EUR {Number(dup.total_monthly_cost).toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
                            ) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <Users2 className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">No duplicate accounts found</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Inactive Licenses */}
            <TabsContent value="inactive" className="space-y-6">
              {/* Header with Export */}
              <div className="flex items-center justify-between">
                <div />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => inactiveReport && exportInactiveLicenses(
                    inactiveReport.licenses,
                    selectedDepartment !== 'all' ? selectedDepartment : undefined
                  )}
                  disabled={!inactiveReport || inactiveReport.licenses.length === 0}
                  className="gap-2"
                >
                  <Download className="h-4 w-4" />
                  Export CSV
                </Button>
              </div>

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
                      {inactiveReport.licenses.map((license) => {
                        const isOffboarded = license.employee_status === 'offboarded';
                        return (
                          <tr key={license.license_id} className="border-b last:border-0 hover:bg-zinc-50/50">
                            <td className="px-4 py-3 font-medium">
                              <Link href={`/providers/${license.provider_id}`} className="hover:underline">
                                {license.provider_name}
                              </Link>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <span className="text-muted-foreground">{license.external_user_id}</span>
                                {license.is_external_email && (
                                  <LicenseStatusBadge
                                    license={{
                                      is_external_email: true,
                                      employee_id: license.employee_id,
                                      employee_status: license.employee_status,
                                    }}
                                    showUnassigned={false}
                                  />
                                )}
                              </div>
                            </td>
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
                                  <Package className="h-3 w-3 mr-1" />
                                  Unassigned
                                </Badge>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <Badge variant={license.days_inactive > 60 ? 'destructive' : 'secondary'} className="tabular-nums">
                                {license.days_inactive}d
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-right tabular-nums">
                              {license.monthly_cost ? formatMonthlyCost(license.monthly_cost, 'EUR') : '-'}
                            </td>
                          </tr>
                        );
                      })}
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
              {/* Header with Export */}
              <div className="flex items-center justify-between">
                <div />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => offboardingReport && exportOffboarding(
                    offboardingReport.employees,
                    selectedDepartment !== 'all' ? selectedDepartment : undefined
                  )}
                  disabled={!offboardingReport || offboardingReport.employees.length === 0}
                  className="gap-2"
                >
                  <Download className="h-4 w-4" />
                  Export CSV
                </Button>
              </div>

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
              {/* Header with Export */}
              <div className="flex items-center justify-between">
                <div />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => externalUsersReport && exportExternalUsers(
                    externalUsersReport.licenses,
                    selectedDepartment !== 'all' ? selectedDepartment : undefined
                  )}
                  disabled={!externalUsersReport || externalUsersReport.licenses.length === 0}
                  className="gap-2"
                >
                  <Download className="h-4 w-4" />
                  Export CSV
                </Button>
              </div>

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
                                <span className="font-medium">{license.external_user_id}</span>
                                <LicenseStatusBadge
                                  license={{
                                    is_external_email: true,
                                    employee_id: license.employee_id,
                                    employee_status: license.employee_status,
                                  }}
                                  showUnassigned={false}
                                />
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <Link href={`/providers/${license.provider_id}`} className="hover:underline text-muted-foreground hover:text-zinc-900">
                                {license.provider_name}
                              </Link>
                            </td>
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
                                  <Package className="h-3 w-3 mr-1" />
                                  Unassigned
                                </Badge>
                              )}
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">{license.license_type || '-'}</td>
                            <td className="px-4 py-3 text-right tabular-nums">
                              {license.monthly_cost ? formatMonthlyCost(license.monthly_cost, 'EUR') : '-'}
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
              {/* Header with Export */}
              <div className="flex items-center justify-between">
                <div />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => costReport && exportCosts(
                    costReport.monthly_costs,
                    costReport.total_cost,
                    selectedDepartment !== 'all' ? selectedDepartment : undefined
                  )}
                  disabled={!costReport || costReport.monthly_costs.length === 0}
                  className="gap-2"
                >
                  <Download className="h-4 w-4" />
                  Export CSV
                </Button>
              </div>

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

              {/* Currency Mix Warning */}
              {costReport?.has_currency_mix && (
                <div className="flex items-start gap-3 p-4 border border-amber-200 rounded-lg bg-amber-50">
                  <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-amber-800">Mixed currencies detected</p>
                    <p className="text-sm text-amber-700 mt-0.5">
                      Cost data includes multiple currencies ({costReport.currencies_found.join(', ')}).
                      Totals are shown in EUR but may not reflect accurate exchange rates.
                    </p>
                  </div>
                </div>
              )}

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

            {/* Costs by Department */}
            <TabsContent value="costs-department" className="space-y-6">
              {/* Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Departments</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">{costsByDepartmentReport?.total_departments || 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">With assigned licenses</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Total Monthly Cost</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">
                    €{Number(costsByDepartmentReport?.total_monthly_cost || 0).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Across all departments</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Avg. Cost / Employee</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">
                    €{Number(costsByDepartmentReport?.average_cost_per_employee || 0).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Company average</p>
                </div>
              </div>

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {costsByDepartmentReport && costsByDepartmentReport.departments.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Department</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Employees</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Licenses</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Monthly Cost</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Cost / Employee</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Top Providers</th>
                      </tr>
                    </thead>
                    <tbody>
                      {costsByDepartmentReport.departments.map((dept) => (
                        <tr key={dept.department} className="border-b last:border-0 hover:bg-zinc-50/50">
                          <td className="px-4 py-3 font-medium">{dept.department}</td>
                          <td className="px-4 py-3 text-right tabular-nums">{dept.employee_count}</td>
                          <td className="px-4 py-3 text-right tabular-nums">{dept.license_count}</td>
                          <td className="px-4 py-3 text-right tabular-nums font-medium">
                            €{Number(dept.total_monthly_cost).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            €{Number(dept.cost_per_employee).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1">
                              {dept.top_providers.map((p, i) => (
                                <Badge key={i} variant="outline" className="text-xs">{p}</Badge>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <Building2 className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">No department data available</p>
                    <p className="text-xs mt-1">Assign licenses to employees to see department costs</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Costs by Employee */}
            <TabsContent value="costs-employee" className="space-y-6">
              {/* Stats */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Employees</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">{costsByEmployeeReport?.total_employees || 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">With assigned licenses</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Total Monthly Cost</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">
                    €{Number(costsByEmployeeReport?.total_monthly_cost || 0).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">All employees</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Average Cost</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">
                    €{Number(costsByEmployeeReport?.average_cost_per_employee || 0).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Per employee</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Median Cost</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">
                    €{Number(costsByEmployeeReport?.median_cost_per_employee || 0).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Per employee</p>
                </div>
              </div>

              {/* Highest Cost Employee Callout */}
              {costsByEmployeeReport?.max_cost_employee && (
                <div className="border rounded-lg bg-amber-50/50 border-amber-200 p-4">
                  <p className="text-sm text-amber-800">
                    <span className="font-medium">Highest cost employee:</span> {costsByEmployeeReport.max_cost_employee}
                  </p>
                </div>
              )}

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {costsByEmployeeReport && costsByEmployeeReport.employees.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Employee</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Department</th>
                        <th className="text-center px-4 py-3 font-medium text-muted-foreground">Status</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Licenses</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Monthly Cost</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Tools</th>
                      </tr>
                    </thead>
                    <tbody>
                      {costsByEmployeeReport.employees.map((employee) => {
                        const isOffboarded = employee.status === 'offboarded';
                        return (
                          <tr key={employee.employee_id} className="border-b last:border-0 hover:bg-zinc-50/50">
                            <td className="px-4 py-3">
                              <Link href={`/users/${employee.employee_id}`} className="flex items-center gap-2 hover:text-zinc-900 group">
                                <div className={`h-7 w-7 rounded-full flex items-center justify-center ${isOffboarded ? 'bg-red-100' : 'bg-zinc-100 group-hover:bg-zinc-200'} transition-colors`}>
                                  <span className={`text-xs font-medium ${isOffboarded ? 'text-red-600' : 'text-zinc-600'}`}>
                                    {employee.employee_name.charAt(0)}
                                  </span>
                                </div>
                                <div>
                                  <p className={`font-medium hover:underline ${isOffboarded ? 'line-through text-muted-foreground' : ''}`}>
                                    {employee.employee_name}
                                  </p>
                                  <p className="text-xs text-muted-foreground">{employee.employee_email}</p>
                                </div>
                              </Link>
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">{employee.department || '-'}</td>
                            <td className="px-4 py-3 text-center">
                              {isOffboarded ? (
                                <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50 text-xs">
                                  <Skull className="h-3 w-3 mr-1" />
                                  Offboarded
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="text-emerald-600 border-emerald-200 bg-emerald-50 text-xs">
                                  Active
                                </Badge>
                              )}
                            </td>
                            <td className="px-4 py-3 text-right tabular-nums">{employee.license_count}</td>
                            <td className="px-4 py-3 text-right tabular-nums font-medium">
                              €{Number(employee.total_monthly_cost).toLocaleString('de-DE', { minimumFractionDigits: 0 })}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex flex-wrap gap-1">
                                {employee.licenses.slice(0, 3).map((lic, i) => (
                                  <Badge key={i} variant="outline" className="text-xs">{lic.provider_name}</Badge>
                                ))}
                                {employee.licenses.length > 3 && (
                                  <Badge variant="secondary" className="text-xs">+{employee.licenses.length - 3}</Badge>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <User className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">No employee data available</p>
                    <p className="text-xs mt-1">Assign licenses to employees to see individual costs</p>
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
