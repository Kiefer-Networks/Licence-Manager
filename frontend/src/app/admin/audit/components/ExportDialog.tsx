'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Download, Loader2, AlertCircle } from 'lucide-react';

const MAX_EXPORT_RECORDS = 10000;

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  totalRecords: number;
  onExport: (limit: number, format: 'csv' | 'json') => Promise<void>;
}

export function ExportDialog({
  open,
  onOpenChange,
  totalRecords,
  onExport,
}: ExportDialogProps) {
  const t = useTranslations('audit');
  const tCommon = useTranslations('common');

  const [limit, setLimit] = useState<number>(Math.min(totalRecords, MAX_EXPORT_RECORDS));
  const [format, setFormat] = useState<'csv' | 'json'>('csv');
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState('');

  const handleLimitChange = (value: string) => {
    const num = parseInt(value, 10);
    if (!isNaN(num)) {
      setLimit(Math.max(1, Math.min(num, MAX_EXPORT_RECORDS)));
    }
  };

  const handleExport = async () => {
    setIsExporting(true);
    setError('');
    try {
      await onExport(limit, format);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('exportFailed'));
    } finally {
      setIsExporting(false);
    }
  };

  const exceedsMax = totalRecords > MAX_EXPORT_RECORDS;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            {t('exportAuditLogs')}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Total records info */}
          <div className="bg-zinc-50 rounded-lg p-3">
            <p className="text-sm text-muted-foreground">
              {t('totalMatchingRecords')}: <span className="font-medium text-zinc-900">{totalRecords.toLocaleString()}</span>
            </p>
            {exceedsMax && (
              <div className="flex items-start gap-2 mt-2 text-amber-600">
                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <p className="text-xs">
                  {t('exportLimitWarning', { max: MAX_EXPORT_RECORDS.toLocaleString() })}
                </p>
              </div>
            )}
          </div>

          {/* Limit input */}
          <div className="space-y-2">
            <Label htmlFor="export-limit">{t('numberOfRecords')}</Label>
            <div className="flex items-center gap-2">
              <Input
                id="export-limit"
                type="number"
                min={1}
                max={MAX_EXPORT_RECORDS}
                value={limit}
                onChange={(e) => handleLimitChange(e.target.value)}
                className="w-32"
              />
              <span className="text-sm text-muted-foreground">
                {t('maxRecords', { max: MAX_EXPORT_RECORDS.toLocaleString() })}
              </span>
            </div>
          </div>

          {/* Format selection */}
          <div className="space-y-2">
            <Label>{t('exportFormat')}</Label>
            <Select value={format} onValueChange={(v) => setFormat(v as 'csv' | 'json')}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="csv">{t('formatCsv')}</SelectItem>
                <SelectItem value="json">{t('formatJson')}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isExporting}>
            {tCommon('cancel')}
          </Button>
          <Button onClick={handleExport} disabled={isExporting || limit < 1}>
            {isExporting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {t('exporting')}
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                {t('exportRecords', { count: limit.toLocaleString() })}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
