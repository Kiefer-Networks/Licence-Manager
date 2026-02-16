'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  api,
  ForecastSummary,
  ScenarioAdjustment,
  ScenarioResult,
  ScenarioType,
  ProviderForecast,
} from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';

export type ForecastHorizon = 3 | 6 | 12 | 24;
export type ForecastGranularity = 'total' | 'provider' | 'department';

export interface UseForecastsReturn {
  // Data
  forecast: ForecastSummary | null;
  loading: boolean;
  scenarioResult: ScenarioResult | null;
  scenarioLoading: boolean;

  // Filter states
  horizon: ForecastHorizon;
  setHorizon: (h: ForecastHorizon) => void;
  granularity: ForecastGranularity;
  setGranularity: (g: ForecastGranularity) => void;

  // Drill-down
  selectedProvider: ProviderForecast | null;
  setSelectedProvider: (p: ProviderForecast | null) => void;

  // Scenario
  adjustments: ScenarioAdjustment[];
  addAdjustment: () => void;
  removeAdjustment: (index: number) => void;
  updateAdjustment: (index: number, update: Partial<ScenarioAdjustment>) => void;
  runSimulation: () => Promise<void>;
  resetScenario: () => void;

  // Derived
  departments: string[];
}

const DEFAULT_ADJUSTMENT: ScenarioAdjustment = {
  type: 'add_employees' as ScenarioType,
  value: 1,
  effective_month: 1,
};

export function useForecasts(): UseForecastsReturn {
  const [forecast, setForecast] = useState<ForecastSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [horizon, setHorizon] = useState<ForecastHorizon>(12);
  const [granularity, setGranularity] = useState<ForecastGranularity>('total');
  const [selectedProvider, setSelectedProvider] = useState<ProviderForecast | null>(null);
  const [adjustments, setAdjustments] = useState<ScenarioAdjustment[]>([]);
  const [scenarioResult, setScenarioResult] = useState<ScenarioResult | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);

  // Load forecast data
  useEffect(() => {
    const loadForecast = async () => {
      setLoading(true);
      try {
        const data = await api.getForecast({ months: horizon });
        setForecast(data);
      } catch (e) {
        handleSilentError('loadForecast', e);
      } finally {
        setLoading(false);
      }
    };
    loadForecast();
  }, [horizon]);

  // Clear scenario when horizon changes
  useEffect(() => {
    setScenarioResult(null);
  }, [horizon]);

  // Derived departments list
  const departments = useMemo(() => {
    if (!forecast) return [];
    return forecast.by_department.map((d) => d.department).sort();
  }, [forecast]);

  const addAdjustment = useCallback(() => {
    setAdjustments((prev) => [...prev, { ...DEFAULT_ADJUSTMENT }]);
  }, []);

  const removeAdjustment = useCallback((index: number) => {
    setAdjustments((prev) => prev.filter((_, i) => i !== index));
    setScenarioResult(null);
  }, []);

  const updateAdjustment = useCallback(
    (index: number, update: Partial<ScenarioAdjustment>) => {
      setAdjustments((prev) =>
        prev.map((adj, i) => (i === index ? { ...adj, ...update } : adj))
      );
      setScenarioResult(null);
    },
    []
  );

  const runSimulation = useCallback(async () => {
    if (adjustments.length === 0) return;
    setScenarioLoading(true);
    try {
      const result = await api.simulateScenario({
        forecast_months: horizon,
        adjustments,
      });
      setScenarioResult(result);
    } catch (e) {
      handleSilentError('runSimulation', e);
    } finally {
      setScenarioLoading(false);
    }
  }, [adjustments, horizon]);

  const resetScenario = useCallback(() => {
    setAdjustments([]);
    setScenarioResult(null);
  }, []);

  return {
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
  };
}
