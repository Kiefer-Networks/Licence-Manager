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
  ReferenceLine,
} from 'recharts';
import { ForecastDataPoint } from '@/lib/api';
import { useLocale } from '@/components/locale-provider';

interface ForecastChartProps {
  dataPoints: ForecastDataPoint[];
  scenarioPoints?: ForecastDataPoint[];
  className?: string;
}

export function ForecastChart({
  dataPoints,
  scenarioPoints,
  className = '',
}: ForecastChartProps) {
  const t = useTranslations('forecasts');
  const { formatCurrency, numberFormat } = useLocale();

  const chartData = useMemo(() => {
    return dataPoints.map((dp, idx) => {
      const scenarioDp = scenarioPoints?.[idx];
      return {
        month: new Date(dp.month).toLocaleDateString(numberFormat, {
          month: 'short',
          year: '2-digit',
        }),
        cost: Number(dp.cost),
        isHistorical: dp.is_historical,
        historical: dp.is_historical ? Number(dp.cost) : undefined,
        projected: !dp.is_historical ? Number(dp.cost) : undefined,
        confidenceLower: dp.confidence_lower ? Number(dp.confidence_lower) : undefined,
        confidenceUpper: dp.confidence_upper ? Number(dp.confidence_upper) : undefined,
        confidenceRange: dp.confidence_lower && dp.confidence_upper
          ? [Number(dp.confidence_lower), Number(dp.confidence_upper)]
          : undefined,
        scenario: scenarioDp && !scenarioDp.is_historical
          ? Number(scenarioDp.cost)
          : undefined,
      };
    });
  }, [dataPoints, scenarioPoints, numberFormat]);

  // Find the transition point between historical and projected
  const transitionIndex = useMemo(() => {
    for (let i = 0; i < dataPoints.length; i++) {
      if (!dataPoints[i].is_historical) return i;
    }
    return dataPoints.length;
  }, [dataPoints]);

  // Add a bridge point: duplicate the last historical value as the first projected value
  const bridgedData = useMemo(() => {
    if (transitionIndex <= 0 || transitionIndex >= chartData.length) return chartData;
    const data = [...chartData];
    // Set the transition point to have both historical and projected values
    const bridgePoint = data[transitionIndex - 1];
    if (bridgePoint && data[transitionIndex]) {
      data[transitionIndex] = {
        ...data[transitionIndex],
        projected: bridgePoint.historical ?? bridgePoint.cost,
      };
    }
    return data;
  }, [chartData, transitionIndex]);

  if (dataPoints.length === 0) {
    return (
      <div className={`flex items-center justify-center h-64 text-muted-foreground ${className}`}>
        <p className="text-sm">{t('noForecastData')}</p>
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="flex items-center gap-4 mb-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-0.5 bg-blue-500" />
          <span>{t('historical')}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-0.5 bg-blue-500 border-dashed" style={{ borderTop: '2px dashed #3b82f6', height: 0 }} />
          <span>{t('projected')}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-2 bg-blue-500/10 rounded-sm" />
          <span>{t('confidenceBand')}</span>
        </div>
        {scenarioPoints && (
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-emerald-500" />
            <span>{t('scenario')}</span>
          </div>
        )}
      </div>

      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={bridgedData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="historicalGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.08} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
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
              tickFormatter={(value) => {
                if (value >= 1000) return `€${(value / 1000).toFixed(0)}k`;
                return `€${value}`;
              }}
              width={55}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e4e4e7',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                fontSize: '12px',
              }}
              formatter={(value: number, name: string) => {
                const labels: Record<string, string> = {
                  historical: t('historical'),
                  projected: t('projected'),
                  scenario: t('scenario'),
                  confidenceUpper: t('confidenceBand'),
                  confidenceLower: t('confidenceBand'),
                };
                return [formatCurrency(value), labels[name] || name];
              }}
              labelStyle={{ fontWeight: 500, marginBottom: 4 }}
            />

            {/* Confidence band - upper */}
            <Area
              type="monotone"
              dataKey="confidenceUpper"
              stroke="none"
              fill="url(#confidenceGradient)"
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />
            {/* Confidence band - lower */}
            <Area
              type="monotone"
              dataKey="confidenceLower"
              stroke="none"
              fill="#fff"
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />

            {/* Historical line - solid */}
            <Area
              type="monotone"
              dataKey="historical"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#historicalGradient)"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
              connectNulls={false}
            />

            {/* Projected line - dashed */}
            <Area
              type="monotone"
              dataKey="projected"
              stroke="#3b82f6"
              strokeWidth={2}
              strokeDasharray="6 3"
              fill="none"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
              connectNulls={false}
            />

            {/* Scenario line */}
            {scenarioPoints && (
              <Area
                type="monotone"
                dataKey="scenario"
                stroke="#10b981"
                strokeWidth={2}
                strokeDasharray="6 3"
                fill="none"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, fill: '#fff', stroke: '#10b981' }}
                connectNulls={false}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
