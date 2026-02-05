'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { api, Employee, EmployeeCreate, EmployeeUpdate } from '@/lib/api';
import { Loader2, Search, X, User } from 'lucide-react';

interface ManualEmployeeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  employee?: Employee | null;
  departments: string[];
  onSuccess: () => void;
  showToast: (type: 'success' | 'error' | 'info', text: string) => void;
}

export function ManualEmployeeDialog({
  open,
  onOpenChange,
  employee,
  departments,
  onSuccess,
  showToast,
}: ManualEmployeeDialogProps) {
  const t = useTranslations('employees');
  const tCommon = useTranslations('common');

  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    full_name: '',
    department: '',
    status: 'active' as 'active' | 'offboarded',
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? t('editEmployee') : t('addEmployee')}
          </DialogTitle>
          <DialogDescription>
            {isEdit ? t('updateEmployee') : t('createEmployee')}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Email */}
          <div className="grid gap-2">
            <Label htmlFor="email">
              {tCommon('email')} <span className="text-red-500">*</span>
            </Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="john.doe@company.com"
              maxLength={255}
              className={errors.email ? 'border-red-500' : ''}
            />
            {errors.email && (
              <p className="text-sm text-red-500">{errors.email}</p>
            )}
          </div>

          {/* Full Name */}
          <div className="grid gap-2">
            <Label htmlFor="full_name">
              {t('fullName')} <span className="text-red-500">*</span>
            </Label>
            <Input
              id="full_name"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              placeholder="John Doe"
              maxLength={255}
              className={errors.full_name ? 'border-red-500' : ''}
            />
            {errors.full_name && (
              <p className="text-sm text-red-500">{errors.full_name}</p>
            )}
          </div>

          {/* Department */}
          <div className="grid gap-2">
            <Label htmlFor="department">{t('department')}</Label>
            <Select
              value={formData.department || '_none'}
              onValueChange={(value) =>
                setFormData({ ...formData, department: value === '_none' ? '' : value })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder={t('department')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_none">{tCommon('none')}</SelectItem>
                {departments.map((dept) => (
                  <SelectItem key={dept} value={dept}>
                    {dept}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Status */}
          <div className="grid gap-2">
            <Label htmlFor="status">{tCommon('status')}</Label>
            <Select
              value={formData.status}
              onValueChange={(value: 'active' | 'offboarded') =>
                setFormData({ ...formData, status: value })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">{t('active')}</SelectItem>
                <SelectItem value="offboarded">{t('offboarded')}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Start Date */}
          <div className="grid gap-2">
            <Label htmlFor="start_date">{t('startDate')}</Label>
            <Input
              id="start_date"
              type="date"
              value={formData.start_date}
              onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
            />
          </div>

          {/* Termination Date */}
          {formData.status === 'offboarded' && (
            <div className="grid gap-2">
              <Label htmlFor="termination_date">{t('terminationDate')}</Label>
              <Input
                id="termination_date"
                type="date"
                value={formData.termination_date}
                onChange={(e) =>
                  setFormData({ ...formData, termination_date: e.target.value })
                }
              />
            </div>
          )}

          {/* Manager */}
          <div className="grid gap-2">
            <Label htmlFor="manager_email">{tCommon('manager')}</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
              <Input
                id="manager_email"
                value={managerSearchQuery}
                onChange={(e) => {
                  setManagerSearchQuery(e.target.value);
                  setShowManagerResults(true);
                  if (!e.target.value) {
                    setFormData({ ...formData, manager_email: '' });
                  }
                }}
                onFocus={() => setShowManagerResults(true)}
                placeholder={t('searchManager')}
                maxLength={255}
                className="pl-9 pr-9"
              />
              {managerSearchQuery && (
                <button
                  type="button"
                  onClick={handleClearManager}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}

              {/* Autocomplete dropdown */}
              {showManagerResults && managerSearchQuery.length >= 2 && (
                <div className="absolute z-50 w-full mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                  {loadingManagers ? (
                    <div className="flex items-center justify-center py-3">
                      <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
                    </div>
                  ) : managerResults.length > 0 ? (
                    managerResults.map((emp) => (
                      <button
                        key={emp.id}
                        type="button"
                        onClick={() => handleSelectManager(emp)}
                        className="w-full px-3 py-2 text-left hover:bg-zinc-50 flex items-center gap-2"
                      >
                        {emp.avatar ? (
                          <img
                            src={emp.avatar}
                            alt=""
                            className="h-6 w-6 rounded-full object-cover"
                          />
                        ) : (
                          <div className="h-6 w-6 rounded-full bg-zinc-100 flex items-center justify-center">
                            <User className="h-3 w-3 text-zinc-500" />
                          </div>
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate">{emp.full_name}</p>
                          <p className="text-xs text-muted-foreground truncate">{emp.email}</p>
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="py-3 text-center text-sm text-muted-foreground">
                      {t('noManagersFound')}
                    </div>
                  )}
                </div>
              )}
            </div>
            {formData.manager_email && (
              <p className="text-xs text-muted-foreground">{formData.manager_email}</p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            {tCommon('cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={saving}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isEdit ? t('updateEmployee') : t('createEmployee')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
