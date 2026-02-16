'use client';

import { useTranslations } from 'next-intl';
import { ForecastDataPoint } from '@/lib/api';
import { useLocale } from '@/components/locale-provider';
import { MousePointerClick } from 'lucide-react';

interface DataPointDetailProps {
  dataPoint: ForecastDataPoint | null;
  adjustedDataPoint?: ForecastDataPoint | null;
  hasAdjustments: boolean;
}

export function DataPointDetail({
  dataPoint,
  adjustedDataPoint,
  hasAdjustments,
}: DataPointDetailProps) {
  const t = useTranslations('forecasts');
  const { formatCurrency, numberFormat } = useLocale();

  if (!dataPoint) {
    return (
      <div className="flex items-center gap-2 py-3 px-4 text-sm text-muted-foreground border rounded-lg bg-zinc-50 dark:bg-zinc-900">
        <MousePointerClick className="h-4 w-4" />
        <span>{t('noPointSelected')}</span>
      </div>
    );
  }

  const monthLabel = new Date(dataPoint.month).toLocaleDateString(numberFormat, {
    month: 'long',
    year: 'numeric',
  });
  const cost = Number(dataPoint.cost);
  const type = dataPoint.is_historical ? t('actual') : t('projected');

  const adjustedCost = adjustedDataPoint ? Number(adjustedDataPoint.cost) : null;
  const difference = adjustedCost != null ? adjustedCost - cost : null;

  return (
    <div className="py-3 px-4 border rounded-lg bg-zinc-50 dark:bg-zinc-900">
      <div className="flex items-center gap-6 text-sm">
        <div>
          <span className="text-xs text-muted-foreground">{t('selectedPoint')}</span>
          <p className="font-medium">{monthLabel}</p>
        </div>
        <div>
          <span className="text-xs text-muted-foreground">{type}</span>
          <p className="font-semibold tabular-nums">{formatCurrency(cost)}</p>
        </div>
        {!dataPoint.is_historical && dataPoint.confidence_lower && dataPoint.confidence_upper && (
          <div>
            <span className="text-xs text-muted-foreground">{t('confidenceRange')}</span>
            <p className="text-xs tabular-nums">
              {formatCurrency(Number(dataPoint.confidence_lower))} – {formatCurrency(Number(dataPoint.confidence_upper))}
            </p>
          </div>
        )}
        {hasAdjustments && adjustedCost != null && !dataPoint.is_historical && (
          <div>
            <span className="text-xs text-muted-foreground">{t('adjusted')}</span>
            <p className="font-semibold tabular-nums text-amber-600">
              {formatCurrency(adjustedCost)}
              {difference != null && (
                <span className={`text-xs ml-1 ${difference > 0 ? 'text-red-500' : difference < 0 ? 'text-emerald-500' : ''}`}>
                  ({difference > 0 ? '+' : ''}{formatCurrency(difference)})
                </span>
              )}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
