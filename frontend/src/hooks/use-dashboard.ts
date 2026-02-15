'use client';

import { useEffect, useState, useMemo } from 'react';
import { api, DashboardData, PaymentMethod, LicenseLifecycleOverview } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';

/**
 * Translation functions required by the useDashboard hook.
 */
interface DashboardTranslations {
  tProviders: (key: string) => string;
}

/**
 * Return type for the useDashboard hook.
 */
export interface UseDashboardReturn {
  // Data
  dashboard: DashboardData | null;
  loading: boolean;
  syncing: boolean;
  toast: { type: 'success' | 'error'; text: string } | null;
  departments: string[];
  selectedDepartment: string;
  setSelectedDepartment: (v: string) => void;
  expiringPaymentMethods: PaymentMethod[];
  lifecycleOverview: LicenseLifecycleOverview | null;

  // Derived data
  hrisProviders: DashboardData['providers'];
  licenseProviders: DashboardData['providers'];
  totalLicenses: number;
  unassignedCount: number;
  externalCount: number;
  potentialSavings: number;
  totalCost: number;

  // Handlers
  handleSync: () => Promise<void>;
}

/**
 * Custom hook that encapsulates all business logic for the Dashboard page.
 * Manages dashboard data, filters, sync, and derived computations.
 */
export function useDashboard(
  { tProviders }: DashboardTranslations,
): UseDashboardReturn {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [departments, setDepartments] = useState<string[]>([]);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [expiringPaymentMethods, setExpiringPaymentMethods] = useState<PaymentMethod[]>([]);
  const [lifecycleOverview, setLifecycleOverview] = useState<LicenseLifecycleOverview | null>(null);

  useEffect(() => {
    Promise.all([
      api.getDepartments(),
      api.getPaymentMethods(),
      api.getLicenseLifecycleOverview(),
    ]).then(([depts, methods, lifecycle]) => {
      setDepartments(depts);
      setExpiringPaymentMethods(methods.items.filter((m) => m.is_expiring));
      setLifecycleOverview(lifecycle);
    }).catch((e) => handleSilentError('loadInitialData', e));
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [selectedDepartment]);

  async function fetchDashboard() {
    try {
      const dept = selectedDepartment !== 'all' ? selectedDepartment : undefined;
      const data = await api.getDashboard(dept);
      setDashboard(data);
    } catch (error) {
      handleSilentError('fetchDashboard', error);
    } finally {
      setLoading(false);
    }
  }

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 4000);
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await api.triggerSync();
      await fetchDashboard();
      showToast(result.success ? 'success' : 'error', result.success ? tProviders('syncSuccess') : tProviders('syncFailed'));
    } catch {
      showToast('error', tProviders('syncFailed'));
    } finally {
      setSyncing(false);
    }
  };

  const hrisProviders = useMemo(
    () => dashboard?.providers.filter((p) => p.name === 'hibob') || [],
    [dashboard?.providers]
  );
  const licenseProviders = useMemo(
    () => dashboard?.providers
      ?.filter((p) => p.name !== 'hibob')
      .sort((a, b) => a.display_name.localeCompare(b.display_name)) || [],
    [dashboard?.providers]
  );

  const totalLicenses = dashboard?.total_licenses || 0;
  const unassignedCount = dashboard?.unassigned_licenses || 0;
  const externalCount = dashboard?.external_licenses || 0;
  const potentialSavings = Number(dashboard?.potential_savings || 0);
  const totalCost = Number(dashboard?.total_monthly_cost || 0);

  return {
    // Data
    dashboard,
    loading,
    syncing,
    toast,
    departments,
    selectedDepartment,
    setSelectedDepartment,
    expiringPaymentMethods,
    lifecycleOverview,

    // Derived data
    hrisProviders,
    licenseProviders,
    totalLicenses,
    unassignedCount,
    externalCount,
    potentialSavings,
    totalCost,

    // Handlers
    handleSync,
  };
}
