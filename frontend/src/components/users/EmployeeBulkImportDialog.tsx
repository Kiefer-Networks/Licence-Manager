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
import { Loader2, Upload, Download, CheckCircle, AlertCircle, FileText } from 'lucide-react';
import { useEmployeeBulkImport } from '@/hooks/use-employee-bulk-import';

interface EmployeeBulkImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  showToast: (type: 'success' | 'error' | 'info', text: string) => void;
}

export function EmployeeBulkImportDialog({
  open,
  onOpenChange,
  onSuccess,
  showToast,
}: EmployeeBulkImportDialogProps) {
  const t = useTranslations('employees');
  const tCommon = useTranslations('common');

  const {
    importing,
    file,
    result,
    parseError,
    handleFileChange,
    downloadTemplate,
    handleImport,
    handleClose,
  } = useEmployeeBulkImport(onOpenChange, onSuccess, showToast, t);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{t('bulkImportTitle')}</DialogTitle>
          <DialogDescription>{t('bulkImportDescription')}</DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* Instructions */}
          <div className="rounded-lg bg-zinc-50 p-4 text-sm">
            <p className="font-medium mb-2">{t('csvRequiredColumns')}</p>
            <p className="text-muted-foreground">{t('csvOptionalColumns')}</p>
          </div>

          {/* Download Template */}
          <div>
            <Button variant="outline" onClick={downloadTemplate} className="gap-2">
              <Download className="h-4 w-4" />
              {t('downloadTemplate')}
            </Button>
          </div>

          {/* File Upload */}
          <div className="grid gap-2">
            <Label htmlFor="csv-file">{t('selectCsvFile')}</Label>
            <div className="flex gap-2">
              <Input
                id="csv-file"
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="flex-1"
              />
            </div>
            {file && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <FileText className="h-4 w-4" />
                {file.name}
              </div>
            )}
          </div>

          {/* Parse Error */}
          {parseError && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 text-red-800 text-sm">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <p>{parseError}</p>
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="rounded-lg border p-4 space-y-3">
              <h4 className="font-medium">{t('importResults')}</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-emerald-600" />
                  <span>
                    {t('created')}: <strong>{result.created}</strong>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-blue-600" />
                  <span>
                    {t('updated')}: <strong>{result.updated}</strong>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-amber-600" />
                  <span>
                    {t('skipped')}: <strong>{result.skipped}</strong>
                  </span>
                </div>
              </div>
              {result.errors.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm font-medium text-red-700 mb-1">
                    {t('importErrors')}:
                  </p>
                  <ul className="text-sm text-red-600 list-disc list-inside max-h-32 overflow-auto">
                    {result.errors.slice(0, 10).map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                    {result.errors.length > 10 && (
                      <li>...and {result.errors.length - 10} more</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            {result ? tCommon('close') : tCommon('cancel')}
          </Button>
          {!result && (
            <Button onClick={handleImport} disabled={!file || importing} className="gap-2">
              {importing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              {t('bulkImport')}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
