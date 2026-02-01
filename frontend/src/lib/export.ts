/**
 * Export utilities for reports and data tables.
 */

type ExportRow = Record<string, string | number | boolean | null | undefined>;

interface ExportOptions {
  filename: string;
  headers?: Record<string, string>;
}

/**
 * Convert data to CSV format and trigger download.
 */
export function exportToCsv<T extends ExportRow>(
  data: T[],
  options: ExportOptions
): void {
  if (data.length === 0) {
    return;
  }

  const { filename, headers } = options;

  // Get column keys from first row or headers
  const keys = headers ? Object.keys(headers) : Object.keys(data[0]);

  // Build header row
  const headerRow = keys.map((key) => {
    const label = headers?.[key] ?? key;
    return escapeCSVField(label);
  });

  // Build data rows
  const dataRows = data.map((row) =>
    keys.map((key) => {
      const value = row[key];
      if (value === null || value === undefined) {
        return '';
      }
      if (typeof value === 'number') {
        return value.toString();
      }
      return escapeCSVField(String(value));
    })
  );

  // Combine with BOM for Excel UTF-8 compatibility
  const BOM = '\uFEFF';
  const csvContent = BOM + [headerRow.join(';'), ...dataRows.map((row) => row.join(';'))].join('\n');

  // Create and trigger download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Escape a field for CSV format.
 */
function escapeCSVField(field: string): string {
  // If field contains semicolon, newline, or quote, wrap in quotes
  if (field.includes(';') || field.includes('\n') || field.includes('"')) {
    return `"${field.replace(/"/g, '""')}"`;
  }
  return field;
}

/**
 * Format date for export (ISO format).
 */
export function formatDateForExport(date: string | Date | null | undefined): string {
  if (!date) return '';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toISOString().split('T')[0];
}

/**
 * Format currency for export.
 */
export function formatCurrencyForExport(
  value: number | string | null | undefined,
  currency = 'EUR'
): string {
  if (value === null || value === undefined) return '';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '';
  return `${num.toFixed(2)} ${currency}`;
}

// Report-specific export functions

export interface InactiveLicenseExportRow {
  provider_name: string;
  external_user_id: string;
  employee_name: string;
  employee_email: string;
  days_inactive: number;
  monthly_cost: string;
  [key: string]: string | number | boolean | null | undefined;
}

export interface ExportTranslations {
  provider: string;
  userId: string;
  employee: string;
  email: string;
  daysInactive: string;
  monthlyCost: string;
  terminationDate: string;
  daysSinceOffboarding: string;
  pendingLicenses: string;
  licenseCount: string;
  externalEmail: string;
  assignedEmployee: string;
  employeeEmail: string;
  status: string;
  licenseType: string;
  licenses: string;
  total: string;
  unassigned: string;
}

export function exportInactiveLicenses(
  licenses: Array<{
    provider_name: string;
    external_user_id: string;
    employee_name?: string | null;
    employee_email?: string | null;
    days_inactive: number;
    monthly_cost?: number | string | null;
  }>,
  translations: ExportTranslations,
  department?: string
): void {
  const data: InactiveLicenseExportRow[] = licenses.map((lic) => ({
    provider_name: lic.provider_name,
    external_user_id: lic.external_user_id,
    employee_name: lic.employee_name || translations.unassigned,
    employee_email: lic.employee_email || '',
    days_inactive: lic.days_inactive,
    monthly_cost: formatCurrencyForExport(lic.monthly_cost),
  }));

  const suffix = department ? `_${department.replace(/\s+/g, '_')}` : '';
  const date = new Date().toISOString().split('T')[0];

  exportToCsv(data, {
    filename: `inactive_licenses${suffix}_${date}`,
    headers: {
      provider_name: translations.provider,
      external_user_id: translations.userId,
      employee_name: translations.employee,
      employee_email: translations.email,
      days_inactive: translations.daysInactive,
      monthly_cost: translations.monthlyCost,
    },
  });
}

export interface OffboardingExportRow {
  employee_name: string;
  employee_email: string;
  termination_date: string;
  days_since_offboarding: number;
  pending_licenses: string;
  pending_license_count: number;
  [key: string]: string | number | boolean | null | undefined;
}

export function exportOffboarding(
  employees: Array<{
    employee_name: string;
    employee_email: string;
    termination_date?: string | null;
    days_since_offboarding: number;
    pending_licenses: Array<{ provider: string }>;
  }>,
  translations: ExportTranslations,
  department?: string
): void {
  const data: OffboardingExportRow[] = employees.map((emp) => ({
    employee_name: emp.employee_name,
    employee_email: emp.employee_email,
    termination_date: formatDateForExport(emp.termination_date),
    days_since_offboarding: emp.days_since_offboarding,
    pending_licenses: emp.pending_licenses.map((l) => l.provider).join(', '),
    pending_license_count: emp.pending_licenses.length,
  }));

  const suffix = department ? `_${department.replace(/\s+/g, '_')}` : '';
  const date = new Date().toISOString().split('T')[0];

  exportToCsv(data, {
    filename: `offboarding_report${suffix}_${date}`,
    headers: {
      employee_name: translations.employee,
      employee_email: translations.email,
      termination_date: translations.terminationDate,
      days_since_offboarding: translations.daysSinceOffboarding,
      pending_licenses: translations.pendingLicenses,
      pending_license_count: translations.licenseCount,
    },
  });
}

export interface ExternalUserExportRow {
  external_user_id: string;
  provider_name: string;
  employee_name: string;
  employee_email: string;
  employee_status: string;
  license_type: string;
  monthly_cost: string;
  [key: string]: string | number | boolean | null | undefined;
}

export function exportExternalUsers(
  licenses: Array<{
    external_user_id: string;
    provider_name: string;
    employee_name?: string | null;
    employee_email?: string | null;
    employee_status?: string | null;
    license_type?: string | null;
    monthly_cost?: number | string | null;
  }>,
  translations: ExportTranslations,
  department?: string
): void {
  const data: ExternalUserExportRow[] = licenses.map((lic) => ({
    external_user_id: lic.external_user_id,
    provider_name: lic.provider_name,
    employee_name: lic.employee_name || translations.unassigned,
    employee_email: lic.employee_email || '',
    employee_status: lic.employee_status || 'active',
    license_type: lic.license_type || '',
    monthly_cost: formatCurrencyForExport(lic.monthly_cost),
  }));

  const suffix = department ? `_${department.replace(/\s+/g, '_')}` : '';
  const date = new Date().toISOString().split('T')[0];

  exportToCsv(data, {
    filename: `external_users${suffix}_${date}`,
    headers: {
      external_user_id: translations.externalEmail,
      provider_name: translations.provider,
      employee_name: translations.assignedEmployee,
      employee_email: translations.employeeEmail,
      employee_status: translations.status,
      license_type: translations.licenseType,
      monthly_cost: translations.monthlyCost,
    },
  });
}

export interface CostExportRow {
  provider_name: string;
  license_count: number;
  monthly_cost: string;
  [key: string]: string | number | boolean | null | undefined;
}

export function exportCosts(
  costs: Array<{
    provider_name: string;
    license_count: number;
    cost: number | string;
  }>,
  totalCost: number | string,
  translations: ExportTranslations,
  department?: string
): void {
  const data: CostExportRow[] = costs.map((entry) => ({
    provider_name: entry.provider_name,
    license_count: entry.license_count,
    monthly_cost: formatCurrencyForExport(entry.cost),
  }));

  // Add total row
  data.push({
    provider_name: translations.total,
    license_count: costs.reduce((sum, c) => sum + c.license_count, 0),
    monthly_cost: formatCurrencyForExport(totalCost),
  });

  const suffix = department ? `_${department.replace(/\s+/g, '_')}` : '';
  const date = new Date().toISOString().split('T')[0];

  exportToCsv(data, {
    filename: `cost_report${suffix}_${date}`,
    headers: {
      provider_name: translations.provider,
      license_count: translations.licenses,
      monthly_cost: translations.monthlyCost,
    },
  });
}
