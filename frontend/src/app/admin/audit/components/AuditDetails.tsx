'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ChevronDown, ChevronRight, Clock, User, Target, Package, Globe } from 'lucide-react';
import { AuditLogEntry } from '@/lib/api';
import { ChangesDisplay } from './ChangesDisplay';
import { getLocale } from '@/lib/locale';

interface AuditDetailsProps {
  log: AuditLogEntry | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
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

export function AuditDetails({ log, open, onOpenChange }: AuditDetailsProps) {
  const t = useTranslations('audit');
  const [showRawData, setShowRawData] = useState(false);

  if (!log) return null;

  const hasChanges = log.changes && Object.keys(log.changes).length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('auditLogDetails')}</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Metadata grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-start gap-3 p-3 bg-zinc-50 rounded-lg">
              <Clock className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-0.5">
                  {t('timestamp')}
                </p>
                <p className="text-sm">
                  {new Date(log.created_at).toLocaleString(getLocale(), {
                    dateStyle: 'full',
                    timeStyle: 'medium',
                  })}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-zinc-50 rounded-lg">
              <User className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-0.5">
                  {t('user')}
                </p>
                <p className="text-sm">
                  {log.admin_user_email || t('systemUser')}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-zinc-50 rounded-lg">
              <Target className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-0.5">
                  {t('action')}
                </p>
                <Badge
                  variant="outline"
                  className={getActionBadgeColor(log.action)}
                >
                  {log.action}
                </Badge>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-zinc-50 rounded-lg">
              <Package className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-0.5">
                  {t('resourceType')} / {t('resource')}
                </p>
                <p className="text-sm">
                  <span className="font-medium">{log.resource_type}</span>
                  {log.resource_id && (
                    <span className="text-muted-foreground ml-2 font-mono text-xs">
                      {log.resource_id}
                    </span>
                  )}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-zinc-50 rounded-lg md:col-span-2">
              <Globe className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-0.5">
                  {t('ipAddress')}
                </p>
                <p className="text-sm font-mono">
                  {log.ip_address || '-'}
                </p>
              </div>
            </div>
          </div>

          {/* Changes section */}
          {hasChanges && (
            <div>
              <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                <span className="w-1 h-4 bg-blue-500 rounded-full"></span>
                {t('changes')}
              </h3>
              <ChangesDisplay changes={log.changes} />
            </div>
          )}

          {/* Raw data section */}
          {hasChanges && (
            <div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowRawData(!showRawData)}
                className="mb-2"
              >
                {showRawData ? (
                  <ChevronDown className="h-4 w-4 mr-2" />
                ) : (
                  <ChevronRight className="h-4 w-4 mr-2" />
                )}
                {t('rawData')}
              </Button>

              {showRawData && (
                <div className="bg-zinc-900 text-zinc-100 rounded-lg p-4 overflow-auto max-h-64">
                  <pre className="text-xs font-mono whitespace-pre-wrap">
                    {JSON.stringify(log.changes, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
