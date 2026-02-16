'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import { api, BackupConfig, StoredBackup } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';

export interface UseBackupsTabReturn {
  // Loading states
  loading: boolean;
  savingConfig: boolean;
  savingPassword: boolean;
  triggeringBackup: boolean;
  downloadingId: string | null;
  deleting: boolean;
  restoring: boolean;

  // Config state
  config: BackupConfig;
  setConfig: React.Dispatch<React.SetStateAction<BackupConfig>>;

  // Backups list state
  backups: StoredBackup[];
  nextScheduled: string | null;
  lastBackup: string | null;

  // Password dialog state
  passwordDialogOpen: boolean;
  setPasswordDialogOpen: (open: boolean) => void;
  newPassword: string;
  setNewPassword: (password: string) => void;
  confirmPassword: string;
  setConfirmPassword: (password: string) => void;

  // Delete dialog state
  deleteDialogOpen: boolean;
  setDeleteDialogOpen: (open: boolean) => void;
  backupToDelete: StoredBackup | null;
  setBackupToDelete: (backup: StoredBackup | null) => void;

  // Restore dialog state
  restoreDialogOpen: boolean;
  setRestoreDialogOpen: (open: boolean) => void;
  backupToRestore: StoredBackup | null;
  setBackupToRestore: (backup: StoredBackup | null) => void;
  restorePassword: string;
  setRestorePassword: (password: string) => void;

  // Table state
  search: string;
  setSearch: (search: string) => void;
  sortColumn: 'created_at' | 'size_bytes' | 'filename';
  sortDirection: 'asc' | 'desc';
  filterEncrypted: 'all' | 'encrypted' | 'unencrypted';
  setFilterEncrypted: (filter: 'all' | 'encrypted' | 'unencrypted') => void;
  page: number;
  setPage: (page: number) => void;
  pageSize: number;
  filteredBackups: StoredBackup[];
  totalPages: number;
  paginatedBackups: StoredBackup[];

  // Handlers
  handleSaveConfig: () => Promise<void>;
  handleSavePassword: () => Promise<void>;
  handleTriggerBackup: () => Promise<void>;
  handleDownloadBackup: (backup: StoredBackup) => Promise<void>;
  handleDeleteBackup: () => Promise<void>;
  handleRestoreBackup: () => Promise<void>;
  handleSort: (column: 'created_at' | 'size_bytes' | 'filename') => void;
  handleClearFilters: () => void;
}

export function useBackupsTab(
  showToast: (type: 'success' | 'error', message: string) => void,
  t: (key: string, params?: Record<string, string | number>) => string,
  tCommon: (key: string) => string,
): UseBackupsTabReturn {
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

  // Table state: search, sort, filter, pagination
  const [search, setSearch] = useState('');
  const [sortColumn, setSortColumn] = useState<'created_at' | 'size_bytes' | 'filename'>('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [filterEncrypted, setFilterEncrypted] = useState<'all' | 'encrypted' | 'unencrypted'>('all');
  const [page, setPage] = useState(1);
  const pageSize = 10;

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

  const handleSaveConfig = useCallback(async () => {
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
  }, [config.enabled, config.schedule, config.retention_count, showToast, t, tCommon]);

  const handleSavePassword = useCallback(async () => {
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
      const message = error instanceof Error ? error.message : tCommon('operationFailed');
      showToast('error', message);
    } finally {
      setSavingPassword(false);
    }
  }, [newPassword, confirmPassword, showToast, t, tCommon]);

  const handleTriggerBackup = useCallback(async () => {
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
  }, [showToast, t, tCommon]);

  const handleDownloadBackup = useCallback(async (backup: StoredBackup) => {
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
  }, [showToast, tCommon]);

  const handleDeleteBackup = useCallback(async () => {
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
  }, [backupToDelete, showToast, t, tCommon]);

  const handleRestoreBackup = useCallback(async () => {
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
  }, [backupToRestore, restorePassword, showToast, t, tCommon]);

  // Sort handler
  const handleSort = useCallback((column: 'created_at' | 'size_bytes' | 'filename') => {
    if (sortColumn === column) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  }, [sortColumn]);

  // Clear filters handler
  const handleClearFilters = useCallback(() => {
    setSearch('');
    setFilterEncrypted('all');
  }, []);

  // Filter, sort, and paginate backups
  const filteredBackups = useMemo(() => {
    let result = backups;

    // Search filter
    if (search) {
      const searchLower = search.toLowerCase();
      result = result.filter(
        (b) =>
          b.filename.toLowerCase().includes(searchLower) ||
          b.age_description?.toLowerCase().includes(searchLower)
      );
    }

    // Encrypted filter
    if (filterEncrypted === 'encrypted') {
      result = result.filter((b) => b.is_encrypted);
    } else if (filterEncrypted === 'unencrypted') {
      result = result.filter((b) => !b.is_encrypted);
    }

    // Sort
    result = [...result].sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;

      switch (sortColumn) {
        case 'created_at':
          aVal = new Date(a.created_at).getTime();
          bVal = new Date(b.created_at).getTime();
          break;
        case 'size_bytes':
          aVal = a.size_bytes;
          bVal = b.size_bytes;
          break;
        case 'filename':
          aVal = a.filename.toLowerCase();
          bVal = b.filename.toLowerCase();
          break;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [backups, search, filterEncrypted, sortColumn, sortDirection]);

  // Pagination
  const totalPages = Math.ceil(filteredBackups.length / pageSize);
  const paginatedBackups = filteredBackups.slice((page - 1) * pageSize, page * pageSize);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [search, filterEncrypted]);

  return {
    // Loading states
    loading,
    savingConfig,
    savingPassword,
    triggeringBackup,
    downloadingId,
    deleting,
    restoring,

    // Config state
    config,
    setConfig,

    // Backups list state
    backups,
    nextScheduled,
    lastBackup,

    // Password dialog state
    passwordDialogOpen,
    setPasswordDialogOpen,
    newPassword,
    setNewPassword,
    confirmPassword,
    setConfirmPassword,

    // Delete dialog state
    deleteDialogOpen,
    setDeleteDialogOpen,
    backupToDelete,
    setBackupToDelete,

    // Restore dialog state
    restoreDialogOpen,
    setRestoreDialogOpen,
    backupToRestore,
    setBackupToRestore,
    restorePassword,
    setRestorePassword,

    // Table state
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

    // Handlers
    handleSaveConfig,
    handleSavePassword,
    handleTriggerBackup,
    handleDownloadBackup,
    handleDeleteBackup,
    handleRestoreBackup,
    handleSort,
    handleClearFilters,
  };
}
