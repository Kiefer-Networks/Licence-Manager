'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { AppLayout } from '@/components/layout/app-layout';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api, Employee, Provider } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import { Search, ChevronUp, ChevronDown, ChevronsUpDown, Loader2, Users, ChevronRight, Bot, ShieldCheck, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { ServiceAccountsTab } from '@/components/users/ServiceAccountsTab';
import { getLocale } from '@/lib/locale';
import { AdminAccountsTab } from '@/components/users/AdminAccountsTab';

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString(getLocale());
}

export default function UsersPage() {
  const t = useTranslations('employees');
  const tCommon = useTranslations('common');
  const tUsers = useTranslations('users');
  const tServiceAccounts = useTranslations('serviceAccounts');
  const tAdminAccounts = useTranslations('adminAccounts');

  const router = useRouter();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [sortColumn, setSortColumn] = useState<string>('full_name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [activeTab, setActiveTab] = useState<string>('employees');
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  const showToast = (type: 'success' | 'error' | 'info', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 4000);
  };

  const debouncedSearch = useDebounce(search, 300);

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const SortIcon = ({ column }: { column: string }) => {
    if (sortColumn !== column) return <ChevronsUpDown className="h-3.5 w-3.5 text-zinc-400" />;
    return sortDirection === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />;
  };

  useEffect(() => {
    api.getDepartments().then(setDepartments).catch((e) => handleSilentError('getDepartments', e));
    api.getProviders().then((data) => setProviders(data.items)).catch((e) => handleSilentError('getProviders', e));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.getEmployees({
      page,
      search: debouncedSearch || undefined,
      status: selectedStatus !== 'all' ? selectedStatus : undefined,
      department: selectedDepartment !== 'all' ? selectedDepartment : undefined,
      sort_by: sortColumn,
      sort_dir: sortDirection,
    }).then((data) => {
      if (!cancelled) {
        setEmployees(data.items);
        setTotal(data.total);
        setLoading(false);
      }
    }).catch(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [page, debouncedSearch, selectedStatus, selectedDepartment, sortColumn, sortDirection]);

  const pageSize = 50;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="pt-2">
          <h1 className="text-2xl font-semibold tracking-tight">{tUsers('title')}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            {t('title')}, {tServiceAccounts('title')}, {tAdminAccounts('title')}
          </p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="employees" className="gap-2">
              <Users className="h-4 w-4" />
              {t('title')}
            </TabsTrigger>
            <TabsTrigger value="service-accounts" className="gap-2">
              <Bot className="h-4 w-4" />
              {tServiceAccounts('title')}
            </TabsTrigger>
            <TabsTrigger value="admin-accounts" className="gap-2">
              <ShieldCheck className="h-4 w-4" />
              {tAdminAccounts('title')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="employees" className="space-y-6 mt-6">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                <Input
                  placeholder={tCommon('search')}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 h-9 bg-zinc-50 border-zinc-200"
                />
              </div>

              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger className="w-32 h-9 bg-zinc-50 border-zinc-200">
                  <SelectValue placeholder={tCommon('status')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{tCommon('all')} {tCommon('status')}</SelectItem>
                  <SelectItem value="active">{t('active')}</SelectItem>
                  <SelectItem value="offboarded">{t('offboarded')}</SelectItem>
                </SelectContent>
              </Select>

              <Select value={selectedDepartment} onValueChange={setSelectedDepartment}>
                <SelectTrigger className="w-44 h-9 bg-zinc-50 border-zinc-200">
                  <SelectValue placeholder={t('department')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{tCommon('all')} {t('department')}</SelectItem>
                  {departments.map((dept) => (
                    <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <span className="text-sm text-muted-foreground ml-auto">
                {total} {t('employee')}{total !== 1 ? 's' : ''}
              </span>
            </div>

            {/* Table */}
            <div className="border rounded-lg bg-white overflow-hidden">
              {loading ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                </div>
              ) : employees.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                  <Users className="h-8 w-8 mb-2 opacity-30" />
                  <p className="text-sm">{t('noEmployees')}</p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-zinc-50/50">
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                        <button onClick={() => handleSort('full_name')} className="flex items-center gap-1.5 hover:text-foreground">
                          {tCommon('name')} <SortIcon column="full_name" />
                        </button>
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                        <button onClick={() => handleSort('email')} className="flex items-center gap-1.5 hover:text-foreground">
                          {tCommon('email')} <SortIcon column="email" />
                        </button>
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                        <button onClick={() => handleSort('department')} className="flex items-center gap-1.5 hover:text-foreground">
                          {t('department')} <SortIcon column="department" />
                        </button>
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                        {tCommon('manager')}
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                        <button onClick={() => handleSort('status')} className="flex items-center gap-1.5 hover:text-foreground">
                          {tCommon('status')} <SortIcon column="status" />
                        </button>
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t('licenseCount')}</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                        <button onClick={() => handleSort('start_date')} className="flex items-center gap-1.5 hover:text-foreground">
                          {t('startDate')} <SortIcon column="start_date" />
                        </button>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {employees.map((employee) => (
                      <tr
                        key={employee.id}
                        onClick={() => router.push(`/users/${employee.id}`)}
                        className="border-b last:border-0 hover:bg-zinc-50/50 transition-colors cursor-pointer"
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            {employee.avatar ? (
                              <img
                                src={employee.avatar}
                                alt=""
                                className="h-7 w-7 rounded-full object-cover flex-shrink-0"
                              />
                            ) : (
                              <div className="h-7 w-7 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">
                                <span className="text-xs font-medium text-zinc-600">{employee.full_name.charAt(0)}</span>
                              </div>
                            )}
                            <span className="font-medium">{employee.full_name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">{employee.email}</td>
                        <td className="px-4 py-3 text-muted-foreground">{employee.department || '-'}</td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {employee.manager ? (
                            <span
                              className="hover:text-foreground cursor-pointer hover:underline"
                              onClick={(e) => {
                                e.stopPropagation();
                                router.push(`/users/${employee.manager!.id}`);
                              }}
                            >
                              {employee.manager.full_name}
                            </span>
                          ) : '-'}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={employee.status === 'active' ? 'secondary' : 'destructive'} className={employee.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-0' : ''}>
                            {employee.status === 'active' ? t('active') : t('offboarded')}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            <Badge variant="outline" className="tabular-nums">{employee.license_count}</Badge>
                            {(employee.owned_admin_account_count || 0) > 0 && (
                              <Badge variant="outline" className="tabular-nums bg-purple-50 text-purple-700 border-purple-200">
                                +{employee.owned_admin_account_count} {t('adminAccounts')}
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground tabular-nums">
                          <div className="flex items-center justify-between">
                            {formatDate(employee.start_date)}
                            <ChevronRight className="h-4 w-4 text-zinc-300" />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">{tCommon('page')} {page} {tCommon('of')} {totalPages}</p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setPage(page - 1)} disabled={page === 1}>{tCommon('back')}</Button>
                  <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={page === totalPages}>{tCommon('next')}</Button>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="service-accounts" className="mt-6">
            <ServiceAccountsTab providers={providers} showToast={showToast} />
          </TabsContent>

          <TabsContent value="admin-accounts" className="mt-6">
            <AdminAccountsTab providers={providers} showToast={showToast} />
          </TabsContent>
        </Tabs>
      </div>

      {/* Toast notification */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-2">
          <div className={`flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg ${
            toast.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
            toast.type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
            'bg-blue-50 text-blue-800 border border-blue-200'
          }`}>
            {toast.type === 'success' && <CheckCircle className="h-4 w-4" />}
            {toast.type === 'error' && <AlertCircle className="h-4 w-4" />}
            {toast.type === 'info' && <Info className="h-4 w-4" />}
            <span className="text-sm">{toast.text}</span>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
