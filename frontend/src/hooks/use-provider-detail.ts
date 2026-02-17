'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  api,
  Provider,
  License,
  Employee,
  LicenseTypeInfo,
  LicenseTypePricing,
  PackagePricing,
  ProviderFile,
  CategorizedLicensesResponse,
  IndividualLicenseTypeInfo,
  PaymentMethod,
  LicensePackage,
  OrganizationLicense,
} from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import { SEAT_BASED_PROVIDERS, FIGMA_LICENSE_TYPES } from '@/lib/constants';
import type { PricingEditState } from '@/components/providers/detail/types';

/**
 * Toast state for user feedback.
 */
export interface Toast {
  type: 'success' | 'error';
  text: string;
}

/**
 * License statistics computed from categorized data.
 */
export interface LicenseStats {
  totalLicenses: number;
  assignedLicenses: number;
  unassignedLicenses: number;
  notInHrisLicenses: number;
  externalLicenses: number;
  inactiveLicenses: number;
  totalMonthlyCost: number;
  availableSeats: number | null;
}

/**
 * Return type for the useProviderDetail hook.
 */
export interface UseProviderDetailReturn {
  // Core data
  provider: Provider | null;
  licenses: License[];
  categorizedLicenses: CategorizedLicensesResponse | null;
  employees: Employee[];
  loading: boolean;

  // Computed values
  isManual: boolean;
  isSeatBased: boolean;
  stats: LicenseStats;

  // Tab state
  activeTab: Tab;
  setActiveTab: (tab: Tab) => void;

  // Toast
  toast: Toast | null;
  showToast: (type: 'success' | 'error', text: string) => void;

  // Sync
  syncing: boolean;
  handleSync: () => Promise<void>;

  // Import dialog
  importDialogOpen: boolean;
  setImportDialogOpen: (open: boolean) => void;

  // Add License
  addLicenseOpen: boolean;
  setAddLicenseOpen: (open: boolean) => void;
  addLicenseMode: 'single' | 'bulk' | 'seats';
  setAddLicenseMode: (mode: 'single' | 'bulk' | 'seats') => void;
  licenseForm: LicenseFormState;
  setLicenseForm: React.Dispatch<React.SetStateAction<LicenseFormState>>;
  bulkKeys: string;
  setBulkKeys: (keys: string) => void;
  savingLicense: boolean;
  handleAddLicense: () => Promise<void>;

  // Assign
  assignDialog: License | null;
  setAssignDialog: (license: License | null) => void;
  selectedEmployeeId: string;
  setSelectedEmployeeId: (id: string) => void;
  handleAssign: () => Promise<void>;
  handleUnassign: (license: License) => Promise<void>;

  // Delete
  deleteDialog: License | null;
  setDeleteDialog: (license: License | null) => void;
  handleDeleteLicense: () => Promise<void>;

  // Service Account
  serviceAccountDialog: License | null;
  serviceAccountForm: ServiceAccountFormState;
  setServiceAccountForm: React.Dispatch<React.SetStateAction<ServiceAccountFormState>>;
  savingServiceAccount: boolean;
  handleOpenServiceAccountDialog: (license: License) => void;
  handleSaveServiceAccount: () => Promise<void>;
  setServiceAccountDialog: (license: License | null) => void;

  // Admin Account
  adminAccountDialog: License | null;
  adminAccountForm: AdminAccountFormState;
  setAdminAccountForm: React.Dispatch<React.SetStateAction<AdminAccountFormState>>;
  savingAdminAccount: boolean;
  handleOpenAdminAccountDialog: (license: License) => void;
  handleSaveAdminAccount: () => Promise<void>;
  setAdminAccountDialog: (license: License | null) => void;

  // License Type
  licenseTypeDialog: License | null;
  selectedLicenseType: string;
  setSelectedLicenseType: (type: string) => void;
  savingLicenseType: boolean;
  handleOpenLicenseTypeDialog: (license: License) => void;
  handleSaveLicenseType: () => Promise<void>;
  setLicenseTypeDialog: (license: License | null) => void;

  // Match suggestions
  handleConfirmMatch: (license: License) => Promise<void>;
  handleRejectMatch: (license: License) => Promise<void>;

  // Settings
  settingsForm: SettingsFormState;
  setSettingsForm: React.Dispatch<React.SetStateAction<SettingsFormState>>;
  savingSettings: boolean;
  handleSaveSettings: () => Promise<void>;
  paymentMethods: PaymentMethod[];

  // Credentials
  credentialsForm: Record<string, string>;
  setCredentialsForm: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  savingCredentials: boolean;
  showCredentialsEdit: boolean;
  setShowCredentialsEdit: (show: boolean) => void;
  publicCredentials: Record<string, string>;
  handleSaveCredentials: () => Promise<void>;

  // Delete Provider
  deleteProviderOpen: boolean;
  setDeleteProviderOpen: (open: boolean) => void;
  handleDeleteProvider: () => void;

  // Pricing
  licenseTypes: LicenseTypeInfo[];
  pricingEdits: Record<string, PricingEditState>;
  setPricingEdits: React.Dispatch<React.SetStateAction<Record<string, PricingEditState>>>;
  savingPricing: boolean;
  handleSavePricing: () => Promise<void>;

  // Individual pricing
  individualLicenseTypes: IndividualLicenseTypeInfo[];
  hasCombinedTypes: boolean;
  individualPricingEdits: Record<string, Omit<PricingEditState, 'next_billing_date'>>;
  setIndividualPricingEdits: React.Dispatch<React.SetStateAction<Record<string, Omit<PricingEditState, 'next_billing_date'>>>>;
  savingIndividualPricing: boolean;
  handleSaveIndividualPricing: () => Promise<void>;

  // Files
  files: ProviderFile[];
  uploadingFile: boolean;
  fileDescription: string;
  setFileDescription: (desc: string) => void;
  fileCategory: string;
  setFileCategory: (cat: string) => void;
  handleFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
  handleDeleteFile: (fileId: string) => Promise<void>;

  // License Packages
  licensePackages: LicensePackage[];
  packageDialogOpen: boolean;
  setPackageDialogOpen: (open: boolean) => void;
  editingPackage: LicensePackage | null;
  packageForm: PackageFormState;
  setPackageForm: React.Dispatch<React.SetStateAction<PackageFormState>>;
  savingPackage: boolean;
  handleOpenPackageDialog: (pkg?: LicensePackage) => void;
  handleSavePackage: () => Promise<void>;
  handleDeletePackage: (pkg: LicensePackage) => Promise<void>;

  // Organization Licenses
  orgLicenses: OrganizationLicense[];
  orgLicenseDialogOpen: boolean;
  setOrgLicenseDialogOpen: (open: boolean) => void;
  editingOrgLicense: OrganizationLicense | null;
  orgLicenseForm: OrgLicenseFormState;
  setOrgLicenseForm: React.Dispatch<React.SetStateAction<OrgLicenseFormState>>;
  savingOrgLicense: boolean;
  handleOpenOrgLicenseDialog: (lic?: OrganizationLicense) => void;
  handleSaveOrgLicense: () => Promise<void>;
  handleDeleteOrgLicense: (lic: OrganizationLicense) => Promise<void>;

  // Fetch functions (for external refresh)
  fetchLicenses: () => Promise<void>;
  fetchCategorizedLicenses: () => Promise<void>;
}

export type Tab = 'overview' | 'licenses' | 'pricing' | 'files' | 'settings';

interface LicenseFormState {
  license_type: string;
  license_key: string;
  quantity: string;
  monthly_cost: string;
  valid_until: string;
  notes: string;
}

interface ServiceAccountFormState {
  is_service_account: boolean;
  service_account_name: string;
  service_account_owner_id: string;
  apply_globally: boolean;
}

interface AdminAccountFormState {
  is_admin_account: boolean;
  admin_account_name: string;
  admin_account_owner_id: string;
  apply_globally: boolean;
}

interface SettingsFormState {
  display_name: string;
  license_model: string;
  payment_method_id: string | null;
}

interface PackageFormState {
  license_type: string;
  display_name: string;
  total_seats: string;
  cost_per_seat: string;
  currency: string;
  billing_cycle: string;
  contract_start: string;
  contract_end: string;
  auto_renew: boolean;
  notes: string;
}

interface OrgLicenseFormState {
  name: string;
  license_type: string;
  quantity: string;
  unit: string;
  monthly_cost: string;
  currency: string;
  billing_cycle: string;
  renewal_date: string;
  notes: string;
}

/**
 * Custom hook that encapsulates all business logic for the provider detail page.
 * Manages provider data, licenses, pricing, files, packages, and organization licenses.
 */
export function useProviderDetail(
  providerId: string,
  t: (key: string, params?: Record<string, string | number>) => string,
  tCommon: (key: string) => string,
  tLicenses: (key: string) => string,
): UseProviderDetailReturn {
  const router = useRouter();

  // Core data
  const [provider, setProvider] = useState<Provider | null>(null);
  const [licenses, setLicenses] = useState<License[]>([]);
  const [categorizedLicenses, setCategorizedLicenses] = useState<CategorizedLicensesResponse | null>(null);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [syncing, setSyncing] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  // Import Dialog
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  // Add License Dialog
  const [addLicenseOpen, setAddLicenseOpen] = useState(false);
  const [addLicenseMode, setAddLicenseMode] = useState<'single' | 'bulk' | 'seats'>('single');
  const [licenseForm, setLicenseForm] = useState<LicenseFormState>({
    license_type: '',
    license_key: '',
    quantity: '1',
    monthly_cost: '',
    valid_until: '',
    notes: '',
  });
  const [bulkKeys, setBulkKeys] = useState('');
  const [savingLicense, setSavingLicense] = useState(false);

  // Assign Dialog
  const [assignDialog, setAssignDialog] = useState<License | null>(null);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('');

  // Settings Form
  const [settingsForm, setSettingsForm] = useState<SettingsFormState>({
    display_name: '',
    license_model: 'license_based',
    payment_method_id: null,
  });
  const [savingSettings, setSavingSettings] = useState(false);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);

  // Credentials Form
  const [credentialsForm, setCredentialsForm] = useState<Record<string, string>>({});
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [showCredentialsEdit, setShowCredentialsEdit] = useState(false);
  const [publicCredentials, setPublicCredentials] = useState<Record<string, string>>({});

  // Delete Dialog
  const [deleteDialog, setDeleteDialog] = useState<License | null>(null);

  // Service Account Dialog
  const [serviceAccountDialog, setServiceAccountDialog] = useState<License | null>(null);
  const [serviceAccountForm, setServiceAccountForm] = useState<ServiceAccountFormState>({
    is_service_account: false,
    service_account_name: '',
    service_account_owner_id: '',
    apply_globally: false,
  });
  const [savingServiceAccount, setSavingServiceAccount] = useState(false);

  // Admin Account Dialog
  const [adminAccountDialog, setAdminAccountDialog] = useState<License | null>(null);
  const [adminAccountForm, setAdminAccountForm] = useState<AdminAccountFormState>({
    is_admin_account: false,
    admin_account_name: '',
    admin_account_owner_id: '',
    apply_globally: false,
  });
  const [savingAdminAccount, setSavingAdminAccount] = useState(false);

  // License Type Dialog
  const [licenseTypeDialog, setLicenseTypeDialog] = useState<License | null>(null);
  const [selectedLicenseType, setSelectedLicenseType] = useState('');
  const [savingLicenseType, setSavingLicenseType] = useState(false);

  // Pricing
  const [licenseTypes, setLicenseTypes] = useState<LicenseTypeInfo[]>([]);
  const [pricingEdits, setPricingEdits] = useState<Record<string, PricingEditState>>({});
  const [savingPricing, setSavingPricing] = useState(false);

  // Individual pricing (for Microsoft/Azure with combined license types)
  const [individualLicenseTypes, setIndividualLicenseTypes] = useState<IndividualLicenseTypeInfo[]>([]);
  const [hasCombinedTypes, setHasCombinedTypes] = useState(false);
  const [individualPricingEdits, setIndividualPricingEdits] = useState<Record<string, Omit<PricingEditState, 'next_billing_date'>>>({});
  const [savingIndividualPricing, setSavingIndividualPricing] = useState(false);

  // Files
  const [files, setFiles] = useState<ProviderFile[]>([]);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [fileDescription, setFileDescription] = useState('');
  const [fileCategory, setFileCategory] = useState('other');

  // License Packages
  const [licensePackages, setLicensePackages] = useState<LicensePackage[]>([]);
  const [packageDialogOpen, setPackageDialogOpen] = useState(false);
  const [editingPackage, setEditingPackage] = useState<LicensePackage | null>(null);
  const [packageForm, setPackageForm] = useState<PackageFormState>({
    license_type: '',
    display_name: '',
    total_seats: '',
    cost_per_seat: '',
    currency: 'EUR',
    billing_cycle: 'monthly',
    contract_start: '',
    contract_end: '',
    auto_renew: false,
    notes: '',
  });
  const [savingPackage, setSavingPackage] = useState(false);

  // Organization Licenses
  const [orgLicenses, setOrgLicenses] = useState<OrganizationLicense[]>([]);
  const [orgLicenseDialogOpen, setOrgLicenseDialogOpen] = useState(false);
  const [editingOrgLicense, setEditingOrgLicense] = useState<OrganizationLicense | null>(null);
  const [orgLicenseForm, setOrgLicenseForm] = useState<OrgLicenseFormState>({
    name: '',
    license_type: '',
    quantity: '',
    unit: '',
    monthly_cost: '',
    currency: 'EUR',
    billing_cycle: 'monthly',
    renewal_date: '',
    notes: '',
  });
  const [savingOrgLicense, setSavingOrgLicense] = useState(false);

  // -- Computed values --

  const isManual = provider?.config?.provider_type === 'manual' || provider?.name === 'manual';

  const isSeatBased = provider?.config?.license_model === 'seat_based' ||
    (provider?.config?.license_model !== 'license_based' &&
      SEAT_BASED_PROVIDERS.includes(provider?.name as typeof SEAT_BASED_PROVIDERS[number]));

  // Stats - count only ACTIVE licenses from categorized arrays
  const statsData = categorizedLicenses?.stats;
  const totalLicenses = statsData?.total_active ?? licenses.filter((l) => l.status === 'active').length;
  const assignedLicensesCount = categorizedLicenses?.assigned.filter((l) => l.status === 'active').length
    ?? licenses.filter((l) => l.status === 'active' && l.employee_id).length;
  const externalLicensesCount = categorizedLicenses?.external.filter((l) => l.status === 'active').length ?? 0;
  const notInHrisLicensesCount = categorizedLicenses?.not_in_hris?.filter((l) => l.status === 'active').length ?? 0;
  const unassignedLicensesCount = categorizedLicenses?.unassigned.filter((l) => l.status === 'active').length ?? 0;
  const maxUsers = provider?.config?.provider_license_info?.max_users;
  const availableSeats = maxUsers ? Math.max(0, maxUsers - totalLicenses) : null;
  const inactiveLicensesCount = statsData?.total_inactive ?? licenses.filter((l) => l.status !== 'active').length;
  const totalMonthlyCostValue = statsData?.monthly_cost
    ? parseFloat(String(statsData.monthly_cost))
    : licenses.filter((l) => l.status === 'active').reduce((sum, l) => sum + (parseFloat(l.monthly_cost || '0') || 0), 0);

  const stats: LicenseStats = {
    totalLicenses,
    assignedLicenses: assignedLicensesCount,
    unassignedLicenses: unassignedLicensesCount,
    notInHrisLicenses: notInHrisLicensesCount,
    externalLicenses: externalLicensesCount,
    inactiveLicenses: inactiveLicensesCount,
    totalMonthlyCost: totalMonthlyCostValue,
    availableSeats,
  };

  // -- Helper functions --

  const showToast = useCallback((type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // -- Fetch functions --

  const fetchProvider = useCallback(async () => {
    try {
      const p = await api.getProvider(providerId);
      setProvider(p);
      setSettingsForm({
        display_name: p.display_name,
        license_model: p.config?.license_model || 'license_based',
        payment_method_id: p.payment_method_id || null,
      });
    } catch (error) {
      handleSilentError('fetchProvider', error);
    }
  }, [providerId]);

  const fetchPaymentMethods = useCallback(async () => {
    try {
      const data = await api.getPaymentMethods();
      setPaymentMethods(data.items);
    } catch (error) {
      handleSilentError('fetchPaymentMethods', error);
    }
  }, []);

  const fetchPublicCredentials = useCallback(async () => {
    try {
      const data = await api.getProviderPublicCredentials(providerId);
      setPublicCredentials(data.credentials);
    } catch (error) {
      handleSilentError('fetchPublicCredentials', error);
    }
  }, [providerId]);

  const fetchLicenses = useCallback(async () => {
    try {
      const data = await api.getLicenses({ provider_id: providerId, page_size: 200 });
      setLicenses(data.items);
    } catch (error) {
      handleSilentError('fetchLicenses', error);
    }
  }, [providerId]);

  const fetchCategorizedLicenses = useCallback(async () => {
    try {
      const data = await api.getCategorizedLicenses({ provider_id: providerId });
      setCategorizedLicenses(data);
    } catch (error) {
      handleSilentError('fetchCategorizedLicenses', error);
    }
  }, [providerId]);

  const fetchEmployees = useCallback(async () => {
    try {
      const data = await api.getEmployees({ status: 'active', page_size: 200 });
      setEmployees(data.items);
    } catch (error) {
      handleSilentError('fetchEmployees', error);
    }
  }, []);

  const fetchLicenseTypes = useCallback(async (currentProvider?: Provider | null) => {
    try {
      const [typesData, pricingData] = await Promise.all([
        api.getProviderLicenseTypes(providerId),
        api.getProviderPricing(providerId),
      ]);
      setLicenseTypes([...typesData.license_types].sort((a, b) => a.license_type.localeCompare(b.license_type)));

      const edits: Record<string, PricingEditState> = {};

      for (const lt of typesData.license_types) {
        edits[lt.license_type] = {
          cost: lt.pricing?.cost || '',
          currency: lt.pricing?.currency || 'EUR',
          billing_cycle: lt.pricing?.billing_cycle || 'yearly',
          payment_frequency: lt.pricing?.payment_frequency || 'yearly',
          display_name: lt.pricing?.display_name || '',
          next_billing_date: lt.pricing?.next_billing_date || '',
          notes: lt.pricing?.notes || '',
        };
      }

      const pkgPricing = pricingData.package_pricing || currentProvider?.config?.package_pricing;
      if (pkgPricing) {
        edits['__package__'] = {
          cost: pkgPricing.cost || '',
          currency: pkgPricing.currency || 'EUR',
          billing_cycle: pkgPricing.billing_cycle || 'yearly',
          payment_frequency: 'yearly',
          display_name: '',
          next_billing_date: pkgPricing.next_billing_date || '',
          notes: pkgPricing.notes || '',
        };
      }

      setPricingEdits(edits);
    } catch (error) {
      handleSilentError('fetchLicenseTypes', error);
    }
  }, [providerId]);

  const fetchIndividualLicenseTypes = useCallback(async () => {
    try {
      const data = await api.getProviderIndividualLicenseTypes(providerId);
      setIndividualLicenseTypes([...data.license_types].sort((a, b) => a.license_type.localeCompare(b.license_type)));
      setHasCombinedTypes(data.has_combined_types);

      const edits: Record<string, Omit<PricingEditState, 'next_billing_date'>> = {};
      for (const lt of data.license_types) {
        edits[lt.license_type] = {
          cost: lt.pricing?.cost || '',
          currency: lt.pricing?.currency || 'EUR',
          billing_cycle: lt.pricing?.billing_cycle || 'yearly',
          payment_frequency: lt.pricing?.payment_frequency || 'monthly',
          display_name: lt.pricing?.display_name || lt.display_name || '',
          notes: lt.pricing?.notes || '',
        };
      }
      setIndividualPricingEdits(edits);
    } catch (error) {
      handleSilentError('fetchIndividualLicenseTypes', error);
    }
  }, [providerId]);

  const fetchFiles = useCallback(async () => {
    try {
      const data = await api.getProviderFiles(providerId);
      setFiles(data.items);
    } catch (error) {
      handleSilentError('fetchFiles', error);
    }
  }, [providerId]);

  const fetchLicensePackages = useCallback(async () => {
    try {
      const data = await api.getLicensePackages(providerId);
      setLicensePackages(data.items);
    } catch (error) {
      handleSilentError('fetchLicensePackages', error);
    }
  }, [providerId]);

  const fetchOrgLicenses = useCallback(async () => {
    try {
      const data = await api.getOrganizationLicenses(providerId);
      setOrgLicenses(data.items);
    } catch (error) {
      handleSilentError('fetchOrgLicenses', error);
    }
  }, [providerId]);

  // -- Initial data load --

  useEffect(() => {
    Promise.all([
      fetchProvider(),
      fetchPublicCredentials(),
      fetchLicenses(),
      fetchCategorizedLicenses(),
      fetchEmployees(),
      fetchLicenseTypes(),
      fetchIndividualLicenseTypes(),
      fetchFiles(),
      fetchLicensePackages(),
      fetchOrgLicenses(),
      fetchPaymentMethods(),
    ]).finally(() => setLoading(false));
  }, [
    fetchProvider,
    fetchPublicCredentials,
    fetchLicenses,
    fetchCategorizedLicenses,
    fetchEmployees,
    fetchLicenseTypes,
    fetchIndividualLicenseTypes,
    fetchFiles,
    fetchLicensePackages,
    fetchOrgLicenses,
    fetchPaymentMethods,
  ]);

  // -- Handlers --

  const handleSync = useCallback(async () => {
    if (!provider || isManual) return;
    setSyncing(true);
    try {
      const result = await api.syncProvider(provider.id);
      showToast(result.success ? 'success' : 'error', result.success ? t('syncCompleted') : t('syncFailed'));
      if (result.success) {
        await Promise.all([
          fetchProvider(),
          fetchLicenses(),
          fetchCategorizedLicenses(),
          fetchLicenseTypes(),
          fetchIndividualLicenseTypes(),
        ]);
      }
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('syncFailed'));
    } finally {
      setSyncing(false);
    }
  }, [provider, isManual, showToast, t, fetchProvider, fetchLicenses, fetchCategorizedLicenses, fetchLicenseTypes, fetchIndividualLicenseTypes]);

  const handleAddLicense = useCallback(async () => {
    if (!provider) return;
    setSavingLicense(true);
    try {
      if (addLicenseMode === 'bulk') {
        const keys = bulkKeys.split('\n').map((k) => k.trim()).filter((k) => k);
        if (keys.length === 0) {
          showToast('error', t('enterLicenseKey'));
          setSavingLicense(false);
          return;
        }
        await api.createManualLicensesBulk({
          provider_id: provider.id,
          license_type: licenseForm.license_type || undefined,
          license_keys: keys,
          monthly_cost: licenseForm.monthly_cost || provider.config?.default_cost || undefined,
          currency: provider.config?.currency || 'EUR',
          valid_until: licenseForm.valid_until || undefined,
          notes: licenseForm.notes || undefined,
        });
        showToast('success', t('licensesAdded', { count: keys.length }));
      } else {
        await api.createManualLicenses({
          provider_id: provider.id,
          license_type: licenseForm.license_type || undefined,
          license_key: addLicenseMode === 'single' ? licenseForm.license_key || undefined : undefined,
          quantity: addLicenseMode === 'seats' ? parseInt(licenseForm.quantity) : 1,
          monthly_cost: licenseForm.monthly_cost || provider.config?.default_cost || undefined,
          currency: provider.config?.currency || 'EUR',
          valid_until: licenseForm.valid_until || undefined,
          notes: licenseForm.notes || undefined,
        });
        showToast('success', addLicenseMode === 'seats' ? t('seatsAdded', { count: licenseForm.quantity }) : t('licenseAdded'));
      }
      setAddLicenseOpen(false);
      setLicenseForm({ license_type: '', license_key: '', quantity: '1', monthly_cost: '', valid_until: '', notes: '' });
      setBulkKeys('');
      await fetchLicenses();
      await fetchCategorizedLicenses();
      await fetchProvider();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToAddLicense'));
    } finally {
      setSavingLicense(false);
    }
  }, [provider, addLicenseMode, bulkKeys, licenseForm, showToast, t, fetchLicenses, fetchCategorizedLicenses, fetchProvider]);

  const handleAssign = useCallback(async () => {
    if (!assignDialog || !selectedEmployeeId) return;
    try {
      await api.assignManualLicense(assignDialog.id, selectedEmployeeId);
      showToast('success', t('licenseAssigned'));
      setAssignDialog(null);
      setSelectedEmployeeId('');
      await fetchLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToAssign'));
    }
  }, [assignDialog, selectedEmployeeId, showToast, t, fetchLicenses]);

  const handleUnassign = useCallback(async (license: License) => {
    try {
      await api.unassignManualLicense(license.id);
      showToast('success', t('licenseUnassigned'));
      await fetchLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUnassign'));
    }
  }, [showToast, t, fetchLicenses]);

  const handleDeleteLicense = useCallback(async () => {
    if (!deleteDialog) return;
    try {
      await api.deleteManualLicense(deleteDialog.id);
      showToast('success', t('licenseDeleted'));
      setDeleteDialog(null);
      await fetchLicenses();
      await fetchCategorizedLicenses();
      await fetchProvider();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToDeleteLicense'));
    }
  }, [deleteDialog, showToast, t, fetchLicenses, fetchCategorizedLicenses, fetchProvider]);

  const handleOpenServiceAccountDialog = useCallback((license: License) => {
    setServiceAccountForm({
      is_service_account: license.is_service_account || false,
      service_account_name: license.service_account_name || '',
      service_account_owner_id: license.service_account_owner_id || '',
      apply_globally: false,
    });
    setServiceAccountDialog(license);
  }, []);

  const handleSaveServiceAccount = useCallback(async () => {
    if (!serviceAccountDialog) return;
    setSavingServiceAccount(true);
    try {
      await api.updateLicenseServiceAccount(serviceAccountDialog.id, {
        is_service_account: serviceAccountForm.is_service_account,
        service_account_name: serviceAccountForm.service_account_name || undefined,
        service_account_owner_id: serviceAccountForm.service_account_owner_id || undefined,
        apply_globally: serviceAccountForm.apply_globally,
      });
      const message = serviceAccountForm.is_service_account
        ? (serviceAccountForm.apply_globally
          ? `${t('markedAsServiceAccount')} ${t('addedToGlobalPatterns')}`
          : t('markedAsServiceAccount'))
        : t('removedServiceAccountFlag');
      showToast('success', message);
      setServiceAccountDialog(null);
      await fetchCategorizedLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUpdate'));
    } finally {
      setSavingServiceAccount(false);
    }
  }, [serviceAccountDialog, serviceAccountForm, showToast, t, fetchCategorizedLicenses]);

  const handleOpenAdminAccountDialog = useCallback((license: License) => {
    setAdminAccountForm({
      is_admin_account: license.is_admin_account || false,
      admin_account_name: license.admin_account_name || '',
      admin_account_owner_id: license.admin_account_owner_id || '',
      apply_globally: false,
    });
    setAdminAccountDialog(license);
  }, []);

  const handleSaveAdminAccount = useCallback(async () => {
    if (!adminAccountDialog) return;
    setSavingAdminAccount(true);
    try {
      await api.updateLicenseAdminAccount(adminAccountDialog.id, {
        is_admin_account: adminAccountForm.is_admin_account,
        admin_account_name: adminAccountForm.admin_account_name || undefined,
        admin_account_owner_id: adminAccountForm.admin_account_owner_id || undefined,
        apply_globally: adminAccountForm.apply_globally,
      });
      const message = adminAccountForm.is_admin_account
        ? (adminAccountForm.apply_globally
          ? `${t('markedAsAdminAccount')} ${t('addedToGlobalPatterns')}`
          : t('markedAsAdminAccount'))
        : t('removedAdminAccountFlag');
      showToast('success', message);
      setAdminAccountDialog(null);
      await fetchCategorizedLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUpdate'));
    } finally {
      setSavingAdminAccount(false);
    }
  }, [adminAccountDialog, adminAccountForm, showToast, t, fetchCategorizedLicenses]);

  const handleOpenLicenseTypeDialog = useCallback((license: License) => {
    setSelectedLicenseType(license.license_type || '');
    setLicenseTypeDialog(license);
  }, []);

  const handleSaveLicenseType = useCallback(async () => {
    if (!licenseTypeDialog || !selectedLicenseType) return;
    setSavingLicenseType(true);
    try {
      await api.updateLicenseType(licenseTypeDialog.id, selectedLicenseType);
      showToast('success', tLicenses('licenseTypeUpdated'));
      setLicenseTypeDialog(null);
      await fetchCategorizedLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUpdate'));
    } finally {
      setSavingLicenseType(false);
    }
  }, [licenseTypeDialog, selectedLicenseType, showToast, t, tLicenses, fetchCategorizedLicenses]);

  const handleConfirmMatch = useCallback(async (license: License) => {
    try {
      await api.confirmLicenseMatch(license.id);
      showToast('success', tLicenses('matchConfirmed'));
      await fetchCategorizedLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUpdate'));
    }
  }, [showToast, t, tLicenses, fetchCategorizedLicenses]);

  const handleRejectMatch = useCallback(async (license: License) => {
    try {
      await api.rejectLicenseMatch(license.id);
      showToast('success', tLicenses('matchRejected'));
      await fetchCategorizedLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUpdate'));
    }
  }, [showToast, t, tLicenses, fetchCategorizedLicenses]);

  const handleSavePricing = useCallback(async () => {
    if (!provider) return;
    setSavingPricing(true);
    try {
      const pricing: LicenseTypePricing[] = [];
      let packagePricing: PackagePricing | null = null;

      for (const [licenseType, edit] of Object.entries(pricingEdits)) {
        if (licenseType === '__package__') {
          if (edit.cost) {
            packagePricing = {
              cost: edit.cost,
              currency: edit.currency,
              billing_cycle: edit.billing_cycle,
              next_billing_date: edit.next_billing_date || undefined,
              notes: edit.notes || undefined,
            };
          }
          continue;
        }

        if (edit.cost) {
          pricing.push({
            license_type: licenseType,
            display_name: edit.display_name || undefined,
            cost: edit.cost,
            currency: edit.currency,
            billing_cycle: edit.billing_cycle,
            payment_frequency: edit.payment_frequency,
            next_billing_date: edit.next_billing_date || undefined,
            notes: edit.notes || undefined,
          });
        }
      }
      await api.updateProviderPricing(provider.id, pricing, packagePricing);
      const updatedProvider = await api.getProvider(provider.id);
      setProvider(updatedProvider);
      await fetchLicenseTypes(updatedProvider);
      await fetchLicenses();
      await fetchCategorizedLicenses();
      showToast('success', t('pricingSavedApplied'));
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToSavePricing'));
    } finally {
      setSavingPricing(false);
    }
  }, [provider, pricingEdits, showToast, t, fetchLicenseTypes, fetchLicenses, fetchCategorizedLicenses]);

  const handleSaveIndividualPricing = useCallback(async () => {
    if (!provider) return;
    setSavingIndividualPricing(true);
    try {
      const pricing: LicenseTypePricing[] = [];

      for (const [licenseType, edit] of Object.entries(individualPricingEdits)) {
        pricing.push({
          license_type: licenseType,
          display_name: edit.display_name || undefined,
          cost: edit.cost || '0',
          currency: edit.currency,
          billing_cycle: edit.billing_cycle,
          payment_frequency: edit.payment_frequency,
          notes: edit.notes || undefined,
        });
      }

      const result = await api.updateProviderIndividualPricing(provider.id, pricing);
      setIndividualLicenseTypes(result.license_types);

      await fetchLicenses();
      await fetchCategorizedLicenses();
      await fetchLicenseTypes();
      showToast('success', t('individualPricingSaved'));
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToSavePricing'));
    } finally {
      setSavingIndividualPricing(false);
    }
  }, [provider, individualPricingEdits, showToast, t, fetchLicenses, fetchCategorizedLicenses, fetchLicenseTypes]);

  const handleSaveSettings = useCallback(async () => {
    if (!provider) return;
    setSavingSettings(true);
    try {
      const config = {
        ...(provider.config || {}),
        provider_type: isManual ? 'manual' : 'api',
        license_model: settingsForm.license_model,
      };
      await api.updateProvider(provider.id, {
        display_name: settingsForm.display_name,
        config,
        payment_method_id: settingsForm.payment_method_id || null,
      });
      await fetchProvider();
      showToast('success', t('settingsSaved'));
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUpdate'));
    } finally {
      setSavingSettings(false);
    }
  }, [provider, isManual, settingsForm, showToast, t, fetchProvider]);

  const handleSaveCredentials = useCallback(async () => {
    if (!provider) return;

    const credentials: Record<string, string> = {};
    for (const [key, value] of Object.entries(credentialsForm)) {
      if (value && value.trim()) {
        credentials[key] = value.trim();
      }
    }

    if (Object.keys(credentials).length === 0) {
      showToast('error', t('enterAtLeastOneCredential'));
      return;
    }

    setSavingCredentials(true);
    try {
      await api.updateProvider(provider.id, { credentials });
      await fetchProvider();
      setCredentialsForm({});
      setShowCredentialsEdit(false);
      showToast('success', t('credentialsSaved'));
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToUpdate'));
    } finally {
      setSavingCredentials(false);
    }
  }, [provider, credentialsForm, showToast, t, fetchProvider]);

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !provider) return;

    setUploadingFile(true);
    try {
      await api.uploadProviderFile(provider.id, file, fileDescription || undefined, fileCategory);
      await fetchFiles();
      setFileDescription('');
      setFileCategory('other');
      showToast('success', t('fileUploaded'));
      e.target.value = '';
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('uploadFailed'));
    } finally {
      setUploadingFile(false);
    }
  }, [provider, fileDescription, fileCategory, showToast, t, fetchFiles]);

  const handleDeleteFile = useCallback(async (fileId: string) => {
    if (!provider) return;
    try {
      await api.deleteProviderFile(provider.id, fileId);
      await fetchFiles();
      showToast('success', t('fileDeleted'));
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('deleteFailed'));
    }
  }, [provider, showToast, t, fetchFiles]);

  const [deleteProviderOpen, setDeleteProviderOpen] = useState(false);

  const handleDeleteProvider = useCallback(() => {
    if (!provider) return;
    api.deleteProvider(provider.id)
      .then(() => {
        showToast('success', t('providerDeleted'));
        router.push('/providers');
      })
      .catch(() => showToast('error', t('deleteProviderFailed')));
  }, [provider, router, showToast, t]);

  // License Package handlers
  const handleOpenPackageDialog = useCallback((pkg?: LicensePackage) => {
    if (pkg) {
      setEditingPackage(pkg);
      setPackageForm({
        license_type: pkg.license_type,
        display_name: pkg.display_name || '',
        total_seats: String(pkg.total_seats),
        cost_per_seat: pkg.cost_per_seat || '',
        currency: pkg.currency,
        billing_cycle: pkg.billing_cycle || 'monthly',
        contract_start: pkg.contract_start || '',
        contract_end: pkg.contract_end || '',
        auto_renew: pkg.auto_renew,
        notes: pkg.notes || '',
      });
    } else {
      setEditingPackage(null);
      setPackageForm({
        license_type: '',
        display_name: '',
        total_seats: '',
        cost_per_seat: '',
        currency: 'EUR',
        billing_cycle: 'monthly',
        contract_start: '',
        contract_end: '',
        auto_renew: false,
        notes: '',
      });
    }
    setPackageDialogOpen(true);
  }, []);

  const handleSavePackage = useCallback(async () => {
    if (!packageForm.license_type || !packageForm.total_seats) {
      showToast('error', t('licenseTypeRequired'));
      return;
    }
    setSavingPackage(true);
    try {
      const data = {
        license_type: packageForm.license_type,
        display_name: packageForm.display_name || undefined,
        total_seats: parseInt(packageForm.total_seats),
        cost_per_seat: packageForm.cost_per_seat || undefined,
        currency: packageForm.currency,
        billing_cycle: packageForm.billing_cycle || undefined,
        contract_start: packageForm.contract_start || undefined,
        contract_end: packageForm.contract_end || undefined,
        auto_renew: packageForm.auto_renew,
        notes: packageForm.notes || undefined,
      };

      if (editingPackage) {
        await api.updateLicensePackage(providerId, editingPackage.id, data);
        showToast('success', t('packageUpdated'));
      } else {
        await api.createLicensePackage(providerId, data);
        showToast('success', t('packageCreated'));
      }
      setPackageDialogOpen(false);
      await fetchLicensePackages();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToSavePackage'));
    } finally {
      setSavingPackage(false);
    }
  }, [packageForm, editingPackage, providerId, showToast, t, fetchLicensePackages]);

  const handleDeletePackage = useCallback(async (pkg: LicensePackage) => {
    if (!confirm(`${tCommon('confirmDelete')}`)) return;
    try {
      await api.deleteLicensePackage(providerId, pkg.id);
      showToast('success', t('packageDeleted'));
      await fetchLicensePackages();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToDeletePackage'));
    }
  }, [providerId, showToast, t, tCommon, fetchLicensePackages]);

  // Organization License handlers
  const handleOpenOrgLicenseDialog = useCallback((lic?: OrganizationLicense) => {
    if (lic) {
      setEditingOrgLicense(lic);
      setOrgLicenseForm({
        name: lic.name,
        license_type: lic.license_type || '',
        quantity: lic.quantity ? String(lic.quantity) : '',
        unit: lic.unit || '',
        monthly_cost: lic.monthly_cost || '',
        currency: lic.currency,
        billing_cycle: lic.billing_cycle || 'monthly',
        renewal_date: lic.renewal_date || '',
        notes: lic.notes || '',
      });
    } else {
      setEditingOrgLicense(null);
      setOrgLicenseForm({
        name: '',
        license_type: '',
        quantity: '',
        unit: '',
        monthly_cost: '',
        currency: 'EUR',
        billing_cycle: 'monthly',
        renewal_date: '',
        notes: '',
      });
    }
    setOrgLicenseDialogOpen(true);
  }, []);

  const handleSaveOrgLicense = useCallback(async () => {
    if (!orgLicenseForm.name) {
      showToast('error', t('nameRequired'));
      return;
    }
    setSavingOrgLicense(true);
    try {
      const data = {
        name: orgLicenseForm.name,
        license_type: orgLicenseForm.license_type || undefined,
        quantity: orgLicenseForm.quantity ? parseInt(orgLicenseForm.quantity) : undefined,
        unit: orgLicenseForm.unit || undefined,
        monthly_cost: orgLicenseForm.monthly_cost || undefined,
        currency: orgLicenseForm.currency,
        billing_cycle: orgLicenseForm.billing_cycle || undefined,
        renewal_date: orgLicenseForm.renewal_date || undefined,
        notes: orgLicenseForm.notes || undefined,
      };

      if (editingOrgLicense) {
        await api.updateOrganizationLicense(providerId, editingOrgLicense.id, data);
        showToast('success', t('orgLicenseUpdated'));
      } else {
        await api.createOrganizationLicense(providerId, data);
        showToast('success', t('orgLicenseCreated'));
      }
      setOrgLicenseDialogOpen(false);
      await fetchOrgLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToSaveOrgLicense'));
    } finally {
      setSavingOrgLicense(false);
    }
  }, [orgLicenseForm, editingOrgLicense, providerId, showToast, t, fetchOrgLicenses]);

  const handleDeleteOrgLicense = useCallback(async (lic: OrganizationLicense) => {
    if (!confirm(`${tCommon('confirmDelete')}`)) return;
    try {
      await api.deleteOrganizationLicense(providerId, lic.id);
      showToast('success', t('orgLicenseDeleted'));
      await fetchOrgLicenses();
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : t('failedToDeleteLicense'));
    }
  }, [providerId, showToast, t, tCommon, fetchOrgLicenses]);

  return {
    // Core data
    provider,
    licenses,
    categorizedLicenses,
    employees,
    loading,

    // Computed values
    isManual,
    isSeatBased,
    stats,

    // Tab state
    activeTab,
    setActiveTab,

    // Toast
    toast,
    showToast,

    // Sync
    syncing,
    handleSync,

    // Import dialog
    importDialogOpen,
    setImportDialogOpen,

    // Add License
    addLicenseOpen,
    setAddLicenseOpen,
    addLicenseMode,
    setAddLicenseMode,
    licenseForm,
    setLicenseForm,
    bulkKeys,
    setBulkKeys,
    savingLicense,
    handleAddLicense,

    // Assign
    assignDialog,
    setAssignDialog,
    selectedEmployeeId,
    setSelectedEmployeeId,
    handleAssign,
    handleUnassign,

    // Delete
    deleteDialog,
    setDeleteDialog,
    handleDeleteLicense,

    // Service Account
    serviceAccountDialog,
    serviceAccountForm,
    setServiceAccountForm,
    savingServiceAccount,
    handleOpenServiceAccountDialog,
    handleSaveServiceAccount,
    setServiceAccountDialog,

    // Admin Account
    adminAccountDialog,
    adminAccountForm,
    setAdminAccountForm,
    savingAdminAccount,
    handleOpenAdminAccountDialog,
    handleSaveAdminAccount,
    setAdminAccountDialog,

    // License Type
    licenseTypeDialog,
    selectedLicenseType,
    setSelectedLicenseType,
    savingLicenseType,
    handleOpenLicenseTypeDialog,
    handleSaveLicenseType,
    setLicenseTypeDialog,

    // Match suggestions
    handleConfirmMatch,
    handleRejectMatch,

    // Settings
    settingsForm,
    setSettingsForm,
    savingSettings,
    handleSaveSettings,
    paymentMethods,

    // Credentials
    credentialsForm,
    setCredentialsForm,
    savingCredentials,
    showCredentialsEdit,
    setShowCredentialsEdit,
    publicCredentials,
    handleSaveCredentials,

    // Delete Provider
    deleteProviderOpen,
    setDeleteProviderOpen,
    handleDeleteProvider,

    // Pricing
    licenseTypes,
    pricingEdits,
    setPricingEdits,
    savingPricing,
    handleSavePricing,

    // Individual pricing
    individualLicenseTypes,
    hasCombinedTypes,
    individualPricingEdits,
    setIndividualPricingEdits,
    savingIndividualPricing,
    handleSaveIndividualPricing,

    // Files
    files,
    uploadingFile,
    fileDescription,
    setFileDescription,
    fileCategory,
    setFileCategory,
    handleFileUpload,
    handleDeleteFile,

    // License Packages
    licensePackages,
    packageDialogOpen,
    setPackageDialogOpen,
    editingPackage,
    packageForm,
    setPackageForm,
    savingPackage,
    handleOpenPackageDialog,
    handleSavePackage,
    handleDeletePackage,

    // Organization Licenses
    orgLicenses,
    orgLicenseDialogOpen,
    setOrgLicenseDialogOpen,
    editingOrgLicense,
    orgLicenseForm,
    setOrgLicenseForm,
    savingOrgLicense,
    handleOpenOrgLicenseDialog,
    handleSaveOrgLicense,
    handleDeleteOrgLicense,

    // Fetch functions
    fetchLicenses,
    fetchCategorizedLicenses,
  };
}
