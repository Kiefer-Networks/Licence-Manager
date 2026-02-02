'use client';

import { useTranslations } from 'next-intl';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Eye, FileText } from 'lucide-react';
import { AuditLogEntry } from '@/lib/api';
import { useLocale } from '@/components/locale-provider';

interface AuditTableProps {
  logs: AuditLogEntry[];
  onViewDetails: (log: AuditLogEntry) => void;
}

function formatRelativeTime(
  dateString: string,
  t: (key: string, params?: Record<string, number>) => string,
  formatDate: (date: string | Date | null | undefined) => string
): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return t('justNow');
  if (diffMin < 60) return t('minutesAgo', { min: diffMin });
  if (diffHour < 24) return t('hoursAgo', { hours: diffHour });
  if (diffDay < 7) return t('daysAgo', { days: diffDay });

  return formatDate(dateString);
}

function getActionBadgeColor(action: string): string {
  const lowerAction = action.toLowerCase();
  if (lowerAction.includes('create') || lowerAction.includes('assign')) {
    return 'bg-emerald-100 text-emerald-700 border-emerald-200';
  }
  if (lowerAction.includes('update') || lowerAction.includes('change')) {
    return 'bg-blue-100 text-blue-700 border-blue-200';
  }
  if (lowerAction.includes('delete') || lowerAction.includes('remove') || lowerAction.includes('revoke')) {
    return 'bg-red-100 text-red-700 border-red-200';
  }
  if (lowerAction.includes('login') || lowerAction.includes('logout')) {
    return 'bg-purple-100 text-purple-700 border-purple-200';
  }
  if (lowerAction.includes('sync')) {
    return 'bg-amber-100 text-amber-700 border-amber-200';
  }
  return 'bg-zinc-100 text-zinc-700 border-zinc-200';
}

function getActionVerb(action: string): string {
  const verbs: Record<string, string> = {
    create: 'erstellt',
    update: 'aktualisiert',
    delete: 'gelöscht',
    login: 'angemeldet',
    logout: 'abgemeldet',
    sync: 'synchronisiert',
    assign: 'zugewiesen',
    unassign: 'entzogen',
    revoke: 'widerrufen',
  };

  const lowerAction = action.toLowerCase();
  for (const [key, verb] of Object.entries(verbs)) {
    if (lowerAction.includes(key)) return verb;
  }
  return action;
}

function generateSummary(log: AuditLogEntry): string {
  const resourceType = log.resource_type?.toLowerCase() || 'Ressource';
  const action = getActionVerb(log.action);

  // Try to extract meaningful info from changes
  let target = '';
  if (log.changes) {
    const changes = log.changes as Record<string, unknown>;
    // Look for email or name in changes
    if (changes.new && typeof changes.new === 'object') {
      const newData = changes.new as Record<string, unknown>;
      target = (newData.email as string) || (newData.name as string) || '';
    }
    if (!target && changes.email) {
      target = String(changes.email);
    }
    if (!target && changes.name) {
      target = String(changes.name);
    }
  }

  if (target) {
    return `${resourceType} "${target}" ${action}`;
  }

  if (log.resource_id) {
    return `${resourceType} ${action}`;
  }

  return `${resourceType} ${action}`;
}

export function AuditTable({ logs, onViewDetails }: AuditTableProps) {
  const t = useTranslations('audit');
  const { formatDate } = useLocale();

  if (logs.length === 0) {
    return (
      <div className="border rounded-lg bg-white p-8 text-center">
        <FileText className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
        <p className="text-muted-foreground">{t('noAuditLogs')}</p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg bg-white">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[160px]">{t('timestamp')}</TableHead>
            <TableHead className="w-[200px]">{t('user')}</TableHead>
            <TableHead className="w-[120px]">{t('action')}</TableHead>
            <TableHead>{t('whatHappened')}</TableHead>
            <TableHead className="w-[120px]">{t('ipAddress')}</TableHead>
            <TableHead className="w-[60px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {logs.map((log) => (
            <TableRow key={log.id} className="hover:bg-zinc-50">
              <TableCell className="text-sm">
                <span
                  title={formatDate(log.created_at)}
                >
                  {formatRelativeTime(log.created_at, t, formatDate)}
                </span>
              </TableCell>
              <TableCell className="text-sm">
                {log.admin_user_email || (
                  <span className="text-muted-foreground italic">
                    {t('systemUser')}
                  </span>
                )}
              </TableCell>
              <TableCell>
                <Badge
                  variant="outline"
                  className={getActionBadgeColor(log.action)}
                >
                  {log.action}
                </Badge>
              </TableCell>
              <TableCell className="text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-zinc-700">
                    {log.resource_type}
                  </span>
                  {log.resource_id && (
                    <span
                      className="text-muted-foreground font-mono text-xs"
                      title={log.resource_id}
                    >
                      {log.resource_id.slice(0, 8)}...
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground font-mono text-xs">
                {log.ip_address || <span className="text-zinc-400">-</span>}
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => onViewDetails(log)}
                  title={t('details')}
                >
                  <Eye className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
