'use client';

import { useState } from 'react';
import { api, EmployeeBulkImportItem, EmployeeBulkImportResponse } from '@/lib/api';

export interface UseEmployeeBulkImportReturn {
  importing: boolean;
  file: File | null;
  result: EmployeeBulkImportResponse | null;
  parseError: string | null;
  handleFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  downloadTemplate: () => void;
  handleImport: () => Promise<void>;
  handleClose: () => void;
}

function parseCSV(csvText: string): EmployeeBulkImportItem[] {
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
}

export function useEmployeeBulkImport(
  onOpenChange: (open: boolean) => void,
  onSuccess: () => void,
  showToast: (type: 'success' | 'error' | 'info', text: string) => void,
  t: (key: string, params?: Record<string, string | number>) => string,
): UseEmployeeBulkImportReturn {
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

  return {
    importing,
    file,
    result,
    parseError,
    handleFileChange,
    downloadTemplate,
    handleImport,
    handleClose,
  };
}
