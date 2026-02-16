'use client';

import { useTranslations } from 'next-intl';
import { Card, CardContent } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { useLocale } from '@/components/locale-provider';

interface ForecastSummaryCardsProps {
  currentMonthly: string;
  projectedMonthly: string;
  projectedAnnual: string;
  changePercent: number;
  adjustedProjectedMonthly?: string | null;
  adjustedProjectedAnnual?: string | null;
  adjustedChangePercent?: number | null;
}

export function ForecastSummaryCards({
  currentMonthly,
  projectedMonthly,
  projectedAnnual,
  changePercent,
  adjustedProjectedMonthly,
  adjustedProjectedAnnual,
  adjustedChangePercent,
}: ForecastSummaryCardsProps) {
  const t = useTranslations('forecasts');
  const { formatCurrency } = useLocale();

  const hasAdjustments = adjustedProjectedMonthly != null;

  const effectiveChange = adjustedChangePercent ?? changePercent;
  const TrendIcon = effectiveChange > 0 ? TrendingUp : effectiveChange < 0 ? TrendingDown : Minus;
  const trendColor = effectiveChange > 0
    ? 'text-red-500'
    : effectiveChange < 0
      ? 'text-emerald-500'
      : 'text-zinc-400';

  const cards = [
    {
      label: t('currentMonthly'),
      value: formatCurrency(currentMonthly),
    },
    {
      label: t('projectedMonthly'),
      value: formatCurrency(projectedMonthly),
      adjustedValue: hasAdjustments ? formatCurrency(adjustedProjectedMonthly!) : null,
    },
    {
      label: t('projectedAnnual'),
      value: formatCurrency(projectedAnnual),
      adjustedValue: hasAdjustments && adjustedProjectedAnnual ? formatCurrency(adjustedProjectedAnnual) : null,
    },
    {
      label: t('changePercent'),
      value: `${changePercent > 0 ? '+' : ''}${changePercent}%`,
      adjustedValue: hasAdjustments && adjustedChangePercent != null
        ? `${adjustedChangePercent > 0 ? '+' : ''}${adjustedChangePercent}%`
        : null,
      icon: <TrendIcon className={`h-4 w-4 ${trendColor}`} />,
      valueColor: trendColor,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs font-medium text-muted-foreground">{card.label}</p>
            <div className="flex items-center gap-2 mt-1">
              {card.icon}
              {card.adjustedValue ? (
                <div className="flex items-baseline gap-2">
                  <p className="text-sm tabular-nums text-muted-foreground line-through">
                    {card.value}
                  </p>
                  <p className={`text-xl font-semibold tabular-nums text-amber-600`}>
                    {card.adjustedValue}
                  </p>
                </div>
              ) : (
                <p className={`text-xl font-semibold tabular-nums ${card.valueColor || ''}`}>
                  {card.value}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
