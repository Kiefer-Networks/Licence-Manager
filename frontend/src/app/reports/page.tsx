'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
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
  Lightbulb,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { exportInactiveLicenses, exportOffboarding, exportExternalUsers, exportCosts, ExportTranslations } from '@/lib/export';
import { LicenseStatusBadge } from '@/components/licenses';
import { CostTrendChart } from '@/components/charts';
import { ExportButton } from '@/components/exports';
import { LicenseRecommendations } from '@/components/reports';
import { EmployeeTable, EmployeeTableData } from '@/components/users/EmployeeTable';
import Link from 'next/link';
import { useLocale } from '@/components/locale-provider';

export default function ReportsPage() {
  const t = useTranslations('reports');
  const tCommon = useTranslations('common');
  const tLicenses = useTranslations('licenses');
  const tExport = useTranslations('export');
  const { formatDate, formatCurrency } = useLocale();

  // Build export translations object
  const exportTranslations: ExportTranslations = {
    provider: tExport('provider'),
    userId: tExport('userId'),
    employee: tExport('employee'),
    email: tExport('email'),
    daysInactive: tExport('daysInactive'),
    monthlyCost: tExport('monthlyCost'),
    terminationDate: tExport('terminationDate'),
    daysSinceOffboarding: tExport('daysSinceOffboarding'),
    pendingLicenses: tExport('pendingLicenses'),
    licenseCount: tExport('licenseCount'),
    externalEmail: tExport('externalEmail'),
    assignedEmployee: tExport('assignedEmployee'),
    employeeEmail: tExport('employeeEmail'),
    status: tExport('status'),
    licenseType: tExport('licenseType'),
    licenses: tExport('licenses'),
    total: tExport('total'),
    unassigned: tExport('unassigned'),
  };
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
  // Min cost filter for costs-by-employee report
  const [minCostFilter, setMinCostFilter] = useState<string>('');
  const [debouncedMinCost, setDebouncedMinCost] = useState<string>('');
  // Tab state for lazy loading
  const [activeTab, setActiveTab] = useState('utilization');
  const [loadedTabs, setLoadedTabs] = useState<Set<string>>(new Set());
  const [tabLoading, setTabLoading] = useState<Set<string>>(new Set());

  // Load departments once
  useEffect(() => {
    api.getDepartments().then(setDepartments).catch((e) => handleSilentError('getDepartments', e));
  }, []);

  // Debounce min cost filter
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedMinCost(minCostFilter);
    }, 500);
    return () => clearTimeout(timer);
  }, [minCostFilter]);

  // Helper to mark tab as loading
  const setTabLoadingState = (tab: string, isLoading: boolean) => {
    setTabLoading(prev => {
      const next = new Set(prev);
      if (isLoading) next.add(tab);
      else next.delete(tab);
      return next;
    });
  };

  // Load data for a specific tab
  const loadTabData = async (tab: string, forceReload = false) => {
    // Skip if already loaded and not forcing reload
    if (loadedTabs.has(tab) && !forceReload) return;

    const dept = selectedDepartment !== 'all' ? selectedDepartment : undefined;
    setTabLoadingState(tab, true);

    try {
      switch (tab) {
        case 'utilization': {
          const [utilization, costTrend] = await Promise.all([
            api.getUtilizationReport(),
            api.getCostTrendReport(6),
          ]);
          setUtilizationReport(utilization);
          setCostTrendReport(costTrend);
          break;
        }
        case 'expiring': {
          const expiring = await api.getExpiringContractsReport(90);
          setExpiringContractsReport(expiring);
          break;
        }
        case 'duplicates': {
          const duplicates = await api.getDuplicateAccountsReport();
          setDuplicateAccountsReport(duplicates);
          break;
        }
        case 'inactive': {
          const inactive = await api.getInactiveLicenseReport(30, dept);
          setInactiveReport(inactive);
          break;
        }
        case 'offboarding': {
          const offboarding = await api.getOffboardingReport(dept);
          setOffboardingReport(offboarding);
          break;
        }
        case 'external': {
          const external = await api.getExternalUsersReport(dept);
          setExternalUsersReport(external);
          break;
        }
        case 'costs': {
          const costs = await api.getCostReport(undefined, undefined, dept);
          setCostReport(costs);
          break;
        }
        case 'costs-department': {
          const costsByDept = await api.getCostsByDepartmentReport();
          setCostsByDepartmentReport(costsByDept);
          break;
        }
        case 'costs-employee': {
          const costsByEmployee = await api.getCostsByEmployeeReport(dept, debouncedMinCost ? parseFloat(debouncedMinCost) : undefined, 100);
          setCostsByEmployeeReport(costsByEmployee);
          break;
        }
        case 'recommendations':
          // LicenseRecommendations component loads its own data
          break;
      }
      setLoadedTabs(prev => new Set(prev).add(tab));
    } catch (e) {
      handleSilentError(`load${tab}Report`, e);
    } finally {
      setTabLoadingState(tab, false);
    }
  };

  // Load initial tab on mount
  useEffect(() => {
    loadTabData('utilization');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load data when active tab changes
  useEffect(() => {
    loadTabData(activeTab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  // Reload current tab when department changes (for department-filtered tabs)
  useEffect(() => {
    const deptFilteredTabs = ['inactive', 'offboarding', 'external', 'costs', 'costs-employee'];
    if (deptFilteredTabs.includes(activeTab) && loadedTabs.has(activeTab)) {
      loadTabData(activeTab, true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDepartment]);

  // Reload costs-employee when min cost filter changes
  useEffect(() => {
    if (activeTab === 'costs-employee' && loadedTabs.has('costs-employee')) {
      loadTabData('costs-employee', true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedMinCost]);

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between pt-2">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
            <p className="text-muted-foreground text-sm mt-0.5">{t('utilizationReport')}</p>
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
                <SelectValue placeholder={tLicenses('department')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{tLicenses('allDepartments')}</SelectItem>
                {departments.map((dept) => (
                  <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="bg-zinc-100/50 p-1 flex-wrap h-auto gap-1">
              <TabsTrigger value="utilization" className="gap-1.5 data-[state=active]:bg-white">
                <BarChart3 className="h-3.5 w-3.5" />
                {t('utilization')}
              </TabsTrigger>
              <TabsTrigger value="expiring" className="gap-1.5 data-[state=active]:bg-white">
                <CalendarClock className="h-3.5 w-3.5" />
                {t('expiring')}
                {expiringContractsReport && expiringContractsReport.total_expiring > 0 && (
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs bg-amber-100 text-amber-700 border-0">
                    {expiringContractsReport.total_expiring}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="duplicates" className="gap-1.5 data-[state=active]:bg-white">
                <Users2 className="h-3.5 w-3.5" />
                {t('duplicates')}
                {duplicateAccountsReport && duplicateAccountsReport.total_duplicates > 0 && (
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs bg-amber-100 text-amber-700 border-0">
                    {duplicateAccountsReport.total_duplicates}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="inactive" className="gap-1.5 data-[state=active]:bg-white">
                <Clock className="h-3.5 w-3.5" />
                {t('inactive')}
              </TabsTrigger>
              <TabsTrigger value="offboarding" className="gap-1.5 data-[state=active]:bg-white">
                <UserMinus className="h-3.5 w-3.5" />
                {t('offboarding')}
              </TabsTrigger>
              <TabsTrigger value="external" className="gap-1.5 data-[state=active]:bg-white">
                <AlertTriangle className="h-3.5 w-3.5" />
                {t('external')}
              </TabsTrigger>
              <TabsTrigger value="costs" className="gap-1.5 data-[state=active]:bg-white">
                <Wallet className="h-3.5 w-3.5" />
                {t('costs')}
              </TabsTrigger>
              <TabsTrigger value="costs-department" className="gap-1.5 data-[state=active]:bg-white">
                <Building2 className="h-3.5 w-3.5" />
                {t('byDepartment')}
              </TabsTrigger>
              <TabsTrigger value="costs-employee" className="gap-1.5 data-[state=active]:bg-white">
                <User className="h-3.5 w-3.5" />
                {t('byEmployee')}
              </TabsTrigger>
              <TabsTrigger value="recommendations" className="gap-1.5 data-[state=active]:bg-white">
                <Lightbulb className="h-3.5 w-3.5" />
                {t('recommendations')}
              </TabsTrigger>
            </TabsList>

            {/* Utilization Report */}
            <TabsContent value="utilization" className="space-y-6">
              {tabLoading.has('utilization') ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : (
              <>
              {/* Stats Overview - Row 1 */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('activeLicenses')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">{utilizationReport?.total_active || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t('acrossAllProviders')}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{tLicenses('assigned')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums text-emerald-600">{utilizationReport?.total_assigned || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t('linkedToEmployees')}</p>
                  </CardContent>
                </Card>
                <Card className="border-amber-200 bg-amber-50/30">
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{tLicenses('unassigned')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums text-amber-600">{utilizationReport?.total_unassigned || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t('noEmployeeLinked')}</p>
                  </CardContent>
                </Card>
                <Card className="border-blue-200 bg-blue-50/30">
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('external')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums text-blue-600">{utilizationReport?.total_external || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t('externalEmails')}</p>
                  </CardContent>
                </Card>
              </div>

              {/* Stats Overview - Row 2: Costs */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{tLicenses('monthlyCost')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">
                      {formatCurrency(utilizationReport?.total_monthly_cost)}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">{t('totalLicenseCosts')}</p>
                  </CardContent>
                </Card>
                <Card className="border-amber-200 bg-amber-50/30">
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('unassignedCost')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums text-amber-600">
                      {formatCurrency(utilizationReport?.total_monthly_waste)}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">{t('noEmployeeLinked')}</p>
                  </CardContent>
                </Card>
                <Card className="border-blue-200 bg-blue-50/30">
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('externalCost')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums text-blue-600">
                      {formatCurrency(utilizationReport?.total_external_cost)}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">{t('externalEmailLicenses')}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-5 pb-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('utilization')}</p>
                    <p className="text-3xl font-semibold mt-1 tabular-nums">
                      {utilizationReport?.overall_utilization || 0}%
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">{t('assignedDivActive')}</p>
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
                      <p className="text-sm">{t('noCostHistoryAvailable')}</p>
                      <p className="text-xs mt-1">{t('historicalDataWillAppear')}</p>
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
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('provider')}</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground">{tLicenses('active')}</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground">{tLicenses('assigned')}</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground">{tLicenses('unassigned')}</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground">{t('external')}</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground">{t('cost')}</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground text-amber-600">{tLicenses('unassigned')} €</th>
                        <th className="text-right px-3 py-3 font-medium text-muted-foreground text-blue-600">{t('external')} €</th>
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
                              <span>{formatCurrency(provider.monthly_cost)}</span>
                            ) : '-'}
                          </td>
                          <td className="px-3 py-3 text-right tabular-nums">
                            {provider.monthly_waste ? (
                              <span className="text-amber-600">
                                {formatCurrency(provider.monthly_waste)}
                              </span>
                            ) : '-'}
                          </td>
                          <td className="px-3 py-3 text-right tabular-nums">
                            {provider.external_cost ? (
                              <span className="text-blue-600">
                                {formatCurrency(provider.external_cost)}
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
                    <p className="text-sm">{t('noLicenseDataAvailable')}</p>
                    <p className="text-xs mt-1">{t('syncProvidersToSeeData')}</p>
                  </div>
                )}
              </div>
              </>
              )}
            </TabsContent>

            {/* Expiring Contracts */}
            <TabsContent value="expiring" className="space-y-6">
              {tabLoading.has('expiring') ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : (
              <>
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
                    <p className="text-sm text-muted-foreground">{t('contractsExpiringIn90Days')}</p>
                  </div>
                </div>
              </div>

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {expiringContractsReport && expiringContractsReport.contracts.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('provider')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tLicenses('licenseType')}</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('seats')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('expiring')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('autoRenew')}</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('totalCost')}</th>
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
                              <span>{formatDate(contract.contract_end)}</span>
                              <Badge variant={contract.days_until_expiry <= 30 ? 'destructive' : 'secondary'} className="tabular-nums">
                                {contract.days_until_expiry}d
                              </Badge>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={contract.auto_renew ? 'secondary' : 'outline'}>
                              {contract.auto_renew ? tCommon('yes') : tCommon('no')}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {contract.total_cost ? (
                              <span>{formatCurrency(contract.total_cost)}</span>
                            ) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <CalendarClock className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">{t('noContractsExpiring90Days')}</p>
                  </div>
                )}
              </div>
              </>
              )}
            </TabsContent>

            {/* Duplicate Accounts */}
            <TabsContent value="duplicates" className="space-y-6">
              {tabLoading.has('duplicates') ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : (
              <>
              {/* Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('duplicateAccounts')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">{duplicateAccountsReport?.total_duplicates || 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">{t('sameEmailInProvider')}</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('potentialSavings')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums text-emerald-600">
                    {formatCurrency(duplicateAccountsReport?.potential_savings)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{t('perMonthIfConsolidated')}</p>
                </div>
              </div>

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {duplicateAccountsReport && duplicateAccountsReport.duplicates.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('email')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('occurrences')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('providers')}</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('totalCost')}</th>
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
                              <span>{formatCurrency(dup.total_monthly_cost)}</span>
                            ) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <Users2 className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">{t('noDuplicatesFound')}</p>
                  </div>
                )}
              </div>
              </>
              )}
            </TabsContent>

            {/* Inactive Licenses */}
            <TabsContent value="inactive" className="space-y-6">
              {tabLoading.has('inactive') ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : (
              <>
              {/* Header with Export */}
              <div className="flex items-center justify-between">
                <div />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => inactiveReport && exportInactiveLicenses(
                    inactiveReport.licenses,
                    exportTranslations,
                    selectedDepartment !== 'all' ? selectedDepartment : undefined
                  )}
                  disabled={!inactiveReport || inactiveReport.licenses.length === 0}
                  className="gap-2"
                >
                  <Download className="h-4 w-4" />
                  {t('exportCSV')}
                </Button>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('inactiveLicenses')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">{inactiveReport?.total_inactive || 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">{t('noActivityInDays', { days: inactiveReport?.threshold_days || 30 })}</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('potentialSavings')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums text-emerald-600">
                    {formatCurrency(inactiveReport?.potential_savings)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{t('perMonthIfRevoked')}</p>
                </div>
              </div>

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {inactiveReport && inactiveReport.licenses.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('provider')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('user')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('employee')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('daysInactive')}</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('cost')}</th>
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
                                      {t('offboarded')}
                                    </Badge>
                                  )}
                                </div>
                              ) : (
                                <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50">
                                  <Package className="h-3 w-3 mr-1" />
                                  {t('unassigned')}
                                </Badge>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <Badge variant={license.days_inactive > 60 ? 'destructive' : 'secondary'} className="tabular-nums">
                                {license.days_inactive}d
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-right tabular-nums">
                              {license.monthly_cost ? formatCurrency(license.monthly_cost) : '-'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <Clock className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">{t('noInactiveLicensesFound')}</p>
                  </div>
                )}
              </div>
              </>
              )}
            </TabsContent>

            {/* Offboarding */}
            <TabsContent value="offboarding" className="space-y-6">
              {tabLoading.has('offboarding') ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : (
              <>
              {/* Header with Export */}
              <div className="flex items-center justify-between">
                <div />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => offboardingReport && exportOffboarding(
                    offboardingReport.employees,
                    exportTranslations,
                    selectedDepartment !== 'all' ? selectedDepartment : undefined
                  )}
                  disabled={!offboardingReport || offboardingReport.employees.length === 0}
                  className="gap-2"
                >
                  <Download className="h-4 w-4" />
                  {t('exportCSV')}
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
                    <p className="text-sm text-muted-foreground">{t('offboardedWithLicenses')}</p>
                  </div>
                </div>
              </div>

              {/* Table */}
              <EmployeeTable
                employees={offboardingReport?.employees.map((emp): EmployeeTableData => ({
                  id: emp.employee_email, // Use email as ID since no real ID available
                  full_name: emp.employee_name,
                  email: emp.employee_email,
                  status: 'offboarded',
                  termination_date: emp.termination_date,
                  days_since_offboarding: emp.days_since_offboarding,
                  pending_licenses: emp.pending_licenses,
                })) || []}
                columns={['name', 'termination_date', 'days_since_offboarding', 'pending_licenses']}
                emptyMessage={t('noOffboardedWithPending')}
                compact
                showAdminAccountBadge={false}
                showManualBadge={false}
              />
              </>
              )}
            </TabsContent>

            {/* External Users */}
            <TabsContent value="external" className="space-y-6">
              {tabLoading.has('external') ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : (
              <>
              {/* Header with Export */}
              <div className="flex items-center justify-between">
                <div />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => externalUsersReport && exportExternalUsers(
                    externalUsersReport.licenses,
                    exportTranslations,
                    selectedDepartment !== 'all' ? selectedDepartment : undefined
                  )}
                  disabled={!externalUsersReport || externalUsersReport.licenses.length === 0}
                  className="gap-2"
                >
                  <Download className="h-4 w-4" />
                  {t('exportCSV')}
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
                    <p className="text-sm text-muted-foreground">{t('licensesWithExternalEmails')}</p>
                  </div>
                </div>
              </div>

              {/* Info */}
              {externalUsersReport && externalUsersReport.total_external === 0 && (
                <div className="border rounded-lg bg-zinc-50/50 p-4 text-sm text-muted-foreground">
                  <p>{t('noExternalUsersFoundDescription')}</p>
                  <p className="mt-1">{t('configureDomainsInSettings')} <Link href="/settings" className="underline hover:text-zinc-900">{tCommon('settings')}</Link>.</p>
                </div>
              )}

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {externalUsersReport && externalUsersReport.licenses.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('externalEmail')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('provider')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('assignedEmployee')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{tCommon('type')}</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('cost')}</th>
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
                                      {t('offboarded')}
                                    </Badge>
                                  )}
                                </div>
                              ) : (
                                <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50">
                                  <Package className="h-3 w-3 mr-1" />
                                  {t('unassigned')}
                                </Badge>
                              )}
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">{license.license_type || '-'}</td>
                            <td className="px-4 py-3 text-right tabular-nums">
                              {license.monthly_cost ? formatCurrency(license.monthly_cost) : '-'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <AlertTriangle className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">{t('noExternalUsersFound')}</p>
                  </div>
                )}
              </div>
              </>
              )}
            </TabsContent>

            {/* Costs */}
            <TabsContent value="costs" className="space-y-6">
              {tabLoading.has('costs') ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : (
              <>
              {/* Header with Export */}
              <div className="flex items-center justify-between">
                <div />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => costReport && exportCosts(
                    costReport.monthly_costs,
                    costReport.total_cost,
                    exportTranslations,
                    selectedDepartment !== 'all' ? selectedDepartment : undefined
                  )}
                  disabled={!costReport || costReport.monthly_costs.length === 0}
                  className="gap-2"
                >
                  <Download className="h-4 w-4" />
                  {t('exportCSV')}
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
                      {formatCurrency(costReport?.total_cost)}
                    </p>
                    <p className="text-sm text-muted-foreground">{t('totalMonthlyCost')}</p>
                  </div>
                </div>
              </div>

              {/* Currency Mix Warning */}
              {costReport?.has_currency_mix && (
                <div className="flex items-start gap-3 p-4 border border-amber-200 rounded-lg bg-amber-50">
                  <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-amber-800">{t('mixedCurrenciesDetected')}</p>
                    <p className="text-sm text-amber-700 mt-0.5">
                      {t('mixedCurrenciesDescription', { currencies: costReport.currencies_found.join(', ') })}
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
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('provider')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('licenses')}</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">{tLicenses('monthlyCost')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {costReport.monthly_costs.map((entry, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-zinc-50/50">
                          <td className="px-4 py-3 font-medium">{entry.provider_name}</td>
                          <td className="px-4 py-3 tabular-nums">{entry.license_count}</td>
                          <td className="px-4 py-3 text-right tabular-nums font-medium">
                            {formatCurrency(entry.cost)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                    <Wallet className="h-8 w-8 mb-2 opacity-30" />
                    <p className="text-sm">{t('noCostDataAvailable')}</p>
                  </div>
                )}
              </div>
              </>
              )}
            </TabsContent>

            {/* Costs by Department */}
            <TabsContent value="costs-department" className="space-y-6">
              {tabLoading.has('costs-department') ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : (
              <>
              {/* Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('departments')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">{costsByDepartmentReport?.total_departments || 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">{t('withAssignedLicenses')}</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('totalMonthlyCost')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">
                    {formatCurrency(costsByDepartmentReport?.total_monthly_cost)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{t('acrossAllDepartments')}</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('avgCostPerEmployee')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">
                    {formatCurrency(costsByDepartmentReport?.average_cost_per_employee)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{t('companyAverage')}</p>
                </div>
              </div>

              {/* Table */}
              <div className="border rounded-lg bg-white overflow-hidden">
                {costsByDepartmentReport && costsByDepartmentReport.departments.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-zinc-50/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('department')}</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('employees')}</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('licenses')}</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">{tLicenses('monthlyCost')}</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">{t('costPerEmployee')}</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('topProviders')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {costsByDepartmentReport.departments.map((dept) => (
                        <tr key={dept.department} className="border-b last:border-0 hover:bg-zinc-50/50">
                          <td className="px-4 py-3 font-medium">{dept.department}</td>
                          <td className="px-4 py-3 text-right tabular-nums">{dept.employee_count}</td>
                          <td className="px-4 py-3 text-right tabular-nums">{dept.license_count}</td>
                          <td className="px-4 py-3 text-right tabular-nums font-medium">
                            {formatCurrency(dept.total_monthly_cost)}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {formatCurrency(dept.cost_per_employee)}
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
                    <p className="text-sm">{t('noDepartmentDataAvailable')}</p>
                    <p className="text-xs mt-1">{t('assignLicensesToSeeDeptCosts')}</p>
                  </div>
                )}
              </div>
              </>
              )}
            </TabsContent>

            {/* Costs by Employee */}
            <TabsContent value="costs-employee" className="space-y-6">
              {tabLoading.has('costs-employee') ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : (
              <>
              {/* Stats */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('employees')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">{costsByEmployeeReport?.total_employees || 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">{t('withAssignedLicenses')}</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('totalMonthlyCost')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">
                    {formatCurrency(costsByEmployeeReport?.total_monthly_cost)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{t('allEmployees')}</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('averageCost')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">
                    {formatCurrency(costsByEmployeeReport?.average_cost_per_employee)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{t('perEmployee')}</p>
                </div>
                <div className="border rounded-lg bg-white p-5">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t('medianCost')}</p>
                  <p className="text-3xl font-semibold mt-1 tabular-nums">
                    {formatCurrency(costsByEmployeeReport?.median_cost_per_employee)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{t('perEmployee')}</p>
                </div>
              </div>

              {/* Highest Cost Employee Callout */}
              {costsByEmployeeReport?.max_cost_employee && (
                <div className="border rounded-lg bg-amber-50/50 border-amber-200 p-4">
                  <p className="text-sm text-amber-800">
                    <span className="font-medium">{t('highestCostEmployee')}:</span> {costsByEmployeeReport.max_cost_employee}
                  </p>
                </div>
              )}

              {/* Min Cost Filter */}
              <div className="flex items-center gap-3">
                <label className="text-sm text-muted-foreground whitespace-nowrap">{t('minMonthlyCost')}:</label>
                <Input
                  type="number"
                  min="0"
                  step="10"
                  placeholder={t('minCostPlaceholder')}
                  value={minCostFilter}
                  onChange={(e) => setMinCostFilter(e.target.value)}
                  className="w-40 h-9"
                />
                {minCostFilter && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setMinCostFilter('')}
                    className="text-muted-foreground"
                  >
                    {tCommon('clear')}
                  </Button>
                )}
              </div>

              {/* Table */}
              <EmployeeTable
                employees={costsByEmployeeReport?.employees.map((emp): EmployeeTableData => ({
                  id: emp.employee_id,
                  full_name: emp.employee_name,
                  email: emp.employee_email,
                  department: emp.department,
                  status: emp.status,
                  license_count: emp.license_count,
                  total_monthly_cost: emp.total_monthly_cost,
                  licenses: emp.licenses,
                })) || []}
                columns={['name', 'department', 'status', 'license_count', 'monthly_cost', 'tools']}
                emptyMessage={t('noEmployeeDataAvailable')}
                emptyDescription={t('assignLicensesToSeeIndividualCosts')}
                linkToEmployee
                compact
                showAdminAccountBadge={false}
                showManualBadge={false}
              />
              </>
              )}
            </TabsContent>

            {/* License Recommendations */}
            <TabsContent value="recommendations">
              <LicenseRecommendations
                department={selectedDepartment !== 'all' ? selectedDepartment : undefined}
              />
            </TabsContent>
          </Tabs>
      </div>
    </AppLayout>
  );
}
