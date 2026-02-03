'use client';

import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronUp, ChevronDown, ChevronRight, Skull, Loader2, Users } from 'lucide-react';
import { useLocale } from '@/components/locale-provider';
import Link from 'next/link';

// Base employee type that all employee data should conform to
export interface EmployeeTableData {
  id: string;
  full_name: string;
  email: string;
  avatar?: string | null;
  department?: string | null;
  status?: string;
  is_manual?: boolean;
  manager?: {
    id: string;
    full_name: string;
    avatar?: string | null;
  } | null;
  license_count?: number;
  owned_admin_account_count?: number;
  start_date?: string | null;
  termination_date?: string | null;
  // For costs report (accepts both string and number from API)
  total_monthly_cost?: number | string;
  licenses?: Array<{
    provider_name: string;
    license_type?: string;
    monthly_cost?: number | string | null;
  }>;
  // For offboarding report
  days_since_offboarding?: number;
  pending_licenses?: Array<{
    provider: string;
    type?: string;
    external_id?: string;
  }>;
}

// Column definitions
export type EmployeeColumnKey =
  | 'name'
  | 'email'
  | 'department'
  | 'manager'
  | 'status'
  | 'license_count'
  | 'start_date'
  | 'monthly_cost'
  | 'tools'
  | 'termination_date'
  | 'days_since_offboarding'
  | 'pending_licenses';

export interface EmployeeColumn {
  key: EmployeeColumnKey;
  sortKey?: string; // The API sort key if different from key
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
  width?: string;
}

// Default column configurations
export const EMPLOYEE_COLUMNS: Record<EmployeeColumnKey, EmployeeColumn> = {
  name: { key: 'name', sortKey: 'full_name', sortable: true, align: 'left' },
  email: { key: 'email', sortKey: 'email', sortable: true, align: 'left' },
  department: { key: 'department', sortKey: 'department', sortable: true, align: 'left' },
  manager: { key: 'manager', sortable: false, align: 'left' },
  status: { key: 'status', sortKey: 'status', sortable: true, align: 'left' },
  license_count: { key: 'license_count', sortKey: 'license_count', sortable: true, align: 'right' },
  start_date: { key: 'start_date', sortKey: 'start_date', sortable: true, align: 'left' },
  monthly_cost: { key: 'monthly_cost', sortable: false, align: 'right' },
  tools: { key: 'tools', sortable: false, align: 'left' },
  termination_date: { key: 'termination_date', sortKey: 'termination_date', sortable: true, align: 'left' },
  days_since_offboarding: { key: 'days_since_offboarding', sortable: false, align: 'left' },
  pending_licenses: { key: 'pending_licenses', sortable: false, align: 'left' },
};

interface EmployeeTableProps {
  employees: EmployeeTableData[];
  columns: EmployeeColumnKey[];
  loading?: boolean;
  emptyMessage?: string;
  emptyDescription?: string;
  // Sorting
  sortable?: boolean;
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  onSort?: (column: string) => void;
  // Pagination
  pagination?: {
    page: number;
    totalPages: number;
    onPageChange: (page: number) => void;
  };
  // Row interaction
  onRowClick?: (employee: EmployeeTableData) => void;
  linkToEmployee?: boolean; // Auto-link to /users/{id}
  // Display options
  showAvatar?: boolean;
  showAdminAccountBadge?: boolean;
  showManualBadge?: boolean;
  showChevron?: boolean;
  compact?: boolean;
}

export function EmployeeTable({
  employees,
  columns,
  loading = false,
  emptyMessage,
  emptyDescription,
  sortable = false,
  sortColumn,
  sortDirection = 'asc',
  onSort,
  pagination,
  onRowClick,
  linkToEmployee = false,
  showAvatar = true,
  showAdminAccountBadge = true,
  showManualBadge = true,
  showChevron = false,
  compact = false,
}: EmployeeTableProps) {
  const t = useTranslations('employees');
  const tCommon = useTranslations('common');
  const tReports = useTranslations('reports');
  const router = useRouter();
  const { formatDate, formatCurrency } = useLocale();

  const handleRowClick = (employee: EmployeeTableData) => {
    if (onRowClick) {
      onRowClick(employee);
    } else if (linkToEmployee) {
      router.push(`/users/${employee.id}`);
    }
  };

  const isClickable = !!onRowClick || linkToEmployee;

  // Sort icon component
  const SortIcon = ({ column }: { column: string }) => {
    if (!sortable || sortColumn !== column) {
      return <ChevronUp className="h-3 w-3 opacity-0 group-hover:opacity-30" />;
    }
    return sortDirection === 'asc'
      ? <ChevronUp className="h-3 w-3" />
      : <ChevronDown className="h-3 w-3" />;
  };

  // Get column header text
  const getColumnHeader = (key: EmployeeColumnKey): string => {
    switch (key) {
      case 'name': return tCommon('name');
      case 'email': return tCommon('email');
      case 'department': return t('department');
      case 'manager': return tCommon('manager');
      case 'status': return tCommon('status');
      case 'license_count': return t('licenseCount');
      case 'start_date': return t('startDate');
      case 'monthly_cost': return tReports('monthlyCost');
      case 'tools': return tReports('tools');
      case 'termination_date': return tReports('termination');
      case 'days_since_offboarding': return tReports('daysSince');
      case 'pending_licenses': return tReports('pendingLicenses');
      default: return key;
    }
  };

  // Render cell content based on column
  const renderCell = (employee: EmployeeTableData, columnKey: EmployeeColumnKey) => {
    const isOffboarded = employee.status === 'offboarded';

    switch (columnKey) {
      case 'name':
        return (
          <div className="flex items-center gap-2">
            {showAvatar && (
              employee.avatar ? (
                <img
                  src={employee.avatar}
                  alt=""
                  className={`rounded-full object-cover flex-shrink-0 ${compact ? 'h-6 w-6' : 'h-7 w-7'}`}
                />
              ) : (
                <div className={`rounded-full flex items-center justify-center flex-shrink-0 ${
                  isOffboarded ? 'bg-red-100' : 'bg-zinc-100'
                } ${compact ? 'h-6 w-6' : 'h-7 w-7'}`}>
                  <span className={`font-medium ${isOffboarded ? 'text-red-600' : 'text-zinc-600'} ${compact ? 'text-[10px]' : 'text-xs'}`}>
                    {employee.full_name.charAt(0)}
                  </span>
                </div>
              )
            )}
            <div className="min-w-0">
              <span className={`font-medium ${isOffboarded ? 'line-through text-muted-foreground' : ''}`}>
                {employee.full_name}
              </span>
              {compact && employee.email && (
                <p className="text-xs text-muted-foreground truncate">{employee.email}</p>
              )}
            </div>
          </div>
        );

      case 'email':
        return <span className="text-muted-foreground">{employee.email}</span>;

      case 'department':
        return <span className="text-muted-foreground">{employee.department || '-'}</span>;

      case 'manager':
        if (!employee.manager) return <span className="text-muted-foreground">-</span>;
        return (
          <Link
            href={`/users/${employee.manager.id}`}
            className="hover:text-foreground hover:underline text-muted-foreground"
            onClick={(e) => e.stopPropagation()}
          >
            {employee.manager.full_name}
          </Link>
        );

      case 'status':
        return (
          <div className="flex items-center gap-1.5">
            {isOffboarded ? (
              <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50 text-xs">
                <Skull className="h-3 w-3 mr-1" />
                {t('offboarded')}
              </Badge>
            ) : (
              <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 border-0">
                {t('active')}
              </Badge>
            )}
            {showManualBadge && employee.is_manual && (
              <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                {t('manual')}
              </Badge>
            )}
          </div>
        );

      case 'license_count':
        return (
          <div className="flex items-center gap-1.5 justify-end">
            <Badge variant="outline" className="tabular-nums">{employee.license_count ?? 0}</Badge>
            {showAdminAccountBadge && (employee.owned_admin_account_count || 0) > 0 && (
              <Badge variant="outline" className="tabular-nums bg-purple-50 text-purple-700 border-purple-200">
                +{employee.owned_admin_account_count} {t('adminAccounts')}
              </Badge>
            )}
          </div>
        );

      case 'start_date':
        return (
          <div className="flex items-center justify-between text-muted-foreground tabular-nums">
            <span>{formatDate(employee.start_date)}</span>
            {showChevron && <ChevronRight className="h-4 w-4 text-zinc-300" />}
          </div>
        );

      case 'monthly_cost':
        return (
          <span className="font-medium tabular-nums">
            {employee.total_monthly_cost != null ? formatCurrency(employee.total_monthly_cost) : '-'}
          </span>
        );

      case 'tools':
        if (!employee.licenses || employee.licenses.length === 0) {
          return <span className="text-muted-foreground">-</span>;
        }
        return (
          <div className="flex flex-wrap gap-1">
            {employee.licenses.slice(0, 3).map((lic, i) => (
              <Badge key={i} variant="outline" className="text-xs">{lic.provider_name}</Badge>
            ))}
            {employee.licenses.length > 3 && (
              <Badge variant="secondary" className="text-xs">+{employee.licenses.length - 3}</Badge>
            )}
          </div>
        );

      case 'termination_date':
        return (
          <span className="text-muted-foreground">
            {employee.termination_date ? formatDate(employee.termination_date) : '-'}
          </span>
        );

      case 'days_since_offboarding':
        if (employee.days_since_offboarding == null) return '-';
        return (
          <Badge variant="destructive" className="tabular-nums">
            {employee.days_since_offboarding}d
          </Badge>
        );

      case 'pending_licenses':
        if (!employee.pending_licenses || employee.pending_licenses.length === 0) {
          return <span className="text-muted-foreground">-</span>;
        }
        return (
          <div className="flex flex-wrap gap-1">
            {employee.pending_licenses.map((lic, i) => (
              <Badge key={i} variant="outline">{lic.provider}</Badge>
            ))}
          </div>
        );

      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Table */}
      <div className="border rounded-lg bg-white overflow-hidden overflow-x-auto">
        {employees.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
            <Users className="h-8 w-8 mb-2 opacity-30" />
            <p className="text-sm">{emptyMessage || t('noEmployees')}</p>
            {emptyDescription && <p className="text-xs mt-1">{emptyDescription}</p>}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-zinc-50/50">
                {columns.map((columnKey) => {
                  const column = EMPLOYEE_COLUMNS[columnKey];
                  const isSortable = sortable && column.sortable;
                  const sortKey = column.sortKey || columnKey;

                  return (
                    <th
                      key={columnKey}
                      className={`px-4 py-3 font-medium text-muted-foreground ${
                        column.align === 'right' ? 'text-right' :
                        column.align === 'center' ? 'text-center' : 'text-left'
                      }`}
                    >
                      {isSortable ? (
                        <button
                          onClick={() => onSort?.(sortKey)}
                          className="flex items-center gap-1.5 hover:text-foreground group"
                        >
                          {getColumnHeader(columnKey)}
                          <SortIcon column={sortKey} />
                        </button>
                      ) : (
                        getColumnHeader(columnKey)
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {employees.map((employee) => (
                <tr
                  key={employee.id}
                  onClick={() => handleRowClick(employee)}
                  className={`border-b last:border-0 hover:bg-zinc-50/50 transition-colors ${
                    isClickable ? 'cursor-pointer' : ''
                  }`}
                >
                  {columns.map((columnKey) => {
                    const column = EMPLOYEE_COLUMNS[columnKey];
                    return (
                      <td
                        key={columnKey}
                        className={`px-4 ${compact ? 'py-2' : 'py-3'} ${
                          column.align === 'right' ? 'text-right' :
                          column.align === 'center' ? 'text-center' : 'text-left'
                        }`}
                      >
                        {renderCell(employee, columnKey)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {pagination && pagination.totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {tCommon('page')} {pagination.page} {tCommon('of')} {pagination.totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(pagination.page - 1)}
              disabled={pagination.page === 1}
            >
              {tCommon('back')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page === pagination.totalPages}
            >
              {tCommon('next')}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper function to convert API employee data to table format
export function mapEmployeeToTableData(employee: any): EmployeeTableData {
  return {
    id: employee.id || employee.employee_id,
    full_name: employee.full_name || employee.employee_name,
    email: employee.email || employee.employee_email,
    avatar: employee.avatar,
    department: employee.department,
    status: employee.status,
    is_manual: employee.is_manual,
    manager: employee.manager,
    license_count: employee.license_count,
    owned_admin_account_count: employee.owned_admin_account_count,
    start_date: employee.start_date,
    termination_date: employee.termination_date,
    total_monthly_cost: employee.total_monthly_cost,
    licenses: employee.licenses,
    days_since_offboarding: employee.days_since_offboarding,
    pending_licenses: employee.pending_licenses,
  };
}
