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
import { Badge } from '@/components/ui/badge';
import { ProviderForecast } from '@/lib/api';
import { useLocale } from '@/components/locale-provider';

interface ProviderForecastTableProps {
  providers: ProviderForecast[];
  onProviderClick?: (provider: ProviderForecast) => void;
}

export function ProviderForecastTable({
  providers,
  onProviderClick,
}: ProviderForecastTableProps) {
  const t = useTranslations('forecasts');
  const { formatCurrency, formatDate } = useLocale();

  if (providers.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-muted-foreground">
        <p className="text-sm">{t('noProviderData')}</p>
      </div>
    );
  }

  return (
    <div>
      <p className="text-xs text-muted-foreground mb-3">{t('clickProviderForDetails')}</p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t('provider')}</TableHead>
            <TableHead className="text-right">{t('currentCost')}</TableHead>
            <TableHead className="text-right">{t('projectedCost')}</TableHead>
            <TableHead className="text-right">{t('change')}</TableHead>
            <TableHead>{t('contractEnd')}</TableHead>
            <TableHead>{t('autoRenew')}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {providers.map((provider) => {
            const changeColor = provider.change_percent > 0
              ? 'text-red-600'
              : provider.change_percent < 0
                ? 'text-emerald-600'
                : '';
            return (
              <TableRow
                key={provider.provider_id}
                className={onProviderClick ? 'cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800' : ''}
                onClick={() => onProviderClick?.(provider)}
              >
                <TableCell className="font-medium">{provider.display_name}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatCurrency(provider.current_cost)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatCurrency(provider.projected_cost)}
                </TableCell>
                <TableCell className={`text-right tabular-nums ${changeColor}`}>
                  {provider.change_percent > 0 ? '+' : ''}{provider.change_percent}%
                </TableCell>
                <TableCell>
                  {provider.contract_end ? formatDate(provider.contract_end) : '-'}
                </TableCell>
                <TableCell>
                  <Badge variant={provider.auto_renew ? 'default' : 'secondary'}>
                    {provider.auto_renew ? t('yes') : t('no')}
                  </Badge>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
