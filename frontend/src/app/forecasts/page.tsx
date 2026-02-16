'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth, Permissions } from '@/components/auth-provider';
import dynamic from 'next/dynamic';
import { AppLayout } from '@/components/layout/app-layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { ForecastSummaryCards } from '@/components/forecasts/ForecastSummaryCards';
import { ProviderForecastTable } from '@/components/forecasts/ProviderForecastTable';
import { DepartmentForecastTable } from '@/components/forecasts/DepartmentForecastTable';
import { ForecastAdjustments } from '@/components/forecasts/ForecastAdjustments';
import { DataPointDetail } from '@/components/forecasts/DataPointDetail';
import { useForecasts, ForecastHorizon, HistoryDepth, ForecastGranularity } from '@/hooks/use-forecasts';

const ForecastChart = dynamic(
  () => import('@/components/charts/ForecastChart').then((mod) => mod.ForecastChart),
  {
    loading: () => (
      <div className="flex items-center justify-center h-72">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    ),
    ssr: false,
  }
);

const HORIZONS: { value: ForecastHorizon; key: string }[] = [
  { value: 3, key: 'months3' },
  { value: 6, key: 'months6' },
  { value: 12, key: 'months12' },
  { value: 24, key: 'months24' },
];

const HISTORY_DEPTHS: { value: HistoryDepth; key: string }[] = [
  { value: 3, key: 'history3' },
  { value: 6, key: 'history6' },
  { value: 12, key: 'history12' },
  { value: 24, key: 'history24' },
];

export default function ForecastsPage() {
  const t = useTranslations('forecasts');
  const router = useRouter();
  const { hasPermission, isLoading: authLoading } = useAuth();

  const {
    forecast,
    adjustedForecast,
    loading,
    adjusting,
    activeDataPoints,
    horizon,
    setHorizon,
    historyDepth,
    setHistoryDepth,
    granularity,
    setGranularity,
    selectedProvider,
    setSelectedProvider,
    selectedDataPoint,
    selectedIndex,
    setSelectedDataPoint,
    priceAdjustment,
    setPriceAdjustment,
    headcountChange,
    setHeadcountChange,
    hasAdjustments,
    resetAdjustments,
    providerPriceAdjustment,
    setProviderPriceAdjustment,
    providerLicenseChange,
    setProviderLicenseChange,
    providerAdjusting,
    providerAdjustedForecast,
    hasProviderAdjustments,
    resetProviderAdjustments,
  } = useForecasts();

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.REPORTS_VIEW)) {
      router.push('/unauthorized');
      return;
    }
  }, [authLoading, hasPermission, router]);

  if (authLoading || loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-sm">{t('loading')}</span>
          </div>
        </div>
      </AppLayout>
    );
  }

  // Get the adjusted data point at the selected index
  const adjustedDataPoint = selectedIndex != null && adjustedForecast
    ? adjustedForecast.data_points[selectedIndex] ?? null
    : null;

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              {t('title')}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">{t('subtitle')}</p>
          </div>
          <div className="flex items-center gap-3">
            {/* History depth selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{t('historyDepth')}:</span>
              <Select
                value={String(historyDepth)}
                onValueChange={(v) => setHistoryDepth(Number(v) as HistoryDepth)}
              >
                <SelectTrigger className="w-[130px] h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {HISTORY_DEPTHS.map((h) => (
                    <SelectItem key={h.value} value={String(h.value)} className="text-xs">
                      {t(h.key)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {/* Horizon selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{t('horizon')}:</span>
              <Select
                value={String(horizon)}
                onValueChange={(v) => setHorizon(Number(v) as ForecastHorizon)}
              >
                <SelectTrigger className="w-[130px] h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {HORIZONS.map((h) => (
                    <SelectItem key={h.value} value={String(h.value)} className="text-xs">
                      {t(h.key)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Summary cards */}
        {forecast && (
          <ForecastSummaryCards
            currentMonthly={forecast.current_monthly_cost}
            projectedMonthly={forecast.projected_monthly_cost}
            projectedAnnual={forecast.projected_annual_cost}
            changePercent={forecast.change_percent}
            adjustedProjectedMonthly={adjustedForecast?.projected_monthly_cost}
            adjustedProjectedAnnual={adjustedForecast?.projected_annual_cost}
            adjustedChangePercent={adjustedForecast?.change_percent}
          />
        )}

        {/* Main content with tabs */}
        <Tabs
          value={granularity}
          onValueChange={(v) => {
            setGranularity(v as ForecastGranularity);
            setSelectedProvider(null);
          }}
        >
          <TabsList>
            <TabsTrigger value="total">{t('tabTotal')}</TabsTrigger>
            <TabsTrigger value="provider">{t('tabByProvider')}</TabsTrigger>
            <TabsTrigger value="department">{t('tabByDepartment')}</TabsTrigger>
          </TabsList>

          {/* Total view */}
          <TabsContent value="total" className="space-y-4 mt-4">
            <div className="flex gap-4">
              {/* Chart */}
              <Card className="flex-1">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{t('forecast')}</CardTitle>
                </CardHeader>
                <CardContent>
                  {forecast && (
                    <ForecastChart
                      dataPoints={forecast.data_points}
                      adjustedPoints={hasAdjustments ? adjustedForecast?.data_points : undefined}
                      selectedIndex={selectedIndex}
                      onDataPointClick={(dp, idx) => setSelectedDataPoint(dp, idx)}
                    />
                  )}
                </CardContent>
              </Card>

              {/* Adjustments sidebar */}
              <ForecastAdjustments
                priceAdjustment={priceAdjustment}
                onPriceAdjustmentChange={setPriceAdjustment}
                headcountChange={headcountChange}
                onHeadcountChangeChange={setHeadcountChange}
                onReset={resetAdjustments}
                hasAdjustments={hasAdjustments}
                adjusting={adjusting}
              />
            </div>

            {/* Data point detail */}
            <DataPointDetail
              dataPoint={selectedDataPoint}
              adjustedDataPoint={adjustedDataPoint}
              hasAdjustments={hasAdjustments}
            />
          </TabsContent>

          {/* Provider view */}
          <TabsContent value="provider" className="space-y-6 mt-4">
            {selectedProvider ? (
              <div className="flex gap-4">
                <Card className="flex-1">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">
                        {selectedProvider.display_name}
                      </CardTitle>
                      <button
                        onClick={() => setSelectedProvider(null)}
                        className="text-xs text-muted-foreground hover:text-foreground"
                      >
                        &larr; {t('tabByProvider')}
                      </button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ForecastChart
                      dataPoints={selectedProvider.data_points}
                      adjustedPoints={hasProviderAdjustments ? providerAdjustedForecast?.data_points : undefined}
                      onDataPointClick={(dp, idx) => setSelectedDataPoint(dp, idx)}
                      selectedIndex={selectedIndex}
                    />
                  </CardContent>
                </Card>

                {/* Provider adjustments sidebar */}
                <ForecastAdjustments
                  priceAdjustment={providerPriceAdjustment}
                  onPriceAdjustmentChange={setProviderPriceAdjustment}
                  headcountChange={providerLicenseChange}
                  onHeadcountChangeChange={setProviderLicenseChange}
                  onReset={resetProviderAdjustments}
                  hasAdjustments={hasProviderAdjustments}
                  adjusting={providerAdjusting}
                  headcountLabel={t('licenseChange')}
                  headcountMin={-500}
                  headcountMax={500}
                />
              </div>
            ) : (
              <Card>
                <CardContent className="pt-4">
                  {forecast && (
                    <ProviderForecastTable
                      providers={adjustedForecast?.by_provider ?? forecast.by_provider}
                      onProviderClick={setSelectedProvider}
                    />
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Department view */}
          <TabsContent value="department" className="mt-4">
            <Card>
              <CardContent className="pt-4">
                {forecast && (
                  <DepartmentForecastTable departments={forecast.by_department} />
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
