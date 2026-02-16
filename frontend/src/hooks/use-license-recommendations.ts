'use client';

import { useEffect, useState } from 'react';
import { api, LicenseRecommendationsReport, Provider } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';

interface UseLicenseRecommendationsProps {
  department?: string;
}

export interface UseLicenseRecommendationsReturn {
  report: LicenseRecommendationsReport | null;
  loading: boolean;
  providers: Provider[];
  selectedProvider: string;
  setSelectedProvider: (value: string) => void;
  minDaysInactive: number;
  setMinDaysInactive: (value: number) => void;
}

/**
 * Custom hook that encapsulates all business logic for the LicenseRecommendations component.
 * Manages loading providers, fetching recommendations based on filters, and filter state.
 */
export function useLicenseRecommendations({
  department,
}: UseLicenseRecommendationsProps): UseLicenseRecommendationsReturn {
  const [report, setReport] = useState<LicenseRecommendationsReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>('all');
  const [minDaysInactive, setMinDaysInactive] = useState<number>(60);

  // Load providers once
  useEffect(() => {
    api.getProviders().then((res) => setProviders(res.items)).catch((e) => handleSilentError('getProviders', e));
  }, []);

  // Load recommendations when filters change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    api.getLicenseRecommendations({
      min_days_inactive: minDaysInactive,
      department: department,
      provider_id: selectedProvider !== 'all' ? selectedProvider : undefined,
      limit: 100,
    }).then((data) => {
      if (!cancelled) {
        setReport(data);
      }
    }).catch((e) => handleSilentError('getLicenseRecommendations', e))
      .finally(() => !cancelled && setLoading(false));

    return () => { cancelled = true; };
  }, [department, selectedProvider, minDaysInactive]);

  return {
    report,
    loading,
    providers,
    selectedProvider,
    setSelectedProvider,
    minDaysInactive,
    setMinDaysInactive,
  };
}
