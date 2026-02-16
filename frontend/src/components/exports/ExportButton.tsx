'use client';

import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Download, FileSpreadsheet, FileText, Loader2 } from 'lucide-react';
import { useExportButton } from '@/hooks/use-export-button';

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
  const { loading, handleExport } = useExportButton({ providerId, department, status });

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
