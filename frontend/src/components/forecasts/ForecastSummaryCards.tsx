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
}

export function ForecastSummaryCards({
  currentMonthly,
  projectedMonthly,
  projectedAnnual,
  changePercent,
}: ForecastSummaryCardsProps) {
  const t = useTranslations('forecasts');
  const { formatCurrency } = useLocale();

  const TrendIcon = changePercent > 0 ? TrendingUp : changePercent < 0 ? TrendingDown : Minus;
  const trendColor = changePercent > 0
    ? 'text-red-500'
    : changePercent < 0
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
    },
    {
      label: t('projectedAnnual'),
      value: formatCurrency(projectedAnnual),
    },
    {
      label: t('changePercent'),
      value: `${changePercent > 0 ? '+' : ''}${changePercent}%`,
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
              <p className={`text-xl font-semibold tabular-nums ${card.valueColor || ''}`}>
                {card.value}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
