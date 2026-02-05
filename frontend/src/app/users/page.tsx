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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api, Employee, EmployeeSource, Provider } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import { Search, Users, Bot, ShieldCheck, CheckCircle, AlertCircle, Info, Upload, UserPlus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { ServiceAccountsTab } from '@/components/users/ServiceAccountsTab';
import { AdminAccountsTab } from '@/components/users/AdminAccountsTab';
import { EmployeeTable, mapEmployeeToTableData } from '@/components/users/EmployeeTable';
import { ManualEmployeeDialog } from '@/components/users/ManualEmployeeDialog';
import { EmployeeBulkImportDialog } from '@/components/users/EmployeeBulkImportDialog';

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
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
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [sortColumn, setSortColumn] = useState<string>('full_name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [activeTab, setActiveTab] = useState<string>('employees');
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Manual employee dialogs
  const [showAddEmployee, setShowAddEmployee] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);

  const showToast = (type: 'success' | 'error' | 'info', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 4000);
  };

  const debouncedSearch = useDebounce(search, 300);

  const handleSort = (column: string) => {
    setPage(1); // Reset to first page when sorting changes
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  useEffect(() => {
    Promise.all([
      api.getDepartments(),
      api.getProviders(),
    ]).then(([departmentsData, providersData]) => {
      setDepartments(departmentsData);
      setProviders(providersData.items);
    }).catch((e) => handleSilentError('getDepartments', e));
  }, []);

  // Reset page to 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, selectedStatus, selectedDepartment, selectedSource]);

  const loadEmployees = () => {
    setLoading(true);
    api.getEmployees({
      page,
      search: debouncedSearch || undefined,
      status: selectedStatus !== 'all' ? selectedStatus : undefined,
      department: selectedDepartment !== 'all' ? selectedDepartment : undefined,
      source: selectedSource !== 'all' ? (selectedSource as EmployeeSource) : undefined,
      sort_by: sortColumn,
      sort_dir: sortDirection,
    }).then((data) => {
      setEmployees(data.items);
      setTotal(data.total);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => {
    loadEmployees();
  }, [page, debouncedSearch, selectedStatus, selectedDepartment, selectedSource, sortColumn, sortDirection]);

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
            {/* Filters and Actions */}
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

              <Select value={selectedSource} onValueChange={setSelectedSource}>
                <SelectTrigger className="w-36 h-9 bg-zinc-50 border-zinc-200">
                  <SelectValue placeholder={t('filterBySource')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('allSources')}</SelectItem>
                  <SelectItem value="hibob">{t('sourceHibob')}</SelectItem>
                  <SelectItem value="personio">{t('sourcePersonio')}</SelectItem>
                  <SelectItem value="manual">{t('sourceManual')}</SelectItem>
                </SelectContent>
              </Select>

              <span className="text-sm text-muted-foreground">
                {total} {t('employee')}{total !== 1 ? 's' : ''}
              </span>

              <div className="flex items-center gap-2 ml-auto">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowImportDialog(true)}
                  className="h-9 gap-2"
                >
                  <Upload className="h-4 w-4" />
                  {t('importEmployees')}
                </Button>
                <Button
                  size="sm"
                  onClick={() => setShowAddEmployee(true)}
                  className="h-9 gap-2"
                >
                  <UserPlus className="h-4 w-4" />
                  {t('addEmployee')}
                </Button>
              </div>
            </div>

            {/* Table */}
            <EmployeeTable
              employees={employees.map(mapEmployeeToTableData)}
              columns={['name', 'email', 'department', 'manager', 'status', 'license_count', 'start_date']}
              loading={loading}
              emptyMessage={t('noEmployees')}
              sortable
              sortColumn={sortColumn}
              sortDirection={sortDirection}
              onSort={handleSort}
              pagination={{
                page,
                totalPages,
                onPageChange: setPage,
              }}
              linkToEmployee
              showChevron
            />
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

      {/* Manual Employee Dialog */}
      <ManualEmployeeDialog
        open={showAddEmployee}
        onOpenChange={setShowAddEmployee}
        employee={null}
        departments={departments}
        onSuccess={loadEmployees}
        showToast={showToast}
      />

      {/* Bulk Import Dialog */}
      <EmployeeBulkImportDialog
        open={showImportDialog}
        onOpenChange={setShowImportDialog}
        onSuccess={loadEmployees}
        showToast={showToast}
      />
    </AppLayout>
  );
}
