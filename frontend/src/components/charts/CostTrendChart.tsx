'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { CostTrendEntry } from '@/lib/api';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { getLocale } from '@/lib/locale';

interface CostTrendChartProps {
  data: CostTrendEntry[];
  trendDirection: 'up' | 'down' | 'stable';
  percentChange: number;
  className?: string;
}

export function CostTrendChart({
  data,
  trendDirection,
  percentChange,
  className = '',
}: CostTrendChartProps) {
  const t = useTranslations('dashboard');
  const chartData = useMemo(() => {
    return data.map((entry) => ({
      month: new Date(entry.month).toLocaleDateString(getLocale(), {
        month: 'short',
        year: '2-digit',
      }),
      cost: Number(entry.total_cost),
      licenses: entry.license_count,
    }));
  }, [data]);

  const currentCost = data.length > 0 ? Number(data[data.length - 1].total_cost) : 0;

  const formatCost = (value: number) => {
    return `EUR ${value.toLocaleString(getLocale(), { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  };

  const TrendIcon = trendDirection === 'up' ? TrendingUp : trendDirection === 'down' ? TrendingDown : Minus;
  const trendColor = trendDirection === 'up' ? 'text-red-500' : trendDirection === 'down' ? 'text-emerald-500' : 'text-zinc-400';
  const trendTextColor = trendDirection === 'up' ? 'text-red-600' : trendDirection === 'down' ? 'text-emerald-600' : 'text-zinc-500';

  if (data.length === 0) {
    return (
      <div className={`flex items-center justify-center h-64 text-muted-foreground ${className}`}>
        <p className="text-sm">{t('noCostTrendData')}</p>
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{t('costTrend')}</p>
          <div className="flex items-center gap-2 mt-1">
            <TrendIcon className={`h-4 w-4 ${trendColor}`} />
            <span className={`text-sm font-medium ${trendTextColor}`}>
              {percentChange > 0 ? '+' : ''}{percentChange}%
            </span>
            <span className="text-xs text-muted-foreground">
              {t('vsMonthsAgo', { months: data.length })}
            </span>
          </div>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold tabular-nums">
            {formatCost(currentCost)}
          </p>
          <p className="text-xs text-muted-foreground">{t('currentMonthly')}</p>
        </div>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
            <XAxis
              dataKey="month"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: '#71717a' }}
              dy={10}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: '#71717a' }}
              tickFormatter={(value) => `€${(value / 1000).toFixed(0)}k`}
              width={50}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e4e4e7',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                fontSize: '12px',
              }}
              formatter={(value: number) => [formatCost(value), t('costLabel')]}
              labelStyle={{ fontWeight: 500, marginBottom: 4 }}
            />
            <Area
              type="monotone"
              dataKey="cost"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#costGradient)"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
