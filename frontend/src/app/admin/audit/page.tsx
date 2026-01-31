'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth, Permissions } from '@/components/auth-provider';
import { api, AuditLogEntry } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
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
import { AppLayout } from '@/components/layout/app-layout';
import { Loader2, ChevronLeft, ChevronRight, FileText, RefreshCw, Filter, Eye } from 'lucide-react';
import { getLocale } from '@/lib/locale';

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;

  return date.toLocaleDateString(getLocale(), {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getActionBadgeColor(action: string): string {
  switch (action.toLowerCase()) {
    case 'create':
      return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    case 'update':
      return 'bg-blue-100 text-blue-700 border-blue-200';
    case 'delete':
      return 'bg-red-100 text-red-700 border-red-200';
    case 'login':
    case 'logout':
      return 'bg-purple-100 text-purple-700 border-purple-200';
    case 'sync':
      return 'bg-amber-100 text-amber-700 border-amber-200';
    default:
      return 'bg-zinc-100 text-zinc-700 border-zinc-200';
  }
}

export default function AuditLogPage() {
  const t = useTranslations('audit');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { hasPermission, isLoading: authLoading } = useAuth();

  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 25;

  // Filters
  const [actionFilter, setActionFilter] = useState<string>('');
  const [resourceTypeFilter, setResourceTypeFilter] = useState<string>('');
  const [availableActions, setAvailableActions] = useState<string[]>([]);
  const [availableResourceTypes, setAvailableResourceTypes] = useState<string[]>([]);

  // Detail dialog
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.AUDIT_VIEW)) {
      router.push('/unauthorized');
      return;
    }
  }, [authLoading, hasPermission, router]);

  useEffect(() => {
    loadFilterOptions();
  }, []);

  useEffect(() => {
    loadLogs();
  }, [page, actionFilter, resourceTypeFilter]);

  const loadFilterOptions = async () => {
    try {
      const [actions, resourceTypes] = await Promise.all([
        api.getAuditActions(),
        api.getAuditResourceTypes(),
      ]);
      setAvailableActions(actions);
      setAvailableResourceTypes(resourceTypes);
    } catch {
      // Silent fail for filter options
    }
  };

  const loadLogs = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await api.getAuditLogs({
        page,
        page_size: pageSize,
        action: actionFilter || undefined,
        resource_type: resourceTypeFilter || undefined,
      });
      setLogs(response.items);
      setTotalPages(response.total_pages);
      setTotal(response.total);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load audit logs';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewDetails = (log: AuditLogEntry) => {
    setSelectedLog(log);
    setDetailDialogOpen(true);
  };

  const handleClearFilters = () => {
    setActionFilter('');
    setResourceTypeFilter('');
    setPage(1);
  };

  const hasFilters = actionFilter || resourceTypeFilter;

  if (authLoading || (isLoading && logs.length === 0)) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
            <p className="text-muted-foreground text-sm mt-0.5">
              {t('details')}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={loadLogs} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            {tCommon('refresh')}
          </Button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={actionFilter || "__all__"} onValueChange={(v) => { setActionFilter(v === "__all__" ? "" : v); setPage(1); }}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="All Actions" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All Actions</SelectItem>
              {availableActions.map((action) => (
                <SelectItem key={action} value={action}>
                  {action}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={resourceTypeFilter || "__all__"} onValueChange={(v) => { setResourceTypeFilter(v === "__all__" ? "" : v); setPage(1); }}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Resources" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All Resources</SelectItem>
              {availableResourceTypes.map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={handleClearFilters}>
              Clear Filters
            </Button>
          )}

          <div className="flex-1" />

          <span className="text-sm text-muted-foreground">
            {total.toLocaleString()} entries
          </span>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Table */}
        <div className="border rounded-lg bg-white">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[180px]">{t('timestamp')}</TableHead>
                <TableHead className="w-[200px]">{t('user')}</TableHead>
                <TableHead className="w-[100px]">{t('action')}</TableHead>
                <TableHead className="w-[150px]">{t('resource')}</TableHead>
                <TableHead>{t('resourceType')}</TableHead>
                <TableHead className="w-[100px]">{t('ipAddress')}</TableHead>
                <TableHead className="w-[60px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                    <FileText className="h-8 w-8 mx-auto mb-2 text-zinc-300" />
                    {t('noAuditLogs')}
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log) => (
                  <TableRow key={log.id} className="hover:bg-zinc-50">
                    <TableCell className="text-sm">
                      <span title={new Date(log.created_at).toLocaleString(getLocale())}>
                        {formatRelativeTime(log.created_at)}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm">
                      {log.admin_user_email || (
                        <span className="text-muted-foreground italic">System</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={getActionBadgeColor(log.action)}>
                        {log.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm font-medium">
                      {log.resource_type}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground font-mono text-xs">
                      {log.resource_id ? (
                        <span title={log.resource_id}>
                          {log.resource_id.slice(0, 8)}...
                        </span>
                      ) : (
                        <span className="text-zinc-400">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground font-mono text-xs">
                      {log.ip_address || <span className="text-zinc-400">-</span>}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handleViewDetails(log)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-2">
            <p className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1 || isLoading}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages || isLoading}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Dialog */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Audit Log Details</DialogTitle>
          </DialogHeader>
          {selectedLog && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Timestamp</p>
                  <p className="text-sm">
                    {new Date(selectedLog.created_at).toLocaleString(getLocale(), {
                      dateStyle: 'full',
                      timeStyle: 'medium',
                    })}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">User</p>
                  <p className="text-sm">{selectedLog.admin_user_email || 'System'}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Action</p>
                  <Badge variant="outline" className={getActionBadgeColor(selectedLog.action)}>
                    {selectedLog.action}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Resource Type</p>
                  <p className="text-sm font-medium">{selectedLog.resource_type}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Resource ID</p>
                  <p className="text-sm font-mono">{selectedLog.resource_id || '-'}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">IP Address</p>
                  <p className="text-sm font-mono">{selectedLog.ip_address || '-'}</p>
                </div>
              </div>

              {selectedLog.changes && Object.keys(selectedLog.changes).length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-2">Changes</p>
                  <div className="bg-zinc-50 rounded-lg p-3 overflow-auto max-h-64">
                    <pre className="text-xs font-mono whitespace-pre-wrap">
                      {JSON.stringify(selectedLog.changes, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
