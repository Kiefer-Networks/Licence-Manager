'use client';

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
import { Employee } from '@/lib/api';
import { Loader2, Search, X, User } from 'lucide-react';
import { useManualEmployee } from '@/hooks/use-manual-employee';

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

  const {
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
  } = useManualEmployee({
    open,
    employee,
    onOpenChange,
    onSuccess,
    showToast,
    translations: { t },
  });

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
