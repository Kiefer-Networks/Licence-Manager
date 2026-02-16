'use client';

import { useTranslations } from 'next-intl';
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
import { ScenarioBuilder } from '@/components/forecasts/ScenarioBuilder';
import { useForecasts, ForecastHorizon, ForecastGranularity } from '@/hooks/use-forecasts';

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

export default function ForecastsPage() {
  const t = useTranslations('forecasts');
  const {
    forecast,
    loading,
    scenarioResult,
    scenarioLoading,
    horizon,
    setHorizon,
    granularity,
    setGranularity,
    selectedProvider,
    setSelectedProvider,
    adjustments,
    addAdjustment,
    removeAdjustment,
    updateAdjustment,
    runSimulation,
    resetScenario,
    departments,
  } = useForecasts();

  if (loading) {
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
          <TabsContent value="total" className="space-y-6 mt-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{t('forecast')}</CardTitle>
              </CardHeader>
              <CardContent>
                {forecast && (
                  <ForecastChart
                    dataPoints={forecast.data_points}
                    scenarioPoints={scenarioResult?.scenario}
                  />
                )}
              </CardContent>
            </Card>

            {/* Scenario builder */}
            {forecast && (
              <ScenarioBuilder
                adjustments={adjustments}
                onAddAdjustment={addAdjustment}
                onRemoveAdjustment={removeAdjustment}
                onUpdateAdjustment={updateAdjustment}
                onRunSimulation={runSimulation}
                onReset={resetScenario}
                scenarioResult={scenarioResult}
                loading={scenarioLoading}
                providers={forecast.by_provider}
                departments={departments}
              />
            )}
          </TabsContent>

          {/* Provider view */}
          <TabsContent value="provider" className="space-y-6 mt-4">
            {selectedProvider ? (
              <Card>
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
                  <ForecastChart dataPoints={selectedProvider.data_points} />
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="pt-4">
                  {forecast && (
                    <ProviderForecastTable
                      providers={forecast.by_provider}
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
