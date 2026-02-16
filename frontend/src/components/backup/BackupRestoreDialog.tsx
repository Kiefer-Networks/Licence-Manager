'use client';

import { useTranslations } from 'next-intl';
import { Upload, Loader2, AlertTriangle, Eye, EyeOff, CheckCircle2, XCircle, FileArchive } from 'lucide-react';
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
import { BackupRestoreResponse } from '@/lib/api';
import { useBackupRestore } from '@/hooks/use-backup-restore';

interface BackupRestoreDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (result: BackupRestoreResponse) => void;
  onError?: (error: string) => void;
}

export function BackupRestoreDialog({
  open,
  onOpenChange,
  onSuccess,
  onError,
}: BackupRestoreDialogProps) {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');

  const {
    file,
    password,
    setPassword,
    showPassword,
    setShowPassword,
    confirmed,
    setConfirmed,
    isLoading,
    error,
    result,
    isDragging,
    canSubmit,
    handleFileSelect,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    handleRestore,
    handleClose,
  } = useBackupRestore({
    onOpenChange,
    onSuccess,
    onError,
    fallbackErrorMessage: t('restoreFailed'),
    invalidFileMessage: t('selectBackupFile'),
  });

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            {t('importBackup')}
          </DialogTitle>
          <DialogDescription>
            {t('importBackupDescription')}
          </DialogDescription>
        </DialogHeader>

        {result?.success ? (
          <div className="space-y-4 py-4">
            <div className="flex items-center gap-3 rounded-lg bg-green-50 p-4 text-green-700">
              <CheckCircle2 className="h-6 w-6 flex-shrink-0" />
              <div>
                <p className="font-medium">{t('importSuccessful')}</p>
                <p className="text-sm mt-1">{t('allDataRestored')}</p>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-sm font-medium text-zinc-700">{t('importedData')}</p>

              {/* User & Access Control */}
              <div className="space-y-1">
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide">{t('usersAndAccess')}</p>
                <div className="grid grid-cols-2 gap-1.5 text-sm">
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('adminUsers')}</span>
                    <span className="font-medium">{result.imported.admin_users}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('roles')}</span>
                    <span className="font-medium">{result.imported.roles}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('permissions')}</span>
                    <span className="font-medium">{result.imported.permissions}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('userRoles')}</span>
                    <span className="font-medium">{result.imported.user_roles}</span>
                  </div>
                </div>
              </div>

              {/* Core Data */}
              <div className="space-y-1">
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide">{t('coreData')}</p>
                <div className="grid grid-cols-2 gap-1.5 text-sm">
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('providers')}</span>
                    <span className="font-medium">{result.imported.providers}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('licenses')}</span>
                    <span className="font-medium">{result.imported.licenses}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('employees')}</span>
                    <span className="font-medium">{result.imported.employees}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('packages')}</span>
                    <span className="font-medium">{result.imported.license_packages}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('files')}</span>
                    <span className="font-medium">{result.imported.provider_files}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('paymentMethods')}</span>
                    <span className="font-medium">{result.imported.payment_methods}</span>
                  </div>
                </div>
              </div>

              {/* Configuration */}
              <div className="space-y-1">
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide">{t('configuration')}</p>
                <div className="grid grid-cols-2 gap-1.5 text-sm">
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{tCommon('settings')}</span>
                    <span className="font-medium">{result.imported.settings}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('notificationRules')}</span>
                    <span className="font-medium">{result.imported.notification_rules}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('accountPatterns')}</span>
                    <span className="font-medium">{result.imported.service_account_patterns + result.imported.admin_account_patterns}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('costSnapshots')}</span>
                    <span className="font-medium">{result.imported.cost_snapshots}</span>
                  </div>
                  <div className="flex justify-between bg-zinc-50 rounded px-3 py-1">
                    <span className="text-zinc-600">{t('auditLogs')}</span>
                    <span className="font-medium">{result.imported.audit_logs}</span>
                  </div>
                </div>
              </div>
            </div>

            {result.validation.providers_failed.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-amber-700">
                  {t('providerValidation')} ({result.validation.providers_valid}/{result.validation.providers_tested} {t('valid')}):
                </p>
                <div className="bg-amber-50 rounded-lg p-3">
                  <ul className="text-sm text-amber-700 space-y-1">
                    {result.validation.providers_failed.map((error, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <XCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                        <span>{error}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            <DialogFooter>
              <Button onClick={handleClose}>{tCommon('close')}</Button>
            </DialogFooter>
          </div>
        ) : (
          <>
            <div className="space-y-4 py-2">
              {error && (
                <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* File Drop Zone */}
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                className={`relative border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                  isDragging
                    ? 'border-blue-500 bg-blue-50'
                    : file
                    ? 'border-green-500 bg-green-50'
                    : 'border-zinc-300 hover:border-zinc-400'
                }`}
              >
                <input
                  type="file"
                  accept=".lcbak"
                  onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  disabled={isLoading}
                />
                {file ? (
                  <div className="flex items-center justify-center gap-2 text-green-700">
                    <FileArchive className="h-8 w-8" />
                    <div className="text-left">
                      <p className="font-medium">{file.name}</p>
                      <p className="text-xs text-green-600">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-zinc-500">
                    <FileArchive className="h-10 w-10 mx-auto mb-2" />
                    <p className="font-medium">{t('dropFileHere')}</p>
                    <p className="text-xs mt-1">{t('clickToSelect')} (.lcbak)</p>
                  </div>
                )}
              </div>

              {/* Password Input */}
              <div className="space-y-2">
                <Label htmlFor="restorePassword" className="text-sm font-medium">
                  {t('backupPassword')}
                </Label>
                <div className="relative">
                  <Input
                    id="restorePassword"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={t('backupPasswordInput')}
                    disabled={isLoading}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Warning */}
              <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium">{t('dataLossWarning')}</p>
                  <p className="text-xs mt-1">
                    {t('dataLossDescription')}
                  </p>
                </div>
              </div>

              {/* Confirmation Checkbox */}
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                  disabled={isLoading}
                  className="mt-1 h-4 w-4 rounded border-zinc-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-zinc-700">
                  {t('confirmDataLoss')}
                </span>
              </label>
            </div>

            <DialogFooter>
              <Button variant="ghost" onClick={handleClose} disabled={isLoading}>
                {tCommon('cancel')}
              </Button>
              <Button
                onClick={handleRestore}
                disabled={!canSubmit || isLoading}
                variant="destructive"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('importing')}
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    {t('import')}
                  </>
                )}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
