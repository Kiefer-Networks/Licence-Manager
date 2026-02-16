'use client';

import { useTranslations } from 'next-intl';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { DepartmentForecast } from '@/lib/api';
import { useLocale } from '@/components/locale-provider';

interface DepartmentForecastTableProps {
  departments: DepartmentForecast[];
}

export function DepartmentForecastTable({
  departments,
}: DepartmentForecastTableProps) {
  const t = useTranslations('forecasts');
  const { formatCurrency } = useLocale();

  if (departments.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-muted-foreground">
        <p className="text-sm">{t('noDepartmentData')}</p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t('department')}</TableHead>
          <TableHead className="text-right">{t('employees')}</TableHead>
          <TableHead className="text-right">{t('projectedEmployees')}</TableHead>
          <TableHead className="text-right">{t('currentCost')}</TableHead>
          <TableHead className="text-right">{t('projectedCost')}</TableHead>
          <TableHead className="text-right">{t('costPerEmployee')}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {departments.map((dept) => (
          <TableRow key={dept.department}>
            <TableCell className="font-medium">{dept.department}</TableCell>
            <TableCell className="text-right tabular-nums">{dept.employee_count}</TableCell>
            <TableCell className="text-right tabular-nums">{dept.projected_employees}</TableCell>
            <TableCell className="text-right tabular-nums">
              {formatCurrency(dept.current_cost)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatCurrency(dept.projected_cost)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatCurrency(dept.cost_per_employee)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
