'use client';

import { useEffect, useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { api, BackupConfig, StoredBackup, BackupListResponse } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import {
  Loader2,
  Database,
  Clock,
  Download,
  Trash2,
  Play,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Calendar,
  HardDrive,
  RotateCcw,
} from 'lucide-react';

interface BackupsTabProps {
  showToast: (type: 'success' | 'error', message: string) => void;
}

const SCHEDULE_PRESETS = [
  { value: '0 2 * * *', label: 'daily' },
  { value: '0 2 * * 0', label: 'weekly' },
  { value: '0 2 1 * *', label: 'monthly' },
];

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function BackupsTab({ showToast }: BackupsTabProps) {
  const t = useTranslations('settings.scheduledBackup');
  const tCommon = useTranslations('common');

  // Config state
  const [config, setConfig] = useState<BackupConfig>({
    enabled: false,
    schedule: '0 2 * * *',
    retention_count: 7,
    password_configured: false,
  });
  const [loading, setLoading] = useState(true);
  const [savingConfig, setSavingConfig] = useState(false);

  // Backups list state
  const [backups, setBackups] = useState<StoredBackup[]>([]);
  const [nextScheduled, setNextScheduled] = useState<string | null>(null);
  const [lastBackup, setLastBackup] = useState<string | null>(null);

  // Password dialog state
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [savingPassword, setSavingPassword] = useState(false);

  // Trigger backup state
  const [triggeringBackup, setTriggeringBackup] = useState(false);

  // Download state
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [backupToDelete, setBackupToDelete] = useState<StoredBackup | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Restore dialog state
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);
  const [backupToRestore, setBackupToRestore] = useState<StoredBackup | null>(null);
  const [restorePassword, setRestorePassword] = useState('');
  const [restoring, setRestoring] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const response = await api.listBackups();
      setConfig(response.config);
      setBackups(response.backups);
      setNextScheduled(response.next_scheduled);
      setLastBackup(response.last_backup);
    } catch (error) {
      handleSilentError('fetchBackups', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleSaveConfig() {
    setSavingConfig(true);
    try {
      const updated = await api.updateBackupConfig({
        enabled: config.enabled,
        schedule: config.schedule,
        retention_count: config.retention_count,
      });
      setConfig(updated);
      showToast('success', t('configSaved'));
    } catch (error) {
      handleSilentError('updateBackupConfig', error);
      showToast('error', tCommon('operationFailed'));
    } finally {
      setSavingConfig(false);
    }
  }

  async function handleSavePassword() {
    if (newPassword !== confirmPassword) {
      showToast('error', tCommon('operationFailed'));
      return;
    }
    if (newPassword.length < 12) {
      showToast('error', tCommon('operationFailed'));
      return;
    }

    setSavingPassword(true);
    try {
      const updated = await api.updateBackupConfig({
        password: newPassword,
      });
      setConfig(updated);
      setPasswordDialogOpen(false);
      setNewPassword('');
      setConfirmPassword('');
      showToast('success', t('configSaved'));
    } catch (error) {
      handleSilentError('updateBackupPassword', error);
      showToast('error', tCommon('operationFailed'));
    } finally {
      setSavingPassword(false);
    }
  }

  async function handleTriggerBackup() {
    setTriggeringBackup(true);
    try {
      const backup = await api.triggerBackup();
      setBackups((prev) => [backup, ...prev]);
      setLastBackup(backup.created_at);
      showToast('success', t('backupCreated'));
    } catch (error) {
      handleSilentError('triggerBackup', error);
      const message = error instanceof Error ? error.message : tCommon('operationFailed');
      showToast('error', message);
    } finally {
      setTriggeringBackup(false);
    }
  }

  async function handleDownloadBackup(backup: StoredBackup) {
    setDownloadingId(backup.id);
    try {
      const blob = await api.downloadStoredBackup(backup.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = backup.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      handleSilentError('downloadBackup', error);
      showToast('error', tCommon('operationFailed'));
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleDeleteBackup() {
    if (!backupToDelete) return;

    setDeleting(true);
    try {
      await api.deleteStoredBackup(backupToDelete.id);
      setBackups((prev) => prev.filter((b) => b.id !== backupToDelete.id));
      setDeleteDialogOpen(false);
      setBackupToDelete(null);
      showToast('success', t('backupDeleted'));
    } catch (error) {
      handleSilentError('deleteBackup', error);
      showToast('error', tCommon('operationFailed'));
    } finally {
      setDeleting(false);
    }
  }

  async function handleRestoreBackup() {
    if (!backupToRestore || !restorePassword) return;

    setRestoring(true);
    try {
      await api.restoreFromStoredBackup(backupToRestore.id, restorePassword);
      setRestoreDialogOpen(false);
      setBackupToRestore(null);
      setRestorePassword('');
      showToast('success', t('restored'));
      // Reload the page after successful restore
      window.location.reload();
    } catch (error) {
      handleSilentError('restoreBackup', error);
      const message = error instanceof Error ? error.message : tCommon('operationFailed');
      showToast('error', message);
    } finally {
      setRestoring(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Schedule Configuration */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-medium">{t('title')}</h2>
          </div>
        </div>

        <div className="border rounded-lg bg-white p-4 space-y-6">
          <p className="text-xs text-muted-foreground">{t('description')}</p>

          {/* Enable Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-sm font-medium">{t('enableScheduled')}</Label>
            </div>
            <Switch
              checked={config.enabled}
              onCheckedChange={(checked) => setConfig({ ...config, enabled: checked })}
            />
          </div>

          {/* Schedule */}
          <div className="space-y-2">
            <Label className="text-xs font-medium">{t('schedule')}</Label>
            <div className="flex gap-2">
              <Input
                value={config.schedule}
                onChange={(e) => setConfig({ ...config, schedule: e.target.value })}
                placeholder="0 2 * * *"
                className="flex-1 font-mono text-sm"
              />
              <Select
                value={
                  SCHEDULE_PRESETS.find((p) => p.value === config.schedule)?.value || ''
                }
                onValueChange={(value) => setConfig({ ...config, schedule: value })}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder={t('presets.label')} />
                </SelectTrigger>
                <SelectContent>
                  {SCHEDULE_PRESETS.map((preset) => (
                    <SelectItem key={preset.value} value={preset.value}>
                      {t(`presets.${preset.label}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <p className="text-xs text-muted-foreground">{t('scheduleHelp')}</p>
          </div>

          {/* Retention */}
          <div className="space-y-2">
            <Label className="text-xs font-medium">{t('retention')}</Label>
            <Input
              type="number"
              value={config.retention_count}
              onChange={(e) =>
                setConfig({ ...config, retention_count: parseInt(e.target.value) || 7 })
              }
              min={1}
              max={100}
              className="w-32"
            />
            <p className="text-xs text-muted-foreground">{t('retentionHelp')}</p>
          </div>

          {/* Password Configuration */}
          <div className="space-y-2">
            <Label className="text-xs font-medium">{t('password')}</Label>
            <div className="flex items-center gap-3">
              {config.password_configured ? (
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  <Lock className="h-3 w-3 mr-1" />
                  {t('passwordConfigured')}
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  {t('passwordNotConfigured')}
                </Badge>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPasswordDialogOpen(true)}
              >
                {config.password_configured ? t('changePassword') : t('setPassword')}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">{t('passwordHelp')}</p>
          </div>

          <div className="pt-4 border-t">
            <Button size="sm" onClick={handleSaveConfig} disabled={savingConfig}>
              {savingConfig && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {t('saveConfig')}
            </Button>
          </div>
        </div>
      </section>

      {/* Manual Backup */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Play className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-medium">{t('manualBackup')}</h2>
          </div>
        </div>

        <div className="border rounded-lg bg-white p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-4 text-sm">
                <span className="text-muted-foreground">{t('lastBackup')}:</span>
                <span className="font-medium">
                  {lastBackup ? formatDate(lastBackup) : t('never')}
                </span>
              </div>
              {config.enabled && (
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-muted-foreground">{t('nextBackup')}:</span>
                  <span className="font-medium">
                    {nextScheduled ? formatDate(nextScheduled) : t('notScheduled')}
                  </span>
                </div>
              )}
            </div>
            <Button
              onClick={handleTriggerBackup}
              disabled={triggeringBackup || !config.password_configured}
            >
              {triggeringBackup ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Database className="h-4 w-4 mr-2" />
              )}
              {t('triggerBackup')}
            </Button>
          </div>
          {!config.password_configured && (
            <p className="text-xs text-amber-600">{t('backupNotConfigured')}</p>
          )}
        </div>
      </section>

      {/* Stored Backups */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <HardDrive className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-medium">
              {t('storedBackupsCount', {
                count: backups.length,
                max: config.retention_count,
              })}
            </h2>
          </div>
        </div>

        <div className="border rounded-lg bg-white divide-y">
          {backups.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              {t('noBackups')}
            </div>
          ) : (
            backups.map((backup) => (
              <div
                key={backup.id}
                className="p-4 flex items-center justify-between gap-4"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm truncate">
                      {backup.filename}
                    </span>
                    {backup.is_overdue && (
                      <Badge
                        variant="outline"
                        className="bg-amber-50 text-amber-700 border-amber-200"
                      >
                        {t('overdue')}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                    <span>{formatBytes(backup.size_bytes)}</span>
                    <span>{backup.age_description}</span>
                    {backup.metadata && (
                      <span>
                        {backup.metadata.provider_count} {t('providers')},{' '}
                        {backup.metadata.license_count} {t('licenses')},{' '}
                        {backup.metadata.employee_count} {t('employees')}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownloadBackup(backup)}
                    disabled={downloadingId === backup.id}
                  >
                    {downloadingId === backup.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Download className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setBackupToRestore(backup);
                      setRestoreDialogOpen(true);
                    }}
                  >
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setBackupToDelete(backup);
                      setDeleteDialogOpen(true);
                    }}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Password Dialog */}
      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {config.password_configured ? t('changePassword') : t('setPassword')}
            </DialogTitle>
            <DialogDescription>{t('passwordHelp')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{t('password')}</Label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Min. 12 characters"
              />
            </div>
            <div className="space-y-2">
              <Label>{tCommon('confirm')}</Label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPasswordDialogOpen(false)}>
              {tCommon('cancel')}
            </Button>
            <Button
              onClick={handleSavePassword}
              disabled={
                savingPassword ||
                newPassword.length < 12 ||
                newPassword !== confirmPassword
              }
            >
              {savingPassword && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {tCommon('save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>
              {backupToDelete?.filename}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tCommon('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteBackup}
              className="bg-red-600 hover:bg-red-700"
              disabled={deleting}
            >
              {deleting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {tCommon('delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Restore Dialog */}
      <Dialog open={restoreDialogOpen} onOpenChange={setRestoreDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              {t('confirmRestore')}
            </DialogTitle>
            <DialogDescription className="text-red-600 font-medium">
              {t('confirmRestoreWarning')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="p-3 bg-zinc-50 rounded-lg text-sm">
              <span className="font-medium">{backupToRestore?.filename}</span>
              <div className="text-xs text-muted-foreground mt-1">
                {backupToRestore && formatDate(backupToRestore.created_at)}
              </div>
            </div>
            <div className="space-y-2">
              <Label>{t('restorePassword')}</Label>
              <Input
                type="password"
                value={restorePassword}
                onChange={(e) => setRestorePassword(e.target.value)}
                placeholder={t('restorePasswordHelp')}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreDialogOpen(false)}>
              {tCommon('cancel')}
            </Button>
            <Button
              onClick={handleRestoreBackup}
              disabled={restoring || !restorePassword}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {restoring && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {restoring ? t('restoring') : tCommon('confirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
