'use client';

import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Pagination } from '@/components/ui/pagination';
import { SearchInput } from '@/components/ui/search-input';
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
import {
  Loader2,
  Database,
  Clock,
  Download,
  Trash2,
  Play,
  AlertTriangle,
  Lock,
  HardDrive,
  RotateCcw,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
} from 'lucide-react';
import { useBackupsTab } from '@/hooks/use-backups-tab';

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

  const {
    loading,
    savingConfig,
    savingPassword,
    triggeringBackup,
    downloadingId,
    deleting,
    restoring,
    config,
    setConfig,
    backups,
    nextScheduled,
    lastBackup,
    passwordDialogOpen,
    setPasswordDialogOpen,
    newPassword,
    setNewPassword,
    confirmPassword,
    setConfirmPassword,
    deleteDialogOpen,
    setDeleteDialogOpen,
    backupToDelete,
    setBackupToDelete,
    restoreDialogOpen,
    setRestoreDialogOpen,
    backupToRestore,
    setBackupToRestore,
    restorePassword,
    setRestorePassword,
    search,
    setSearch,
    sortColumn,
    sortDirection,
    filterEncrypted,
    setFilterEncrypted,
    page,
    setPage,
    pageSize,
    filteredBackups,
    totalPages,
    paginatedBackups,
    handleSaveConfig,
    handleSavePassword,
    handleTriggerBackup,
    handleDownloadBackup,
    handleDeleteBackup,
    handleRestoreBackup,
    handleSort,
    handleClearFilters,
  } = useBackupsTab(showToast, t, tCommon);

  // Sort icon component
  const SortIcon = ({ column }: { column: 'created_at' | 'size_bytes' | 'filename' }) => {
    if (sortColumn !== column) return <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" />;
    return sortDirection === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />;
  };

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

        <div className="border rounded-lg bg-card p-4 space-y-6">
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
                <Badge variant="outline" className="bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800">
                  <Lock className="h-3 w-3 mr-1" />
                  {t('passwordConfigured')}
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800">
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

        <div className="border rounded-lg bg-card p-4 space-y-4">
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
            <p className="text-xs text-amber-600 dark:text-amber-400">{t('backupNotConfigured')}</p>
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

        {/* Search and Filter */}
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder={t('searchBackups')}
            className="flex-1 min-w-[200px]"
          />
          <Select value={filterEncrypted} onValueChange={(v) => setFilterEncrypted(v as 'all' | 'encrypted' | 'unencrypted')}>
            <SelectTrigger className="w-40 h-9 text-sm">
              <SelectValue placeholder={t('filterEncryption')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{tCommon('all')}</SelectItem>
              <SelectItem value="encrypted">{t('encrypted')}</SelectItem>
              <SelectItem value="unencrypted">{t('unencrypted')}</SelectItem>
            </SelectContent>
          </Select>
          {(search || filterEncrypted !== 'all') && (
            <Button
              variant="ghost"
              size="sm"
              className="h-9 text-sm text-muted-foreground hover:text-foreground"
              onClick={handleClearFilters}
            >
              {tCommon('clear')}
            </Button>
          )}
          <span className="text-sm text-muted-foreground ml-auto">
            {t('backupCount', { count: filteredBackups.length })}
          </span>
        </div>

        {/* Backups Table */}
        <div className="border rounded-lg bg-card overflow-hidden">
          {paginatedBackups.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              {backups.length === 0 ? t('noBackups') : tCommon('noResults')}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button
                      onClick={() => handleSort('filename')}
                      className="flex items-center gap-1.5 hover:text-foreground"
                    >
                      {t('filename')} <SortIcon column="filename" />
                    </button>
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <button
                      onClick={() => handleSort('created_at')}
                      className="flex items-center gap-1.5 hover:text-foreground"
                    >
                      {t('createdAt')} <SortIcon column="created_at" />
                    </button>
                  </th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">
                    <button
                      onClick={() => handleSort('size_bytes')}
                      className="flex items-center gap-1.5 justify-end hover:text-foreground ml-auto"
                    >
                      {t('size')} <SortIcon column="size_bytes" />
                    </button>
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    {t('metadata')}
                  </th>
                  <th className="w-32 px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {paginatedBackups.map((backup) => (
                  <tr
                    key={backup.id}
                    className="border-b last:border-0 hover:bg-muted/50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate max-w-[200px]">
                          {backup.filename}
                        </span>
                        {backup.is_encrypted && (
                          <Lock className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
                        )}
                        {backup.is_overdue && (
                          <Badge
                            variant="outline"
                            className="bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800"
                          >
                            {t('overdue')}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      <div>
                        <span>{formatDate(backup.created_at)}</span>
                        <span className="block text-xs">{backup.age_description}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {formatBytes(backup.size_bytes)}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {backup.metadata ? (
                        <span>
                          {backup.metadata.provider_count} {t('providers')},{' '}
                          {backup.metadata.license_count} {t('licenses')},{' '}
                          {backup.metadata.employee_count} {t('employees')}
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={() => handleDownloadBackup(backup)}
                          disabled={downloadingId === backup.id}
                          title={tCommon('download')}
                        >
                          {downloadingId === backup.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Download className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={() => {
                            setBackupToRestore(backup);
                            setRestoreDialogOpen(true);
                          }}
                          title={t('restore')}
                        >
                          <RotateCcw className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 text-red-500 dark:text-red-400 hover:text-red-600 dark:hover:text-red-300"
                          onClick={() => {
                            setBackupToDelete(backup);
                            setDeleteDialogOpen(true);
                          }}
                          title={tCommon('delete')}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        <div className="mt-4">
          <Pagination
            page={page}
            totalPages={totalPages}
            totalItems={filteredBackups.length}
            pageSize={pageSize}
            onPageChange={setPage}
          />
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
                autoFocus
                tabIndex={1}
              />
            </div>
            <div className="space-y-2">
              <Label>{tCommon('confirm')}</Label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password"
                tabIndex={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPasswordDialogOpen(false)} tabIndex={4}>
              {tCommon('cancel')}
            </Button>
            <Button
              onClick={handleSavePassword}
              disabled={
                savingPassword ||
                newPassword.length < 12 ||
                newPassword !== confirmPassword
              }
              tabIndex={3}
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
            <DialogDescription className="text-red-600 dark:text-red-400 font-medium">
              {t('confirmRestoreWarning')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="p-3 bg-muted rounded-lg text-sm">
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
