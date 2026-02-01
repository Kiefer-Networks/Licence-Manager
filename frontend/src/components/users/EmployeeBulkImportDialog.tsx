'use client';

import { useState } from 'react';
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
import { api, EmployeeBulkImportItem, EmployeeBulkImportResponse } from '@/lib/api';
import { Loader2, Upload, Download, CheckCircle, AlertCircle, FileText } from 'lucide-react';

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

  const [importing, setImporting] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<EmployeeBulkImportResponse | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setResult(null);
      setParseError(null);
    }
  };

  const downloadTemplate = () => {
    const csvContent = 'email,full_name,department,status,start_date,manager_email\njohn.doe@company.com,John Doe,Engineering,active,2024-01-15,jane.smith@company.com\njane.smith@company.com,Jane Smith,Engineering,active,2023-06-01,';
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'employee_import_template.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const parseCSV = (csvText: string): EmployeeBulkImportItem[] => {
    const lines = csvText.trim().split('\n');
    if (lines.length < 2) {
      throw new Error('CSV must have a header row and at least one data row');
    }

    const headers = lines[0].toLowerCase().split(',').map((h) => h.trim());

    const emailIndex = headers.indexOf('email');
    const fullNameIndex = headers.indexOf('full_name');
    const departmentIndex = headers.indexOf('department');
    const statusIndex = headers.indexOf('status');
    const startDateIndex = headers.indexOf('start_date');
    const managerEmailIndex = headers.indexOf('manager_email');

    if (emailIndex === -1 || fullNameIndex === -1) {
      throw new Error('CSV must have email and full_name columns');
    }

    const employees: EmployeeBulkImportItem[] = [];

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',').map((v) => v.trim());
      if (values.length < 2) continue;

      const email = values[emailIndex];
      const full_name = values[fullNameIndex];

      if (!email || !full_name) continue;

      const employee: EmployeeBulkImportItem = {
        email,
        full_name,
      };

      if (departmentIndex !== -1 && values[departmentIndex]) {
        employee.department = values[departmentIndex];
      }

      if (statusIndex !== -1 && values[statusIndex]) {
        const status = values[statusIndex].toLowerCase();
        if (status === 'active' || status === 'offboarded') {
          employee.status = status;
        }
      }

      if (startDateIndex !== -1 && values[startDateIndex]) {
        employee.start_date = values[startDateIndex];
      }

      if (managerEmailIndex !== -1 && values[managerEmailIndex]) {
        employee.manager_email = values[managerEmailIndex];
      }

      employees.push(employee);
    }

    return employees;
  };

  const handleImport = async () => {
    if (!file) return;

    setImporting(true);
    setParseError(null);
    setResult(null);

    try {
      const text = await file.text();
      const employees = parseCSV(text);

      if (employees.length === 0) {
        setParseError('No valid employees found in CSV');
        return;
      }

      if (employees.length > 500) {
        setParseError('Maximum 500 employees per import');
        return;
      }

      const importResult = await api.bulkImportEmployees(employees);
      setResult(importResult);

      if (importResult.created > 0 || importResult.updated > 0) {
        showToast(
          'success',
          t('importComplete', {
            created: importResult.created,
            updated: importResult.updated,
            skipped: importResult.skipped,
          })
        );
        onSuccess();
      } else if (importResult.skipped > 0) {
        showToast('info', t('noNewEmployees'));
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setParseError(errorMessage);
      showToast('error', t('importFailed'));
    } finally {
      setImporting(false);
    }
  };

  const handleClose = () => {
    setFile(null);
    setResult(null);
    setParseError(null);
    onOpenChange(false);
  };

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
