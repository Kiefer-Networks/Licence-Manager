'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Download, FileSpreadsheet, FileText, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

type ExportType = 'licenses-csv' | 'costs-csv' | 'full-excel';

interface ExportButtonProps {
  className?: string;
  providerId?: string;
  department?: string;
  status?: string;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

export function ExportButton({
  className = '',
  providerId,
  department,
  status,
  variant = 'outline',
  size = 'sm',
}: ExportButtonProps) {
  const t = useTranslations('reports');
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

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant={variant} size={size} className={`gap-2 ${className}`}>
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          {t('export')}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem
          onClick={() => handleExport('licenses-csv')}
          disabled={loading !== null}
          className="gap-2"
        >
          <FileText className="h-4 w-4 text-muted-foreground" />
          {t('licensesCSV')}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => handleExport('costs-csv')}
          disabled={loading !== null}
          className="gap-2"
        >
          <FileText className="h-4 w-4 text-muted-foreground" />
          {t('costsCSV')}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => handleExport('full-excel')}
          disabled={loading !== null}
          className="gap-2"
        >
          <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
          {t('fullReportExcel')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
