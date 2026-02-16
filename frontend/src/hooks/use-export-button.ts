'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

export type ExportType = 'licenses-csv' | 'costs-csv' | 'full-excel';

export interface UseExportButtonParams {
  providerId?: string;
  department?: string;
  status?: string;
}

export interface UseExportButtonReturn {
  loading: ExportType | null;
  handleExport: (type: ExportType) => Promise<void>;
}

export function useExportButton({
  providerId,
  department,
  status,
}: UseExportButtonParams): UseExportButtonReturn {
  const [loading, setLoading] = useState<ExportType | null>(null);

  const handleExport = async (type: ExportType) => {
    setLoading(type);
    try {
      let url: string;
      let filename: string;

      switch (type) {
        case 'licenses-csv':
          url = await api.getExportUrl('licenses', 'csv', { providerId, department, status });
          filename = 'licenses.csv';
          break;
        case 'costs-csv':
          url = await api.getExportUrl('costs', 'csv');
          filename = 'costs.csv';
          break;
        case 'full-excel':
          url = await api.getExportUrl('full-report', 'excel');
          filename = 'license_report.xlsx';
          break;
      }

      // Trigger download
      await api.downloadExport(url, filename);
    } catch {
      // Error handled silently - export failed notification could be added via toast
    } finally {
      setLoading(null);
    }
  };

  return {
    loading,
    handleExport,
  };
}
