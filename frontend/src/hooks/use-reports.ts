'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  api,
  InactiveLicenseReport,
  OffboardingReport,
  CostReport,
  ExternalUsersReport,
  ExpiringContractsReport,
  UtilizationReport,
  CostTrendReport,
  DuplicateAccountsReport,
  CostsByDepartmentReport,
  CostsByEmployeeReport,
} from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import { exportInactiveLicenses, exportOffboarding, exportExternalUsers, exportCosts, ExportTranslations } from '@/lib/export';

/**
 * Return type for the useReports hook.
 */
export interface UseReportsReturn {
  // Report data
  inactiveReport: InactiveLicenseReport | null;
  offboardingReport: OffboardingReport | null;
  costReport: CostReport | null;
  externalUsersReport: ExternalUsersReport | null;
  expiringContractsReport: ExpiringContractsReport | null;
  utilizationReport: UtilizationReport | null;
  costTrendReport: CostTrendReport | null;
  duplicateAccountsReport: DuplicateAccountsReport | null;
  costsByDepartmentReport: CostsByDepartmentReport | null;
  costsByEmployeeReport: CostsByEmployeeReport | null;

  // Filter state
  departments: string[];
  selectedDepartment: string;
  setSelectedDepartment: (dept: string) => void;
  minCostFilter: string;
  setMinCostFilter: (val: string) => void;

  // Tab state
  activeTab: string;
  setActiveTab: (tab: string) => void;
  tabLoading: Set<string>;

  // Export translations
  exportTranslations: ExportTranslations;

  // Export handlers
  handleExportInactive: () => void;
  handleExportOffboarding: () => void;
  handleExportExternalUsers: () => void;
  handleExportCosts: () => void;
}

/**
 * Custom hook that encapsulates all business logic for the Reports page.
 * Manages report data, filters, tab loading, and export functionality.
 */
export function useReports(
  t: (key: string, params?: Record<string, string | number>) => string,
  tCommon: (key: string) => string,
  tLicenses: (key: string) => string,
  tExport: (key: string) => string,
): UseReportsReturn {
  // Build export translations object
  const exportTranslations: ExportTranslations = {
    provider: tExport('provider'),
    userId: tExport('userId'),
    employee: tExport('employee'),
    email: tExport('email'),
    daysInactive: tExport('daysInactive'),
    monthlyCost: tExport('monthlyCost'),
    terminationDate: tExport('terminationDate'),
    daysSinceOffboarding: tExport('daysSinceOffboarding'),
    pendingLicenses: tExport('pendingLicenses'),
    licenseCount: tExport('licenseCount'),
    externalEmail: tExport('externalEmail'),
    assignedEmployee: tExport('assignedEmployee'),
    employeeEmail: tExport('employeeEmail'),
    status: tExport('status'),
    licenseType: tExport('licenseType'),
    licenses: tExport('licenses'),
    total: tExport('total'),
    unassigned: tExport('unassigned'),
  };

  // Report data state
  const [inactiveReport, setInactiveReport] = useState<InactiveLicenseReport | null>(null);
  const [offboardingReport, setOffboardingReport] = useState<OffboardingReport | null>(null);
  const [costReport, setCostReport] = useState<CostReport | null>(null);
  const [externalUsersReport, setExternalUsersReport] = useState<ExternalUsersReport | null>(null);
  const [expiringContractsReport, setExpiringContractsReport] = useState<ExpiringContractsReport | null>(null);
  const [utilizationReport, setUtilizationReport] = useState<UtilizationReport | null>(null);
  const [costTrendReport, setCostTrendReport] = useState<CostTrendReport | null>(null);
  const [duplicateAccountsReport, setDuplicateAccountsReport] = useState<DuplicateAccountsReport | null>(null);
  const [costsByDepartmentReport, setCostsByDepartmentReport] = useState<CostsByDepartmentReport | null>(null);
  const [costsByEmployeeReport, setCostsByEmployeeReport] = useState<CostsByEmployeeReport | null>(null);

  // Filter state
  const [departments, setDepartments] = useState<string[]>([]);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [minCostFilter, setMinCostFilter] = useState<string>('');
  const [debouncedMinCost, setDebouncedMinCost] = useState<string>('');

  // Tab state for lazy loading
  const [activeTab, setActiveTab] = useState('utilization');
  const [loadedTabs, setLoadedTabs] = useState<Set<string>>(new Set());
  const [tabLoading, setTabLoading] = useState<Set<string>>(new Set());

  // Load departments once
  useEffect(() => {
    api.getDepartments().then(setDepartments).catch((e) => handleSilentError('getDepartments', e));
  }, []);

  // Debounce min cost filter
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedMinCost(minCostFilter);
    }, 500);
    return () => clearTimeout(timer);
  }, [minCostFilter]);

  // Helper to mark tab as loading
  const setTabLoadingState = useCallback((tab: string, isLoading: boolean) => {
    setTabLoading(prev => {
      const next = new Set(prev);
      if (isLoading) next.add(tab);
      else next.delete(tab);
      return next;
    });
  }, []);

  // Load data for a specific tab
  const loadTabData = useCallback(async (tab: string, forceReload = false) => {
    // Skip if already loaded and not forcing reload
    if (loadedTabs.has(tab) && !forceReload) return;

    const dept = selectedDepartment !== 'all' ? selectedDepartment : undefined;
    setTabLoadingState(tab, true);

    try {
      switch (tab) {
        case 'utilization': {
          const [utilization, costTrend] = await Promise.all([
            api.getUtilizationReport(),
            api.getCostTrendReport(6),
          ]);
          setUtilizationReport(utilization);
          setCostTrendReport(costTrend);
          break;
        }
        case 'expiring': {
          const expiring = await api.getExpiringContractsReport(90);
          setExpiringContractsReport(expiring);
          break;
        }
        case 'duplicates': {
          const duplicates = await api.getDuplicateAccountsReport();
          setDuplicateAccountsReport(duplicates);
          break;
        }
        case 'inactive': {
          const inactive = await api.getInactiveLicenseReport(30, dept);
          setInactiveReport(inactive);
          break;
        }
        case 'offboarding': {
          const offboarding = await api.getOffboardingReport(dept);
          setOffboardingReport(offboarding);
          break;
        }
        case 'external': {
          const external = await api.getExternalUsersReport(dept);
          setExternalUsersReport(external);
          break;
        }
        case 'costs': {
          const costs = await api.getCostReport(undefined, undefined, dept);
          setCostReport(costs);
          break;
        }
        case 'costs-department': {
          const costsByDept = await api.getCostsByDepartmentReport();
          setCostsByDepartmentReport(costsByDept);
          break;
        }
        case 'costs-employee': {
          const costsByEmployee = await api.getCostsByEmployeeReport(dept, debouncedMinCost ? parseFloat(debouncedMinCost) : undefined, 100);
          setCostsByEmployeeReport(costsByEmployee);
          break;
        }
        case 'recommendations':
          // LicenseRecommendations component loads its own data
          break;
      }
      setLoadedTabs(prev => new Set(prev).add(tab));
    } catch (e) {
      handleSilentError(`load${tab}Report`, e);
    } finally {
      setTabLoadingState(tab, false);
    }
  }, [loadedTabs, selectedDepartment, debouncedMinCost, setTabLoadingState]);

  // Load initial tab on mount
  useEffect(() => {
    loadTabData('utilization');
  }, []);

  // Load data when active tab changes
  useEffect(() => {
    loadTabData(activeTab);
  }, [activeTab]);

  // Reload current tab when department changes (for department-filtered tabs)
  useEffect(() => {
    const deptFilteredTabs = ['inactive', 'offboarding', 'external', 'costs', 'costs-employee'];
    if (deptFilteredTabs.includes(activeTab) && loadedTabs.has(activeTab)) {
      loadTabData(activeTab, true);
    }
  }, [selectedDepartment]);

  // Reload costs-employee when min cost filter changes
  useEffect(() => {
    if (activeTab === 'costs-employee' && loadedTabs.has('costs-employee')) {
      loadTabData('costs-employee', true);
    }
  }, [debouncedMinCost]);

  // Export handlers
  const handleExportInactive = useCallback(() => {
    if (inactiveReport) {
      exportInactiveLicenses(
        inactiveReport.licenses,
        exportTranslations,
        selectedDepartment !== 'all' ? selectedDepartment : undefined
      );
    }
  }, [inactiveReport, exportTranslations, selectedDepartment]);

  const handleExportOffboarding = useCallback(() => {
    if (offboardingReport) {
      exportOffboarding(
        offboardingReport.employees,
        exportTranslations,
        selectedDepartment !== 'all' ? selectedDepartment : undefined
      );
    }
  }, [offboardingReport, exportTranslations, selectedDepartment]);

  const handleExportExternalUsers = useCallback(() => {
    if (externalUsersReport) {
      exportExternalUsers(
        externalUsersReport.licenses,
        exportTranslations,
        selectedDepartment !== 'all' ? selectedDepartment : undefined
      );
    }
  }, [externalUsersReport, exportTranslations, selectedDepartment]);

  const handleExportCosts = useCallback(() => {
    if (costReport) {
      exportCosts(
        costReport.monthly_costs,
        costReport.total_cost,
        exportTranslations,
        selectedDepartment !== 'all' ? selectedDepartment : undefined
      );
    }
  }, [costReport, exportTranslations, selectedDepartment]);

  return {
    // Report data
    inactiveReport,
    offboardingReport,
    costReport,
    externalUsersReport,
    expiringContractsReport,
    utilizationReport,
    costTrendReport,
    duplicateAccountsReport,
    costsByDepartmentReport,
    costsByEmployeeReport,

    // Filter state
    departments,
    selectedDepartment,
    setSelectedDepartment,
    minCostFilter,
    setMinCostFilter,

    // Tab state
    activeTab,
    setActiveTab,
    tabLoading,

    // Export translations
    exportTranslations,

    // Export handlers
    handleExportInactive,
    handleExportOffboarding,
    handleExportExternalUsers,
    handleExportCosts,
  };
}
