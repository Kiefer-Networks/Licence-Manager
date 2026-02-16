'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  api,
  ForecastSummary,
  ForecastDataPoint,
  ProviderForecast,
} from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';

export type ForecastHorizon = 3 | 6 | 12 | 24;
export type HistoryDepth = 3 | 6 | 12 | 24;
export type ForecastGranularity = 'total' | 'provider' | 'department';

export interface UseForecastsReturn {
  // Data
  forecast: ForecastSummary | null;
  adjustedForecast: ForecastSummary | null;
  loading: boolean;
  adjusting: boolean;

  // Active data points (adjusted if available, otherwise baseline)
  activeDataPoints: ForecastDataPoint[];

  // Filter states
  horizon: ForecastHorizon;
  setHorizon: (h: ForecastHorizon) => void;
  historyDepth: HistoryDepth;
  setHistoryDepth: (d: HistoryDepth) => void;
  granularity: ForecastGranularity;
  setGranularity: (g: ForecastGranularity) => void;

  // Drill-down
  selectedProvider: ProviderForecast | null;
  setSelectedProvider: (p: ProviderForecast | null) => void;

  // Data point selection (chart click)
  selectedDataPoint: ForecastDataPoint | null;
  selectedIndex: number | null;
  setSelectedDataPoint: (dp: ForecastDataPoint | null, index: number | null) => void;

  // Adjustments (sliders) — global (total tab)
  priceAdjustment: number;
  setPriceAdjustment: (v: number) => void;
  headcountChange: number;
  setHeadcountChange: (v: number) => void;
  hasAdjustments: boolean;
  resetAdjustments: () => void;

  // Adjustments — provider-specific
  providerPriceAdjustment: number;
  setProviderPriceAdjustment: (v: number) => void;
  providerLicenseChange: number;
  setProviderLicenseChange: (v: number) => void;
  providerAdjusting: boolean;
  providerAdjustedForecast: ProviderForecast | null;
  hasProviderAdjustments: boolean;
  resetProviderAdjustments: () => void;

  // Derived
  departments: string[];
}

export function useForecasts(): UseForecastsReturn {
  const [forecast, setForecast] = useState<ForecastSummary | null>(null);
  const [adjustedForecast, setAdjustedForecast] = useState<ForecastSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [adjusting, setAdjusting] = useState(false);
  const [horizon, setHorizon] = useState<ForecastHorizon>(12);
  const [historyDepth, setHistoryDepth] = useState<HistoryDepth>(6);
  const [granularity, setGranularity] = useState<ForecastGranularity>('total');
  const [selectedProvider, setSelectedProvider] = useState<ProviderForecast | null>(null);
  const [selectedDataPoint, setSelectedDataPointState] = useState<ForecastDataPoint | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [priceAdjustment, setPriceAdjustment] = useState(0);
  const [headcountChange, setHeadcountChange] = useState(0);

  // Provider-specific adjustment state
  const [providerPriceAdjustment, setProviderPriceAdjustment] = useState(0);
  const [providerLicenseChange, setProviderLicenseChange] = useState(0);
  const [providerAdjusting, setProviderAdjusting] = useState(false);
  const [providerAdjustedForecast, setProviderAdjustedForecast] = useState<ProviderForecast | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const providerDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hasAdjustments = priceAdjustment !== 0 || headcountChange !== 0;
  const hasProviderAdjustments = providerPriceAdjustment !== 0 || providerLicenseChange !== 0;

  // Load baseline forecast data
  useEffect(() => {
    const loadForecast = async () => {
      setLoading(true);
      try {
        const data = await api.getForecast({
          months: horizon,
          history_months: historyDepth,
        });
        setForecast(data);
      } catch (e) {
        handleSilentError('loadForecast', e);
      } finally {
        setLoading(false);
      }
    };
    loadForecast();
  }, [horizon, historyDepth]);

  // Clear adjustments when horizon/history changes
  useEffect(() => {
    setAdjustedForecast(null);
    setSelectedDataPointState(null);
    setSelectedIndex(null);
  }, [horizon, historyDepth]);

  // Debounced adjusted forecast API call
  useEffect(() => {
    if (!hasAdjustments) {
      setAdjustedForecast(null);
      return;
    }

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(async () => {
      setAdjusting(true);
      try {
        const result = await api.getAdjustedForecast({
          forecast_months: horizon,
          history_months: historyDepth,
          price_adjustment_percent: priceAdjustment,
          headcount_change: headcountChange,
        });
        setAdjustedForecast(result);
      } catch (e) {
        handleSilentError('getAdjustedForecast', e);
      } finally {
        setAdjusting(false);
      }
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [priceAdjustment, headcountChange, horizon, historyDepth, hasAdjustments]);

  // Reset provider adjustments when selectedProvider changes
  useEffect(() => {
    setProviderPriceAdjustment(0);
    setProviderLicenseChange(0);
    setProviderAdjustedForecast(null);
  }, [selectedProvider?.provider_id]);

  // Debounced provider-specific adjusted forecast API call
  useEffect(() => {
    if (!hasProviderAdjustments || !selectedProvider) {
      setProviderAdjustedForecast(null);
      return;
    }

    if (providerDebounceRef.current) {
      clearTimeout(providerDebounceRef.current);
    }

    providerDebounceRef.current = setTimeout(async () => {
      setProviderAdjusting(true);
      try {
        const result = await api.getAdjustedForecast({
          forecast_months: horizon,
          history_months: historyDepth,
          price_adjustment_percent: providerPriceAdjustment,
          headcount_change: providerLicenseChange,
          provider_id: selectedProvider.provider_id,
        });
        // Extract the provider-level data points from the adjusted result
        setProviderAdjustedForecast({
          ...selectedProvider,
          data_points: result.data_points,
          projected_cost: result.projected_monthly_cost,
          change_percent: result.change_percent,
        });
      } catch (e) {
        handleSilentError('getProviderAdjustedForecast', e);
      } finally {
        setProviderAdjusting(false);
      }
    }, 300);

    return () => {
      if (providerDebounceRef.current) {
        clearTimeout(providerDebounceRef.current);
      }
    };
  }, [providerPriceAdjustment, providerLicenseChange, horizon, historyDepth, hasProviderAdjustments, selectedProvider]);

  // Active data points: adjusted if available, otherwise baseline
  const activeDataPoints = useMemo(() => {
    const source = adjustedForecast ?? forecast;
    return source?.data_points ?? [];
  }, [adjustedForecast, forecast]);

  // Derived departments list
  const departments = useMemo(() => {
    if (!forecast) return [];
    return forecast.by_department.map((d) => d.department).sort();
  }, [forecast]);

  const setSelectedDataPoint = useCallback(
    (dp: ForecastDataPoint | null, index: number | null) => {
      setSelectedDataPointState(dp);
      setSelectedIndex(index);
    },
    []
  );

  const resetAdjustments = useCallback(() => {
    setPriceAdjustment(0);
    setHeadcountChange(0);
    setAdjustedForecast(null);
  }, []);

  const resetProviderAdjustments = useCallback(() => {
    setProviderPriceAdjustment(0);
    setProviderLicenseChange(0);
    setProviderAdjustedForecast(null);
  }, []);

  return {
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
    departments,
  };
}
