'use client';

import { useEffect, useState } from 'react';
import { api, Employee, EmployeeSource, Provider } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import { useDebounce } from '@/hooks/use-debounce';

/**
 * Translation functions required by the useEmployees hook.
 */
interface EmployeesTranslations {
  t: (key: string) => string;
}

/**
 * Return type for the useEmployees hook.
 */
export interface UseEmployeesReturn {
  // Data
  employees: Employee[];
  providers: Provider[];
  departments: string[];
  loading: boolean;
  total: number;
  toast: { type: 'success' | 'error' | 'info'; text: string } | null;

  // Filters
  search: string;
  setSearch: (value: string) => void;
  selectedStatus: string;
  setSelectedStatus: (value: string) => void;
  selectedDepartment: string;
  setSelectedDepartment: (value: string) => void;
  selectedSource: string;
  setSelectedSource: (value: string) => void;

  // Sorting
  sortColumn: string;
  sortDirection: 'asc' | 'desc';
  handleSort: (column: string) => void;

  // Pagination
  page: number;
  setPage: (page: number) => void;
  totalPages: number;

  // Tabs
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // Dialogs
  showAddEmployee: boolean;
  setShowAddEmployee: (show: boolean) => void;
  showImportDialog: boolean;
  setShowImportDialog: (show: boolean) => void;

  // Handlers
  showToast: (type: 'success' | 'error' | 'info', text: string) => void;
  loadEmployees: () => void;
}

/**
 * Custom hook that encapsulates all business logic for the Users/Employees page.
 * Manages employee data, filters, sorting, pagination, and dialogs.
 */
export function useEmployees(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _translations?: EmployeesTranslations,
): UseEmployeesReturn {
  // Data state
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Filter state
  const [search, setSearch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [selectedSource, setSelectedSource] = useState<string>('all');

  // Sorting state
  const [sortColumn, setSortColumn] = useState<string>('full_name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Pagination state
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const totalPages = Math.ceil(total / pageSize);

  // Tab state
  const [activeTab, setActiveTab] = useState<string>('employees');

  // Dialog state
  const [showAddEmployee, setShowAddEmployee] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);

  const debouncedSearch = useDebounce(search, 300);

  const showToast = (type: 'success' | 'error' | 'info', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 4000);
  };

  const handleSort = (column: string) => {
    setPage(1); // Reset to first page when sorting changes
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  // Load departments and providers on mount
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
    }).catch((e) => {
      handleSilentError('loadEmployees', e);
      setLoading(false);
    });
  };

  // Load employees when filters/pagination/sorting change
  useEffect(() => {
    loadEmployees();
  }, [page, debouncedSearch, selectedStatus, selectedDepartment, selectedSource, sortColumn, sortDirection]);

  return {
    // Data
    employees,
    providers,
    departments,
    loading,
    total,
    toast,

    // Filters
    search,
    setSearch,
    selectedStatus,
    setSelectedStatus,
    selectedDepartment,
    setSelectedDepartment,
    selectedSource,
    setSelectedSource,

    // Sorting
    sortColumn,
    sortDirection,
    handleSort,

    // Pagination
    page,
    setPage,
    totalPages,

    // Tabs
    activeTab,
    setActiveTab,

    // Dialogs
    showAddEmployee,
    setShowAddEmployee,
    showImportDialog,
    setShowImportDialog,

    // Handlers
    showToast,
    loadEmployees,
  };
}
