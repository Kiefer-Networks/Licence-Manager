'use client';

import { useEffect, useState } from 'react';
import { api, Employee, EmployeeCreate, EmployeeUpdate } from '@/lib/api';

interface ManualEmployeeTranslations {
  t: (key: string, params?: Record<string, string | number>) => string;
}

interface UseManualEmployeeProps {
  open: boolean;
  employee?: Employee | null;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  showToast: (type: 'success' | 'error' | 'info', text: string) => void;
  translations: ManualEmployeeTranslations;
}

export interface ManualEmployeeFormData {
  email: string;
  full_name: string;
  department: string;
  status: 'active' | 'offboarded';
  start_date: string;
  termination_date: string;
  manager_email: string;
}

export interface UseManualEmployeeReturn {
  saving: boolean;
  formData: ManualEmployeeFormData;
  setFormData: (data: ManualEmployeeFormData) => void;
  errors: Record<string, string>;
  managerSearchQuery: string;
  setManagerSearchQuery: (value: string) => void;
  managerResults: Employee[];
  showManagerResults: boolean;
  setShowManagerResults: (value: boolean) => void;
  loadingManagers: boolean;
  isEdit: boolean;
  handleSelectManager: (manager: Employee) => void;
  handleClearManager: () => void;
  handleSubmit: () => Promise<void>;
}

/**
 * Custom hook that encapsulates all business logic for the ManualEmployeeDialog component.
 * Manages form state, validation, manager autocomplete search, and create/update operations.
 */
export function useManualEmployee({
  open,
  employee,
  onOpenChange,
  onSuccess,
  showToast,
  translations,
}: UseManualEmployeeProps): UseManualEmployeeReturn {
  const { t } = translations;

  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<ManualEmployeeFormData>({
    email: '',
    full_name: '',
    department: '',
    status: 'active',
    start_date: '',
    termination_date: '',
    manager_email: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Manager autocomplete state
  const [managerSearchQuery, setManagerSearchQuery] = useState('');
  const [managerResults, setManagerResults] = useState<Employee[]>([]);
  const [showManagerResults, setShowManagerResults] = useState(false);
  const [loadingManagers, setLoadingManagers] = useState(false);

  const isEdit = !!employee;

  // Reset form when dialog opens or employee changes
  useEffect(() => {
    if (open) {
      if (employee) {
        setFormData({
          email: employee.email || '',
          full_name: employee.full_name || '',
          department: employee.department || '',
          status: (employee.status as 'active' | 'offboarded') || 'active',
          start_date: employee.start_date || '',
          termination_date: employee.termination_date || '',
          manager_email: employee.manager?.email || '',
        });
        setManagerSearchQuery(employee.manager?.full_name || '');
      } else {
        setFormData({
          email: '',
          full_name: '',
          department: '',
          status: 'active',
          start_date: '',
          termination_date: '',
          manager_email: '',
        });
        setManagerSearchQuery('');
      }
      setErrors({});
      setShowManagerResults(false);
      setManagerResults([]);
    }
  }, [open, employee]);

  // Debounced manager search
  useEffect(() => {
    if (!open) return;

    const timer = setTimeout(async () => {
      const query = managerSearchQuery.trim();
      if (query.length < 2) {
        setManagerResults([]);
        return;
      }

      setLoadingManagers(true);
      try {
        const response = await api.getEmployees({
          page_size: 10,
          status: 'active',
          search: query,
        });
        // Filter out current employee being edited
        const filtered = employee
          ? response.items.filter((emp) => emp.id !== employee.id)
          : response.items;
        setManagerResults(filtered);
      } catch {
        setManagerResults([]);
      } finally {
        setLoadingManagers(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [managerSearchQuery, open, employee]);

  const handleSelectManager = (manager: Employee) => {
    setFormData({ ...formData, manager_email: manager.email });
    setManagerSearchQuery(manager.full_name);
    setShowManagerResults(false);
  };

  const handleClearManager = () => {
    setFormData({ ...formData, manager_email: '' });
    setManagerSearchQuery('');
    setShowManagerResults(false);
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.email.trim()) {
      newErrors.email = t('emailRequired');
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = t('invalidEmailFormat');
    }

    if (!formData.full_name.trim()) {
      newErrors.full_name = t('fullNameRequired');
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setSaving(true);
    try {
      if (isEdit && employee) {
        const updateData: EmployeeUpdate = {
          email: formData.email.trim(),
          full_name: formData.full_name.trim(),
          department: formData.department || undefined,
          status: formData.status,
          start_date: formData.start_date || undefined,
          termination_date: formData.termination_date || undefined,
          manager_email: formData.manager_email.trim() || undefined,
        };
        await api.updateEmployee(employee.id, updateData);
        showToast('success', t('employeeUpdated'));
      } else {
        const createData: EmployeeCreate = {
          email: formData.email.trim(),
          full_name: formData.full_name.trim(),
          department: formData.department || undefined,
          status: formData.status,
          start_date: formData.start_date || undefined,
          termination_date: formData.termination_date || undefined,
          manager_email: formData.manager_email.trim() || undefined,
        };
        await api.createEmployee(createData);
        showToast('success', t('employeeCreated'));
      }
      onSuccess();
      onOpenChange(false);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (errorMessage.includes('email already exists')) {
        setErrors({ email: t('emailAlreadyExists') });
      } else {
        showToast('error', errorMessage);
      }
    } finally {
      setSaving(false);
    }
  };

  return {
    saving,
    formData,
    setFormData,
    errors,
    managerSearchQuery,
    setManagerSearchQuery,
    managerResults,
    showManagerResults,
    setShowManagerResults,
    loadingManagers,
    isEdit,
    handleSelectManager,
    handleClearManager,
    handleSubmit,
  };
}
