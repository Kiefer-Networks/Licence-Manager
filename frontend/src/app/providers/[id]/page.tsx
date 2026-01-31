'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/app-layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { api, Provider, License, Employee, LicenseTypeInfo, LicenseTypePricing, PackagePricing, ProviderFile, CategorizedLicensesResponse, IndividualLicenseTypeInfo } from '@/lib/api';
import { ThreeTableLayout } from '@/components/licenses';
import { formatMonthlyCost } from '@/lib/format';
import { handleSilentError } from '@/lib/error-handler';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { CopyButton, CopyableText } from '@/components/ui/copy-button';
import {
  ArrowLeft,
  Key,
  Package,
  Settings,
  RefreshCw,
  Plus,
  Trash2,
  UserPlus,
  UserMinus,
  Loader2,
  CheckCircle2,
  XCircle,
  Calendar,
  DollarSign,
  Users,
  Clock,
  AlertTriangle,
  Skull,
  Globe,
  Upload,
  Download,
  FileText,
  File,
  Eye,
  Bot,
  Building2,
  ShieldCheck,
} from 'lucide-react';
import Link from 'next/link';

const licenseModelOptions = [
  { value: 'seat_based', label: 'Seat-based (per user)' },
  { value: 'license_based', label: 'License-based (transferable)' },
];

type Tab = 'overview' | 'licenses' | 'pricing' | 'files' | 'settings';

export default function ProviderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const providerId = params.id as string;

  const [provider, setProvider] = useState<Provider | null>(null);
  const [licenses, setLicenses] = useState<License[]>([]);
  const [categorizedLicenses, setCategorizedLicenses] = useState<CategorizedLicensesResponse | null>(null);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [syncing, setSyncing] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Add License Dialog
  const [addLicenseOpen, setAddLicenseOpen] = useState(false);
  const [addLicenseMode, setAddLicenseMode] = useState<'single' | 'bulk' | 'seats'>('single');
  const [licenseForm, setLicenseForm] = useState({
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
  const [settingsForm, setSettingsForm] = useState({
    display_name: '',
    license_model: 'license_based',
  });
  const [savingSettings, setSavingSettings] = useState(false);

  // Delete Dialog
  const [deleteDialog, setDeleteDialog] = useState<License | null>(null);

  // Service Account Dialog
  const [serviceAccountDialog, setServiceAccountDialog] = useState<License | null>(null);
  const [serviceAccountForm, setServiceAccountForm] = useState({
    is_service_account: false,
    service_account_name: '',
    service_account_owner_id: '',
    apply_globally: false,
  });
  const [savingServiceAccount, setSavingServiceAccount] = useState(false);

  // Admin Account Dialog
  const [adminAccountDialog, setAdminAccountDialog] = useState<License | null>(null);
  const [adminAccountForm, setAdminAccountForm] = useState({
    is_admin_account: false,
    admin_account_name: '',
    admin_account_owner_id: '',
    apply_globally: false,
  });
  const [savingAdminAccount, setSavingAdminAccount] = useState(false);

  // Pricing
  const [licenseTypes, setLicenseTypes] = useState<LicenseTypeInfo[]>([]);
  const [pricingEdits, setPricingEdits] = useState<Record<string, {
    cost: string;
    currency: string;
    billing_cycle: string;
    payment_frequency: string;
    display_name: string;
    next_billing_date: string;
    notes: string;
  }>>({});
  const [savingPricing, setSavingPricing] = useState(false);

  // Individual pricing (for Microsoft/Azure with combined license types)
  const [individualLicenseTypes, setIndividualLicenseTypes] = useState<IndividualLicenseTypeInfo[]>([]);
  const [hasCombinedTypes, setHasCombinedTypes] = useState(false);
  const [individualPricingEdits, setIndividualPricingEdits] = useState<Record<string, {
    cost: string;
    currency: string;
    billing_cycle: string;
    payment_frequency: string;
    display_name: string;
    notes: string;
  }>>({});
  const [savingIndividualPricing, setSavingIndividualPricing] = useState(false);

  // Files
  const [files, setFiles] = useState<ProviderFile[]>([]);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [fileDescription, setFileDescription] = useState('');
  const [fileCategory, setFileCategory] = useState('other');

  // License Packages
  const [licensePackages, setLicensePackages] = useState<import('@/lib/api').LicensePackage[]>([]);
  const [packageDialogOpen, setPackageDialogOpen] = useState(false);
  const [editingPackage, setEditingPackage] = useState<import('@/lib/api').LicensePackage | null>(null);
  const [packageForm, setPackageForm] = useState({
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
  const [orgLicenses, setOrgLicenses] = useState<import('@/lib/api').OrganizationLicense[]>([]);
  const [orgLicenseDialogOpen, setOrgLicenseDialogOpen] = useState(false);
  const [editingOrgLicense, setEditingOrgLicense] = useState<import('@/lib/api').OrganizationLicense | null>(null);
  const [orgLicenseForm, setOrgLicenseForm] = useState({
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

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  };

  const isManual = provider?.config?.provider_type === 'manual' || provider?.name === 'manual';

  // Providers where licenses are tied to users (seat-based) vs transferable (license-based)
  // Seat-based: user IS the license holder, can only activate/deactivate
  // License-based: licenses can be reassigned to different users
  const SEAT_BASED_PROVIDERS = ['slack', 'cursor', 'google_workspace', 'microsoft', 'figma', 'miro', 'github', 'gitlab', 'mattermost', 'openai', '1password'];
  const isSeatBased = provider?.config?.license_model === 'seat_based' ||
    (provider?.config?.license_model !== 'license_based' && SEAT_BASED_PROVIDERS.includes(provider?.name || ''));

  const fetchProvider = useCallback(async () => {
    try {
      const p = await api.getProvider(providerId);
      setProvider(p);
      setSettingsForm({
        display_name: p.display_name,
        license_model: p.config?.license_model || 'license_based',
      });
    } catch (error) {
      handleSilentError('fetchProvider', error);
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
      setLicenseTypes(typesData.license_types);

      // Initialize pricing edits with current values
      const edits: Record<string, { cost: string; currency: string; billing_cycle: string; payment_frequency: string; display_name: string; next_billing_date: string; notes: string }> = {};

      // Initialize license type pricing
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

      // Initialize package pricing - check API response first, then provider config as fallback
      const pkgPricing = pricingData.package_pricing || currentProvider?.config?.package_pricing;
      if (pkgPricing) {
        edits['__package__'] = {
          cost: pkgPricing.cost || '',
          currency: pkgPricing.currency || 'EUR',
          billing_cycle: pkgPricing.billing_cycle || 'yearly',
          payment_frequency: 'yearly', // Not used for package pricing
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
      setIndividualLicenseTypes(data.license_types);
      setHasCombinedTypes(data.has_combined_types);

      // Initialize individual pricing edits
      const edits: Record<string, { cost: string; currency: string; billing_cycle: string; payment_frequency: string; display_name: string; notes: string }> = {};
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

  useEffect(() => {
    Promise.all([fetchProvider(), fetchLicenses(), fetchCategorizedLicenses(), fetchEmployees(), fetchLicenseTypes(), fetchIndividualLicenseTypes(), fetchFiles(), fetchLicensePackages(), fetchOrgLicenses()]).finally(() =>
      setLoading(false)
    );
  }, [fetchProvider, fetchLicenses, fetchCategorizedLicenses, fetchEmployees, fetchLicenseTypes, fetchIndividualLicenseTypes, fetchFiles, fetchLicensePackages, fetchOrgLicenses]);

  const handleSync = async () => {
    if (!provider || isManual) return;
    setSyncing(true);
    try {
      const result = await api.syncProvider(provider.id);
      await fetchProvider();
      await fetchLicenses();
      showToast(result.success ? 'success' : 'error', result.success ? 'Sync completed' : 'Sync failed');
    } catch (error: any) {
      showToast('error', error.message || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const handleAddLicense = async () => {
    if (!provider) return;
    setSavingLicense(true);
    try {
      if (addLicenseMode === 'bulk') {
        const keys = bulkKeys.split('\n').map((k) => k.trim()).filter((k) => k);
        if (keys.length === 0) {
          showToast('error', 'Please enter at least one license key');
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
        showToast('success', `${keys.length} licenses added`);
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
        showToast('success', addLicenseMode === 'seats' ? `${licenseForm.quantity} seats added` : 'License added');
      }
      setAddLicenseOpen(false);
      setLicenseForm({ license_type: '', license_key: '', quantity: '1', monthly_cost: '', valid_until: '', notes: '' });
      setBulkKeys('');
      await fetchLicenses();
      await fetchCategorizedLicenses();
      await fetchProvider();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to add license');
    } finally {
      setSavingLicense(false);
    }
  };

  const handleAssign = async () => {
    if (!assignDialog || !selectedEmployeeId) return;
    try {
      await api.assignManualLicense(assignDialog.id, selectedEmployeeId);
      showToast('success', 'License assigned');
      setAssignDialog(null);
      setSelectedEmployeeId('');
      await fetchLicenses();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to assign');
    }
  };

  const handleUnassign = async (license: License) => {
    try {
      await api.unassignManualLicense(license.id);
      showToast('success', 'License unassigned');
      await fetchLicenses();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to unassign');
    }
  };

  const handleDeleteLicense = async () => {
    if (!deleteDialog) return;
    try {
      await api.deleteManualLicense(deleteDialog.id);
      showToast('success', 'License deleted');
      setDeleteDialog(null);
      await fetchLicenses();
      await fetchCategorizedLicenses();
      await fetchProvider();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to delete');
    }
  };

  const handleOpenServiceAccountDialog = (license: License) => {
    setServiceAccountForm({
      is_service_account: license.is_service_account || false,
      service_account_name: license.service_account_name || '',
      service_account_owner_id: license.service_account_owner_id || '',
      apply_globally: false,  // Always start unchecked
    });
    setServiceAccountDialog(license);
  };

  const handleSaveServiceAccount = async () => {
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
          ? 'Marked as service account and added to global patterns'
          : 'Marked as service account')
        : 'Removed service account flag';
      showToast('success', message);
      setServiceAccountDialog(null);
      await fetchCategorizedLicenses();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to update');
    } finally {
      setSavingServiceAccount(false);
    }
  };

  const handleOpenAdminAccountDialog = (license: License) => {
    setAdminAccountForm({
      is_admin_account: license.is_admin_account || false,
      admin_account_name: license.admin_account_name || '',
      admin_account_owner_id: license.admin_account_owner_id || '',
      apply_globally: false,  // Always start unchecked
    });
    setAdminAccountDialog(license);
  };

  const handleSaveAdminAccount = async () => {
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
          ? 'Marked as admin account and added to global patterns'
          : 'Marked as admin account')
        : 'Removed admin account flag';
      showToast('success', message);
      setAdminAccountDialog(null);
      await fetchCategorizedLicenses();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to update');
    } finally {
      setSavingAdminAccount(false);
    }
  };

  // License Package handlers
  const handleOpenPackageDialog = (pkg?: import('@/lib/api').LicensePackage) => {
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
  };

  const handleSavePackage = async () => {
    if (!packageForm.license_type || !packageForm.total_seats) {
      showToast('error', 'License type and total seats are required');
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
        showToast('success', 'Package updated');
      } else {
        await api.createLicensePackage(providerId, data);
        showToast('success', 'Package created');
      }
      setPackageDialogOpen(false);
      await fetchLicensePackages();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to save package');
    } finally {
      setSavingPackage(false);
    }
  };

  const handleDeletePackage = async (pkg: import('@/lib/api').LicensePackage) => {
    if (!confirm(`Delete package "${pkg.display_name || pkg.license_type}"?`)) return;
    try {
      await api.deleteLicensePackage(providerId, pkg.id);
      showToast('success', 'Package deleted');
      await fetchLicensePackages();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to delete package');
    }
  };

  // Organization License handlers
  const handleOpenOrgLicenseDialog = (lic?: import('@/lib/api').OrganizationLicense) => {
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
  };

  const handleSaveOrgLicense = async () => {
    if (!orgLicenseForm.name) {
      showToast('error', 'Name is required');
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
        showToast('success', 'Organization license updated');
      } else {
        await api.createOrganizationLicense(providerId, data);
        showToast('success', 'Organization license created');
      }
      setOrgLicenseDialogOpen(false);
      await fetchOrgLicenses();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to save organization license');
    } finally {
      setSavingOrgLicense(false);
    }
  };

  const handleDeleteOrgLicense = async (lic: import('@/lib/api').OrganizationLicense) => {
    if (!confirm(`Delete "${lic.name}"?`)) return;
    try {
      await api.deleteOrganizationLicense(providerId, lic.id);
      showToast('success', 'Organization license deleted');
      await fetchOrgLicenses();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to delete');
    }
  };

  const handleSavePricing = async () => {
    if (!provider) return;
    setSavingPricing(true);
    try {
      const pricing: LicenseTypePricing[] = [];
      let packagePricing: PackagePricing | null = null;

      for (const [licenseType, edit] of Object.entries(pricingEdits)) {
        // Handle package pricing separately
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
      // Fetch provider first to get updated config, then pass to fetchLicenseTypes
      const updatedProvider = await api.getProvider(provider.id);
      setProvider(updatedProvider);
      await fetchLicenseTypes(updatedProvider);
      await fetchLicenses();
      await fetchCategorizedLicenses();
      showToast('success', 'Pricing saved and applied to licenses');
    } catch (error: any) {
      showToast('error', error.message || 'Failed to save pricing');
    } finally {
      setSavingPricing(false);
    }
  };

  const handleSaveIndividualPricing = async () => {
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

      // Refresh license data to show updated costs
      await fetchLicenses();
      await fetchCategorizedLicenses();
      await fetchLicenseTypes();
      showToast('success', 'Individual pricing saved and applied to licenses');
    } catch (error: any) {
      showToast('error', error.message || 'Failed to save individual pricing');
    } finally {
      setSavingIndividualPricing(false);
    }
  };

  const handleSaveSettings = async () => {
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
      });
      await fetchProvider();
      showToast('success', 'Settings saved');
    } catch (error: any) {
      showToast('error', error.message || 'Failed to save');
    } finally {
      setSavingSettings(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !provider) return;

    setUploadingFile(true);
    try {
      await api.uploadProviderFile(provider.id, file, fileDescription || undefined, fileCategory);
      await fetchFiles();
      setFileDescription('');
      setFileCategory('other');
      showToast('success', 'File uploaded');
      // Reset file input
      e.target.value = '';
    } catch (error: any) {
      showToast('error', error.message || 'Upload failed');
    } finally {
      setUploadingFile(false);
    }
  };

  const handleDeleteFile = async (fileId: string) => {
    if (!provider) return;
    try {
      await api.deleteProviderFile(provider.id, fileId);
      await fetchFiles();
      showToast('success', 'File deleted');
    } catch (error: any) {
      showToast('error', error.message || 'Delete failed');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Stats - count only ACTIVE licenses from categorized arrays
  const stats = categorizedLicenses?.stats;
  const totalLicenses = stats?.total_active ?? licenses.filter((l) => l.status === 'active').length;
  // Count only ACTIVE assigned (internal) - stats.total_assigned includes inactive
  const assignedLicenses = categorizedLicenses?.assigned.filter((l) => l.status === 'active').length
    ?? licenses.filter((l) => l.status === 'active' && l.employee_id).length;
  // Count only ACTIVE external licenses
  const externalLicenses = categorizedLicenses?.external.filter((l) => l.status === 'active').length ?? 0;
  // "Not in HRIS" = active internal licenses without employee match (CRITICAL for seat-based providers!)
  const notInHrisLicenses = categorizedLicenses?.unassigned.filter((l) => l.status === 'active').length ?? 0;
  // For package providers: available = max_users - active_users (unused seats)
  // For other providers: this is the same as notInHrisLicenses
  const maxUsers = provider?.config?.provider_license_info?.max_users;
  const availableSeats = maxUsers ? Math.max(0, maxUsers - totalLicenses) : null;
  const inactiveLicenses = stats?.total_inactive ?? licenses.filter((l) => l.status !== 'active').length;
  const totalMonthlyCost = stats?.monthly_cost ? parseFloat(String(stats.monthly_cost)) : licenses.filter((l) => l.status === 'active').reduce((sum, l) => sum + (parseFloat(l.monthly_cost || '0') || 0), 0);

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
        </div>
      </AppLayout>
    );
  }

  if (!provider) {
    return (
      <AppLayout>
        <div className="max-w-4xl mx-auto py-12 text-center">
          <p className="text-muted-foreground">Provider not found</p>
          <Link href="/settings">
            <Button variant="outline" className="mt-4">Back to Settings</Button>
          </Link>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Toast */}
        {toast && (
          <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'success' ? 'bg-zinc-900 text-white' : 'bg-red-600 text-white'
          }`}>
            {toast.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            {toast.text}
          </div>
        )}

        {/* Breadcrumbs */}
        <Breadcrumbs
          items={[
            { label: 'Providers', href: '/providers' },
            { label: provider.display_name },
          ]}
          className="pt-2"
        />

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
              {provider.logo_url ? (
                <img
                  src={provider.logo_url}
                  alt={provider.display_name}
                  className="h-10 w-10 rounded-lg object-contain bg-white border"
                  onError={(e) => {
                    // Fallback to icon if logo fails to load
                    e.currentTarget.style.display = 'none';
                    e.currentTarget.nextElementSibling?.classList.remove('hidden');
                  }}
                />
              ) : null}
              <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${isManual ? 'bg-purple-50' : 'bg-zinc-100'} ${provider.logo_url ? 'hidden' : ''}`}>
                {isManual ? <Package className="h-5 w-5 text-purple-600" /> : <Key className="h-5 w-5 text-zinc-600" />}
              </div>
              <div>
                <h1 className="text-xl font-semibold">{provider.display_name}</h1>
                <div className="flex items-center gap-2 mt-0.5">
                  <Badge variant="secondary" className={isManual ? 'bg-purple-50 text-purple-700 border-0' : 'bg-emerald-50 text-emerald-700 border-0'}>
                    {isManual ? 'Manual' : 'API'}
                  </Badge>
                  {provider.config?.billing_cycle && (
                    <span className="text-xs text-muted-foreground">{provider.config.billing_cycle}</span>
                  )}
                </div>
              </div>
            </div>
          <div className="flex items-center gap-2">
            {!isManual && (
              <Button variant="outline" size="sm" onClick={handleSync} disabled={syncing}>
                <RefreshCw className={`h-4 w-4 mr-1.5 ${syncing ? 'animate-spin' : ''}`} />
                Sync
              </Button>
            )}
            {isManual && (
              <Button size="sm" onClick={() => { setAddLicenseOpen(true); setAddLicenseMode('single'); }}>
                <Plus className="h-4 w-4 mr-1.5" />
                Add License
              </Button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <nav className="flex gap-6">
            {(['overview', 'licenses', 'pricing', 'files', 'settings'] as Tab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-zinc-900 text-zinc-900'
                    : 'border-transparent text-muted-foreground hover:text-zinc-900'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats */}
            {(() => {
              // Determine billing cycle from package pricing or license pricing
              const packagePricing = provider.config?.package_pricing;
              const licensePricing = provider.config?.license_pricing || {};
              const firstPricing = Object.values(licensePricing)[0] as { billing_cycle?: string } | undefined;
              const billingCycle = packagePricing?.billing_cycle || firstPricing?.billing_cycle || 'monthly';
              const isYearly = billingCycle === 'yearly';
              const costLabel = isYearly ? 'Yearly Cost' : 'Monthly Cost';
              const displayCost = isYearly ? totalMonthlyCost * 12 : totalMonthlyCost;

              return (
                <div className={`grid grid-cols-2 ${availableSeats !== null ? 'lg:grid-cols-5' : 'lg:grid-cols-4'} gap-4`}>
                  <Card>
                    <CardContent className="pt-5 pb-4">
                      <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <Key className="h-4 w-4" />
                        <span className="text-xs font-medium uppercase">Active</span>
                      </div>
                      <p className="text-2xl font-semibold">{totalLicenses}</p>
                    </CardContent>
                  </Card>
                  <Card className={notInHrisLicenses > 0 ? 'border-red-200 bg-red-50/30' : ''}>
                    <CardContent className="pt-5 pb-4">
                      <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <Users className="h-4 w-4" />
                        <span className="text-xs font-medium uppercase">Assigned</span>
                      </div>
                      <div className="flex items-baseline gap-1 flex-wrap">
                        <span className="text-2xl font-semibold">{assignedLicenses}</span>
                        {externalLicenses > 0 && (
                          <span className="text-sm text-muted-foreground">+ {externalLicenses} <span className="text-xs">(ext)</span></span>
                        )}
                        {notInHrisLicenses > 0 && (
                          <span className="text-sm text-red-600 font-medium">+ {notInHrisLicenses} <span className="text-xs">(⚠ not in HRIS)</span></span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                  {availableSeats !== null && (
                    <Card>
                      <CardContent className="pt-5 pb-4">
                        <div className="flex items-center gap-2 text-muted-foreground mb-1">
                          <Package className="h-4 w-4" />
                          <span className="text-xs font-medium uppercase">Available</span>
                        </div>
                        <p className="text-2xl font-semibold text-emerald-600">{availableSeats}</p>
                      </CardContent>
                    </Card>
                  )}
                  <Card>
                    <CardContent className="pt-5 pb-4">
                      <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <UserMinus className="h-4 w-4" />
                        <span className="text-xs font-medium uppercase">Inactive</span>
                      </div>
                      <p className="text-2xl font-semibold text-zinc-400">{inactiveLicenses}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-5 pb-4">
                      <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <DollarSign className="h-4 w-4" />
                        <span className="text-xs font-medium uppercase">{costLabel}</span>
                      </div>
                      <p className="text-xl font-semibold">
                        {provider.config?.currency || 'EUR'} {displayCost.toFixed(2)}
                      </p>
                    </CardContent>
                  </Card>
                </div>
              );
            })()}

            {/* Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Provider Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Type</span>
                  <span>{isManual ? 'Manual Entry' : 'API Integration'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">License Model</span>
                  <span>{isSeatBased ? 'Seat-based' : 'License-based'}</span>
                </div>
                {(() => {
                  // Get billing info from license_pricing config
                  const licensePricing = provider.config?.license_pricing || {};
                  const pricingEntries = Object.values(licensePricing) as Array<{ billing_cycle?: string; cost?: string; currency?: string }>;
                  const firstPricing = pricingEntries[0];
                  const billingCycle = provider.config?.billing_cycle || firstPricing?.billing_cycle;

                  // Calculate total monthly cost from pricing config
                  let configuredMonthlyCost = 0;
                  for (const pricing of pricingEntries) {
                    if (pricing.cost) {
                      const cost = parseFloat(pricing.cost);
                      if (pricing.billing_cycle === 'yearly') {
                        configuredMonthlyCost += cost / 12;
                      } else if (pricing.billing_cycle === 'monthly') {
                        configuredMonthlyCost += cost;
                      }
                    }
                  }

                  return (
                    <>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Billing Cycle</span>
                        <span className="capitalize">{billingCycle || 'Not set'}</span>
                      </div>
                      {firstPricing?.cost && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Cost per License</span>
                          <span>{firstPricing.currency || 'EUR'} {firstPricing.cost}/{firstPricing.billing_cycle === 'yearly' ? 'year' : 'month'}</span>
                        </div>
                      )}
                    </>
                  );
                })()}
                {!isManual && provider.last_sync_at && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Sync</span>
                    <span>{new Date(provider.last_sync_at).toLocaleString('de-DE')}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Provider License Info (from API) */}
            {provider.config?.provider_license_info && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Key className="h-4 w-4" />
                    Provider License
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  {(() => {
                    const licenseInfo = provider.config.provider_license_info;
                    const expiresAt = licenseInfo.expires_at ? new Date(licenseInfo.expires_at) : null;
                    const isExpiringSoon = expiresAt && (expiresAt.getTime() - Date.now()) < 30 * 24 * 60 * 60 * 1000;
                    const usedSeats = totalLicenses;
                    const maxSeats = licenseInfo.max_users || 0;
                    const availableSeats = maxSeats - usedSeats;
                    const usagePercent = maxSeats > 0 ? (usedSeats / maxSeats) * 100 : 0;

                    return (
                      <>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">License Type</span>
                          <Badge variant="outline" className="capitalize">
                            {licenseInfo.sku_name || 'Standard'}
                            {licenseInfo.is_trial && <span className="ml-1 text-amber-600">(Trial)</span>}
                          </Badge>
                        </div>
                        {licenseInfo.company && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Licensed To</span>
                            <span>{licenseInfo.company}</span>
                          </div>
                        )}
                        {maxSeats > 0 && (
                          <>
                            <div className="flex justify-between items-center">
                              <span className="text-muted-foreground">Seat Usage</span>
                              <span className={usagePercent > 90 ? 'text-red-600 font-medium' : usagePercent > 75 ? 'text-amber-600' : ''}>
                                {usedSeats} / {maxSeats} ({Math.round(usagePercent)}%)
                              </span>
                            </div>
                            <div className="w-full bg-zinc-100 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full transition-all ${usagePercent > 90 ? 'bg-red-500' : usagePercent > 75 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                style={{ width: `${Math.min(usagePercent, 100)}%` }}
                              />
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Available Seats</span>
                              <span className={availableSeats < 10 ? 'text-amber-600 font-medium' : 'text-emerald-600'}>
                                {availableSeats > 0 ? availableSeats : 'No seats available'}
                              </span>
                            </div>
                          </>
                        )}
                        {expiresAt && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Expires</span>
                            <span className={isExpiringSoon ? 'text-red-600 font-medium' : ''}>
                              {expiresAt.toLocaleDateString('de-DE')}
                              {isExpiringSoon && (
                                <Badge variant="outline" className="ml-2 text-red-600 border-red-200 bg-red-50">
                                  <AlertTriangle className="h-3 w-3 mr-1" />
                                  Expiring Soon
                                </Badge>
                              )}
                            </span>
                          </div>
                        )}
                        {licenseInfo.licensee_email && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">License Contact</span>
                            <span className="text-xs">{licenseInfo.licensee_email}</span>
                          </div>
                        )}
                      </>
                    );
                  })()}
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'licenses' && (
          <div className="space-y-4">
            {isManual && (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => { setAddLicenseOpen(true); setAddLicenseMode('single'); }}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Single License
                </Button>
                <Button variant="outline" size="sm" onClick={() => { setAddLicenseOpen(true); setAddLicenseMode('bulk'); }}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Bulk Keys
                </Button>
                <Button variant="outline" size="sm" onClick={() => { setAddLicenseOpen(true); setAddLicenseMode('seats'); }}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Add Seats
                </Button>
              </div>
            )}

            {categorizedLicenses ? (
              <ThreeTableLayout
                assigned={categorizedLicenses.assigned}
                unassigned={categorizedLicenses.unassigned}
                external={categorizedLicenses.external}
                serviceAccounts={categorizedLicenses.service_accounts}
                stats={categorizedLicenses.stats}
                showProvider={false}
                showStats={true}
                maxUsers={provider?.config?.provider_license_info?.max_users}
                onServiceAccountClick={handleOpenServiceAccountDialog}
                onAdminAccountClick={handleOpenAdminAccountDialog}
                onAssignClick={(license) => setAssignDialog(license)}
                onDeleteClick={(license) => setDeleteDialog(license)}
              />
            ) : (
              <div className="border rounded-lg bg-white p-8 text-center text-muted-foreground">
                <Key className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No licenses yet</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'pricing' && (
          <div className="space-y-6">
            {/* Package Pricing - for providers with package licenses (e.g., Mattermost) */}
            {provider.config?.provider_license_info?.max_users && (
              <Card className="border-blue-200 bg-blue-50/30">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Package className="h-4 w-4" />
                    Package License Pricing
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    This provider uses a package license for {provider.config.provider_license_info.max_users} users.
                    Enter the total package cost and it will be distributed across all active users.
                  </p>
                </CardHeader>
                <CardContent className="space-y-4">
                  {(() => {
                    const licenseInfo = provider.config?.provider_license_info;
                    const packagePricing = provider.config?.package_pricing || {};
                    const packageEdit = pricingEdits['__package__'] || {
                      cost: packagePricing.cost || '',
                      currency: packagePricing.currency || 'EUR',
                      billing_cycle: packagePricing.billing_cycle || 'yearly',
                      next_billing_date: packagePricing.next_billing_date || '',
                      notes: packagePricing.notes || '',
                    };
                    const updatePackageEdit = (updates: Partial<typeof packageEdit>) => {
                      setPricingEdits({
                        ...pricingEdits,
                        ['__package__']: { ...packageEdit, ...updates },
                      });
                    };

                    const packageCost = parseFloat(packageEdit.cost) || 0;
                    const maxUsers = licenseInfo?.max_users || 0;
                    const isYearly = packageEdit.billing_cycle === 'yearly';

                    // Get expiration date from license info
                    const expiresAt = licenseInfo?.expires_at ? new Date(licenseInfo.expires_at) : null;
                    const expiresAtStr = expiresAt ? expiresAt.toISOString().split('T')[0] : '';

                    // Use expires_at from license info as default for next_billing_date if not set
                    const nextBillingDate = packageEdit.next_billing_date || expiresAtStr;

                    // Cost per user based on package size (not active users)
                    // If yearly: show yearly cost per user, if monthly: show monthly cost per user
                    const costPerUser = maxUsers > 0 ? packageCost / maxUsers : 0;
                    const monthlyCostPerUser = isYearly ? costPerUser / 12 : costPerUser;

                    return (
                      <>
                        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 p-4 bg-white rounded-lg border">
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground uppercase">Package Size</p>
                            <p className="text-xl font-semibold">{maxUsers} Users</p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground uppercase">Active Users</p>
                            <p className="text-xl font-semibold">{totalLicenses}</p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground uppercase">{isYearly ? 'Yearly' : 'Monthly'} Cost</p>
                            <p className="text-xl font-semibold">{packageEdit.currency} {packageCost.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground uppercase">Cost per User</p>
                            <p className="text-xl font-semibold text-emerald-600">
                              {packageEdit.currency} {costPerUser.toFixed(2)}{isYearly ? '/yr' : '/mo'}
                            </p>
                            {isYearly && (
                              <p className="text-xs text-muted-foreground">({packageEdit.currency} {monthlyCostPerUser.toFixed(2)}/mo)</p>
                            )}
                          </div>
                          {expiresAt && (
                            <div className="text-center">
                              <p className="text-xs text-muted-foreground uppercase">Expires</p>
                              <p className="text-xl font-semibold">{expiresAt.toLocaleDateString('de-DE')}</p>
                            </div>
                          )}
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Total Package Cost</Label>
                            <div className="flex gap-1">
                              <Input
                                type="number"
                                step="0.01"
                                min="0"
                                className="flex-1"
                                placeholder="0.00"
                                value={packageEdit.cost}
                                onChange={(e) => updatePackageEdit({ cost: e.target.value })}
                              />
                              <Select value={packageEdit.currency} onValueChange={(v) => updatePackageEdit({ currency: v })}>
                                <SelectTrigger className="w-20">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="EUR">EUR</SelectItem>
                                  <SelectItem value="USD">USD</SelectItem>
                                  <SelectItem value="GBP">GBP</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                          </div>

                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Billing Cycle</Label>
                            <Select value={packageEdit.billing_cycle} onValueChange={(v) => updatePackageEdit({ billing_cycle: v })}>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="yearly">Yearly</SelectItem>
                                <SelectItem value="monthly">Monthly</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Next Billing / Renewal</Label>
                            <Input
                              type="date"
                              value={nextBillingDate}
                              onChange={(e) => updatePackageEdit({ next_billing_date: e.target.value })}
                            />
                          </div>

                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Notes</Label>
                            <Input
                              placeholder="e.g., Professional Plan"
                              value={packageEdit.notes}
                              onChange={(e) => updatePackageEdit({ notes: e.target.value })}
                            />
                          </div>
                        </div>

                        <div className="flex justify-end">
                          <Button size="sm" onClick={handleSavePricing} disabled={savingPricing}>
                            {savingPricing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                            Apply Package Pricing
                          </Button>
                        </div>
                      </>
                    );
                  })()}
                </CardContent>
              </Card>
            )}

            {/* Individual License Type Pricing - for providers with combined license types (Microsoft 365) */}
            {hasCombinedTypes && individualLicenseTypes.length > 0 && (
              <>
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-sm font-medium">License Type Pricing</h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Set prices for each individual license. The total cost per user is calculated as the sum of their assigned licenses.
                    </p>
                  </div>
                  <Button size="sm" onClick={handleSaveIndividualPricing} disabled={savingIndividualPricing}>
                    {savingIndividualPricing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                    Save Pricing
                  </Button>
                </div>

                <div className="space-y-4">
                  {individualLicenseTypes.map((lt) => {
                    const edit = individualPricingEdits[lt.license_type] || {
                      cost: '',
                      currency: 'EUR',
                      billing_cycle: 'yearly',
                      payment_frequency: 'monthly',
                      display_name: '',
                      notes: '',
                    };
                    const updateEdit = (updates: Partial<typeof edit>) => {
                      setIndividualPricingEdits({
                        ...individualPricingEdits,
                        [lt.license_type]: { ...edit, ...updates },
                      });
                    };

                    // Calculate monthly equivalent for display
                    let monthlyEquivalent = '';
                    if (edit.cost && parseFloat(edit.cost) > 0) {
                      const cost = parseFloat(edit.cost);
                      if (edit.billing_cycle === 'yearly') {
                        monthlyEquivalent = `≈ ${(cost / 12).toFixed(2)} ${edit.currency}/month`;
                      } else if (edit.billing_cycle === 'monthly') {
                        monthlyEquivalent = `${cost.toFixed(2)} ${edit.currency}/month`;
                      }
                    }

                    return (
                      <Card key={lt.license_type}>
                        <CardContent className="pt-4 pb-4">
                          <div className="flex items-start justify-between mb-3">
                            <div>
                              <p className="text-xs text-muted-foreground font-mono">{lt.license_type}</p>
                              <h3 className="font-medium text-sm">
                                {edit.display_name || lt.license_type}
                              </h3>
                              <p className="text-xs text-muted-foreground">{lt.user_count} users</p>
                            </div>
                            {monthlyEquivalent && (
                              <Badge variant="secondary" className="text-xs">
                                {monthlyEquivalent}
                              </Badge>
                            )}
                          </div>

                          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                            <div className="space-y-1.5 md:col-span-2">
                              <Label className="text-xs text-muted-foreground">Display Name</Label>
                              <Input
                                placeholder={lt.license_type}
                                value={edit.display_name}
                                onChange={(e) => updateEdit({ display_name: e.target.value })}
                              />
                            </div>

                            <div className="space-y-1.5">
                              <Label className="text-xs text-muted-foreground">Cost</Label>
                              <div className="flex gap-1">
                                <Input
                                  type="number"
                                  step="0.01"
                                  min="0"
                                  className="flex-1"
                                  placeholder="0.00"
                                  value={edit.cost}
                                  onChange={(e) => updateEdit({ cost: e.target.value })}
                                />
                                <Select value={edit.currency} onValueChange={(v) => updateEdit({ currency: v })}>
                                  <SelectTrigger className="w-20">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="EUR">EUR</SelectItem>
                                    <SelectItem value="USD">USD</SelectItem>
                                    <SelectItem value="GBP">GBP</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>

                            <div className="space-y-1.5">
                              <Label className="text-xs text-muted-foreground">Billing Cycle</Label>
                              <Select value={edit.billing_cycle} onValueChange={(v) => updateEdit({ billing_cycle: v })}>
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="yearly">Yearly</SelectItem>
                                  <SelectItem value="monthly">Monthly</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>

                            <div className="space-y-1.5">
                              <Label className="text-xs text-muted-foreground">Payment</Label>
                              <Select value={edit.payment_frequency} onValueChange={(v) => updateEdit({ payment_frequency: v })}>
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="monthly">Monthly</SelectItem>
                                  <SelectItem value="yearly">Yearly</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </>
            )}

            {/* License Type Pricing - for providers without combined types */}
            {!hasCombinedTypes && (
              <>
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-sm font-medium">License Type Pricing</h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {provider.config?.provider_license_info?.max_users
                        ? 'Or set individual prices per license type (overrides package pricing).'
                        : 'Set prices for each license type. Prices will be applied to existing and new licenses.'}
                    </p>
                  </div>
                  <Button size="sm" onClick={handleSavePricing} disabled={savingPricing}>
                    {savingPricing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                    Save Pricing
                  </Button>
                </div>
              </>
            )}

            {!hasCombinedTypes && licenseTypes.length === 0 && (
              <div className="border rounded-lg bg-white p-8 text-center text-muted-foreground">
                <DollarSign className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No license types found</p>
                <p className="text-xs mt-1">Sync the provider to discover license types</p>
              </div>
            )}

            {!hasCombinedTypes && licenseTypes.length > 0 && (
              <div className="space-y-4">
                {licenseTypes.map((lt) => {
                  const edit = pricingEdits[lt.license_type] || {
                    cost: '',
                    currency: 'EUR',
                    billing_cycle: 'yearly',
                    payment_frequency: 'yearly',
                    display_name: '',
                    next_billing_date: '',
                    notes: '',
                  };
                  const updateEdit = (updates: Partial<typeof edit>) => {
                    setPricingEdits({
                      ...pricingEdits,
                      [lt.license_type]: { ...edit, ...updates },
                    });
                  };

                  // Calculate monthly equivalent for display
                  let monthlyEquivalent = '';
                  if (edit.cost && parseFloat(edit.cost) > 0) {
                    const cost = parseFloat(edit.cost);
                    if (edit.billing_cycle === 'yearly') {
                      monthlyEquivalent = `≈ ${(cost / 12).toFixed(2)} ${edit.currency}/month`;
                    } else if (edit.billing_cycle === 'monthly') {
                      monthlyEquivalent = `${cost.toFixed(2)} ${edit.currency}/month`;
                    }
                  }

                  return (
                    <Card key={lt.license_type}>
                      <CardContent className="pt-4 pb-4">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <p className="text-xs text-muted-foreground font-mono">{lt.license_type}</p>
                            <h3 className="font-medium text-sm">
                              {edit.display_name || lt.license_type}
                            </h3>
                            <p className="text-xs text-muted-foreground">
                              {licenses.filter(l => l.license_type === lt.license_type && l.status === 'active').length} active licenses
                              {licenses.filter(l => l.license_type === lt.license_type && l.status !== 'active').length > 0 && (
                                <span className="text-zinc-400"> ({licenses.filter(l => l.license_type === lt.license_type && l.status !== 'active').length} inactive)</span>
                              )}
                            </p>
                          </div>
                          {monthlyEquivalent && (
                            <Badge variant="secondary" className="text-xs">
                              {monthlyEquivalent}
                            </Badge>
                          )}
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
                          <div className="space-y-1.5 md:col-span-2">
                            <Label className="text-xs text-muted-foreground">Display Name</Label>
                            <Input
                              placeholder={lt.license_type}
                              value={edit.display_name}
                              onChange={(e) => updateEdit({ display_name: e.target.value })}
                            />
                          </div>

                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Next Billing</Label>
                            <Input
                              type="date"
                              value={edit.next_billing_date}
                              onChange={(e) => updateEdit({ next_billing_date: e.target.value })}
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Cost</Label>
                            <div className="flex gap-1">
                              <Input
                                type="number"
                                step="0.01"
                                min="0"
                                className="flex-1"
                                placeholder="0.00"
                                value={edit.cost}
                                onChange={(e) => updateEdit({ cost: e.target.value })}
                              />
                              <Select value={edit.currency} onValueChange={(v) => updateEdit({ currency: v })}>
                                <SelectTrigger className="w-20">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="EUR">EUR</SelectItem>
                                  <SelectItem value="USD">USD</SelectItem>
                                  <SelectItem value="GBP">GBP</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                          </div>

                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Billing Cycle</Label>
                            <Select value={edit.billing_cycle} onValueChange={(v) => updateEdit({ billing_cycle: v })}>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="yearly">Yearly</SelectItem>
                                <SelectItem value="monthly">Monthly</SelectItem>
                                <SelectItem value="perpetual">Perpetual</SelectItem>
                                <SelectItem value="one_time">One-time</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Payment</Label>
                            <Select value={edit.payment_frequency} onValueChange={(v) => updateEdit({ payment_frequency: v })}>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="yearly">Yearly</SelectItem>
                                <SelectItem value="monthly">Monthly</SelectItem>
                                <SelectItem value="one_time">One-time</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Notes</Label>
                            <Input
                              placeholder="e.g., Volume discount"
                              value={edit.notes}
                              onChange={(e) => updateEdit({ notes: e.target.value })}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}

            {!hasCombinedTypes && licenseTypes.length > 0 && (
              <p className="text-xs text-muted-foreground">
                The monthly cost shown on licenses is calculated from the billing cycle.
                Yearly costs are divided by 12, perpetual/one-time show as €0/month.
              </p>
            )}

            {hasCombinedTypes && individualLicenseTypes.length > 0 && (
              <p className="text-xs text-muted-foreground">
                The monthly cost per user is calculated as the sum of all their individual license prices.
                Yearly costs are divided by 12.
              </p>
            )}

            {/* License Packages Section */}
            <div className="border-t pt-6 mt-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-sm font-medium flex items-center gap-2">
                    <Package className="h-4 w-4" />
                    License Packages
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Track purchased seat packages and their utilization
                  </p>
                </div>
                <Button size="sm" variant="outline" onClick={() => handleOpenPackageDialog()}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add Package
                </Button>
              </div>

              {licensePackages.length === 0 ? (
                <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground">
                  <Package className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No license packages defined</p>
                  <p className="text-xs mt-1">Add a package to track seat utilization</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {licensePackages.map((pkg) => (
                    <Card key={pkg.id}>
                      <CardContent className="pt-4 pb-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="font-medium text-sm">{pkg.display_name || pkg.license_type}</h3>
                              <Badge
                                variant="outline"
                                className={pkg.utilization_percent > 90 ? 'text-red-600 border-red-200 bg-red-50' : pkg.utilization_percent > 70 ? 'text-amber-600 border-amber-200 bg-amber-50' : 'text-emerald-600 border-emerald-200 bg-emerald-50'}
                              >
                                {pkg.utilization_percent}% used
                              </Badge>
                              {pkg.status === 'cancelled' && (
                                <Badge variant="destructive">Cancelled</Badge>
                              )}
                              {pkg.status === 'expired' && (
                                <Badge variant="secondary">Expired</Badge>
                              )}
                              {pkg.needs_reorder && (
                                <Badge variant="outline" className="text-blue-600 border-blue-200 bg-blue-50">
                                  Needs Reorder
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground font-mono mb-2">{pkg.license_type}</p>

                            <div className="flex items-center gap-4 text-sm">
                              <div>
                                <span className="text-muted-foreground">Seats:</span>{' '}
                                <span className="font-medium">{pkg.assigned_seats}</span>
                                <span className="text-muted-foreground"> / {pkg.total_seats}</span>
                                {pkg.available_seats > 0 && (
                                  <span className="text-emerald-600 ml-1">({pkg.available_seats} available)</span>
                                )}
                              </div>
                              {pkg.cost_per_seat && (
                                <div>
                                  <span className="text-muted-foreground">Cost/seat:</span>{' '}
                                  <span className="font-medium">{pkg.currency} {pkg.cost_per_seat}</span>
                                </div>
                              )}
                              {pkg.total_monthly_cost && (
                                <div>
                                  <span className="text-muted-foreground">Total:</span>{' '}
                                  <span className="font-medium">{pkg.currency} {pkg.total_monthly_cost}/mo</span>
                                </div>
                              )}
                            </div>

                            {(pkg.contract_start || pkg.contract_end) && (
                              <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                                <Calendar className="h-3 w-3" />
                                {pkg.contract_start && <span>From {new Date(pkg.contract_start).toLocaleDateString('de-DE')}</span>}
                                {pkg.contract_end && <span>to {new Date(pkg.contract_end).toLocaleDateString('de-DE')}</span>}
                                {pkg.auto_renew && <Badge variant="secondary" className="text-xs">Auto-renew</Badge>}
                              </div>
                            )}
                            {pkg.cancelled_at && pkg.cancellation_effective_date && (
                              <div className="flex items-center gap-2 mt-2 text-xs text-red-600">
                                <AlertTriangle className="h-3 w-3" />
                                <span>
                                  Cancellation effective: {new Date(pkg.cancellation_effective_date).toLocaleDateString('de-DE')}
                                  {pkg.cancellation_reason && ` - ${pkg.cancellation_reason}`}
                                </span>
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" onClick={() => handleOpenPackageDialog(pkg)}>
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeletePackage(pkg)}>
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </div>

                        {/* Utilization bar */}
                        <div className="mt-3 h-2 bg-zinc-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all ${pkg.utilization_percent > 90 ? 'bg-red-500' : pkg.utilization_percent > 70 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                            style={{ width: `${Math.min(100, pkg.utilization_percent)}%` }}
                          />
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>

            {/* Organization Licenses Section */}
            <div className="border-t pt-6 mt-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-sm font-medium flex items-center gap-2">
                    <Building2 className="h-4 w-4" />
                    Organization Licenses
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Organization-wide licenses not tied to individual users (e.g., storage, capacity)
                  </p>
                </div>
                <Button size="sm" variant="outline" onClick={() => handleOpenOrgLicenseDialog()}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add License
                </Button>
              </div>

              {orgLicenses.length === 0 ? (
                <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground">
                  <Building2 className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No organization licenses</p>
                  <p className="text-xs mt-1">Add licenses for organization-wide resources</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {orgLicenses.map((lic) => (
                    <Card key={lic.id}>
                      <CardContent className="pt-4 pb-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h3 className="font-medium text-sm">{lic.name}</h3>
                            {lic.license_type && (
                              <p className="text-xs text-muted-foreground font-mono">{lic.license_type}</p>
                            )}

                            <div className="flex items-center gap-4 mt-2 text-sm">
                              {lic.quantity && (
                                <div>
                                  <span className="text-muted-foreground">Quantity:</span>{' '}
                                  <span className="font-medium">{lic.quantity} {lic.unit || 'units'}</span>
                                </div>
                              )}
                              {lic.monthly_cost && (
                                <div>
                                  <span className="text-muted-foreground">Cost:</span>{' '}
                                  <span className="font-medium">{lic.currency} {lic.monthly_cost}/mo</span>
                                </div>
                              )}
                            </div>

                            {lic.renewal_date && (
                              <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                                <Calendar className="h-3 w-3" />
                                <span>Renews {new Date(lic.renewal_date).toLocaleDateString('de-DE')}</span>
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" onClick={() => handleOpenOrgLicenseDialog(lic)}>
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteOrgLicense(lic)}>
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'files' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-medium">Documents & Files</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Upload contracts, invoices, and other documents related to this provider.
                </p>
              </div>
            </div>

            {/* Upload Section */}
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Category</Label>
                    <Select value={fileCategory} onValueChange={setFileCategory}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="agreement">Agreement</SelectItem>
                        <SelectItem value="contract">Contract</SelectItem>
                        <SelectItem value="invoice">Invoice</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                        <SelectItem value="quote">Quote</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1.5 md:col-span-2">
                    <Label className="text-xs text-muted-foreground">Description (optional)</Label>
                    <Input
                      placeholder="e.g., Annual contract 2024"
                      value={fileDescription}
                      onChange={(e) => setFileDescription(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label
                      htmlFor="file-upload"
                      className={`inline-flex items-center justify-center h-9 px-4 rounded-md text-sm font-medium cursor-pointer transition-colors ${
                        uploadingFile
                          ? 'bg-zinc-100 text-zinc-400 cursor-not-allowed'
                          : 'bg-zinc-900 text-white hover:bg-zinc-800'
                      }`}
                    >
                      {uploadingFile ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <Upload className="h-4 w-4 mr-2" />
                          Upload File
                        </>
                      )}
                    </Label>
                    <input
                      id="file-upload"
                      type="file"
                      className="hidden"
                      accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.bmp,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp"
                      onChange={handleFileUpload}
                      disabled={uploadingFile}
                    />
                    <p className="text-xs text-muted-foreground">
                      Allowed: PDF, Images (PNG, JPG, GIF), Office documents (Word, Excel, PowerPoint)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Files List */}
            {files.length === 0 ? (
              <div className="border rounded-lg bg-white p-8 text-center text-muted-foreground">
                <FileText className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No files uploaded yet</p>
                <p className="text-xs mt-1">Upload contracts, invoices, or other documents</p>
              </div>
            ) : (
              <div className="border rounded-lg bg-white overflow-hidden">
                <table className="w-full">
                  <thead className="bg-zinc-50 border-b">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">File</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Category</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Size</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Uploaded</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {files.map((file) => (
                      <tr key={file.id} className="hover:bg-zinc-50">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <File className="h-4 w-4 text-muted-foreground" />
                            <div>
                              <p className="text-sm font-medium">{file.original_name}</p>
                              {file.description && (
                                <p className="text-xs text-muted-foreground">{file.description}</p>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="outline" className="text-xs capitalize">
                            {file.category || 'other'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">
                          {formatFileSize(file.file_size)}
                        </td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">
                          {new Date(file.created_at).toLocaleDateString('de-DE')}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {file.viewable && (
                              <a
                                href={api.getProviderFileViewUrl(providerId, file.id)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-zinc-100 transition-colors"
                                title="View in browser"
                              >
                                <Eye className="h-3.5 w-3.5" />
                              </a>
                            )}
                            <a
                              href={api.getProviderFileDownloadUrl(providerId, file.id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-zinc-100 transition-colors"
                              title="Download"
                            >
                              <Download className="h-3.5 w-3.5" />
                            </a>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-red-600"
                              onClick={() => handleDeleteFile(file.id)}
                              title="Delete"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="max-w-xl space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">General Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-xs font-medium">Display Name</Label>
                  <Input
                    value={settingsForm.display_name}
                    onChange={(e) => setSettingsForm({ ...settingsForm, display_name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-medium">License Model</Label>
                  <Select value={settingsForm.license_model} onValueChange={(v) => setSettingsForm({ ...settingsForm, license_model: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {licenseModelOptions.map((o) => (
                        <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Seat-based licenses are tied to users. License-based licenses can be transferred between users.
                  </p>
                </div>
                <Button onClick={handleSaveSettings} disabled={savingSettings}>
                  {savingSettings ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                  Save Settings
                </Button>
              </CardContent>
            </Card>

            {/* Danger Zone */}
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="text-sm text-red-600">Danger Zone</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-3">
                  Deleting this provider will remove all associated licenses.
                </p>
                <Button
                  variant="outline"
                  className="text-red-600 border-red-200 hover:bg-red-50"
                  onClick={async () => {
                    if (confirm(`Delete provider "${provider.display_name}" and all its licenses?`)) {
                      try {
                        await api.deleteProvider(provider.id);
                        router.push('/settings');
                      } catch (e) {
                        showToast('error', 'Failed to delete provider');
                      }
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4 mr-1.5" />
                  Delete Provider
                </Button>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Add License Dialog */}
      <Dialog open={addLicenseOpen} onOpenChange={setAddLicenseOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {addLicenseMode === 'bulk' ? 'Add Multiple Licenses' : addLicenseMode === 'seats' ? 'Add Seats' : 'Add License'}
            </DialogTitle>
            <DialogDescription>
              {addLicenseMode === 'bulk'
                ? 'Enter one license key per line'
                : addLicenseMode === 'seats'
                ? 'Add multiple unnamed seats'
                : 'Add a single license with optional key'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-xs font-medium">License Type</Label>
              <Input
                value={licenseForm.license_type}
                onChange={(e) => setLicenseForm({ ...licenseForm, license_type: e.target.value })}
                placeholder="e.g., Pro, Enterprise, Standard"
              />
            </div>

            {addLicenseMode === 'single' && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">License Key (optional)</Label>
                <Input
                  value={licenseForm.license_key}
                  onChange={(e) => setLicenseForm({ ...licenseForm, license_key: e.target.value })}
                  placeholder="e.g., XXXX-YYYY-ZZZZ"
                />
              </div>
            )}

            {addLicenseMode === 'bulk' && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">License Keys (one per line)</Label>
                <Textarea
                  value={bulkKeys}
                  onChange={(e) => setBulkKeys(e.target.value)}
                  placeholder="KEY-0001-AAAA&#10;KEY-0002-BBBB&#10;KEY-0003-CCCC"
                  rows={6}
                />
              </div>
            )}

            {addLicenseMode === 'seats' && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">Number of Seats</Label>
                <Input
                  type="number"
                  min="1"
                  value={licenseForm.quantity}
                  onChange={(e) => setLicenseForm({ ...licenseForm, quantity: e.target.value })}
                />
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-xs font-medium">Cost per License</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={licenseForm.monthly_cost}
                  onChange={(e) => setLicenseForm({ ...licenseForm, monthly_cost: e.target.value })}
                  placeholder={provider?.config?.default_cost || 'Optional'}
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-medium">Valid Until</Label>
                <Input
                  type="date"
                  value={licenseForm.valid_until}
                  onChange={(e) => setLicenseForm({ ...licenseForm, valid_until: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">Notes (optional)</Label>
              <Input
                value={licenseForm.notes}
                onChange={(e) => setLicenseForm({ ...licenseForm, notes: e.target.value })}
                placeholder="e.g., Purchased via vendor"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAddLicenseOpen(false)}>Cancel</Button>
            <Button onClick={handleAddLicense} disabled={savingLicense}>
              {savingLicense ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Add {addLicenseMode === 'bulk' ? 'Licenses' : addLicenseMode === 'seats' ? 'Seats' : 'License'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign Dialog */}
      <Dialog open={!!assignDialog} onOpenChange={() => setAssignDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign License</DialogTitle>
            <DialogDescription>
              Assign <strong>{assignDialog?.metadata?.email || assignDialog?.external_user_id}</strong> to an employee
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label className="text-xs font-medium mb-2 block">Select Employee</Label>
            <Select value={selectedEmployeeId} onValueChange={setSelectedEmployeeId}>
              <SelectTrigger>
                <SelectValue placeholder="Choose employee..." />
              </SelectTrigger>
              <SelectContent>
                {employees.map((emp) => (
                  <SelectItem key={emp.id} value={emp.id}>
                    {emp.full_name} ({emp.email})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAssignDialog(null)}>Cancel</Button>
            <Button onClick={handleAssign} disabled={!selectedEmployeeId}>Assign</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={!!deleteDialog} onOpenChange={() => setDeleteDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete License</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteDialog?.external_user_id}</strong>? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteDialog(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteLicense}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Service Account Dialog */}
      <Dialog open={!!serviceAccountDialog} onOpenChange={() => setServiceAccountDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-blue-500" />
              Service Account Settings
            </DialogTitle>
            <DialogDescription>
              Configure <strong>{serviceAccountDialog?.external_user_id}</strong> as a service account.
              Service accounts are intentionally not linked to HRIS employees.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="is_service_account"
                checked={serviceAccountForm.is_service_account}
                onChange={(e) => setServiceAccountForm(prev => ({ ...prev, is_service_account: e.target.checked }))}
                className="h-4 w-4 rounded border-zinc-300 text-blue-600 focus:ring-blue-500"
              />
              <Label htmlFor="is_service_account" className="cursor-pointer">
                Mark as Service Account
              </Label>
            </div>

            {serviceAccountForm.is_service_account && (
              <>
                <div>
                  <Label className="text-xs font-medium mb-2 block">Service Account Name (optional)</Label>
                  <Input
                    placeholder="e.g., Backup Service, CI/CD Bot, Shared Mailbox"
                    value={serviceAccountForm.service_account_name}
                    onChange={(e) => setServiceAccountForm(prev => ({ ...prev, service_account_name: e.target.value }))}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    A descriptive name for this service account
                  </p>
                </div>

                <div>
                  <Label className="text-xs font-medium mb-2 block">Owner (optional)</Label>
                  <Select
                    value={serviceAccountForm.service_account_owner_id}
                    onValueChange={(v) => setServiceAccountForm(prev => ({ ...prev, service_account_owner_id: v === '__none__' ? '' : v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select responsible employee..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">No owner</SelectItem>
                      {employees.map((emp) => (
                        <SelectItem key={emp.id} value={emp.id}>
                          {emp.full_name} ({emp.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground mt-1">
                    The employee responsible for this service account
                  </p>
                </div>

                <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <input
                    type="checkbox"
                    id="apply_globally"
                    checked={serviceAccountForm.apply_globally}
                    onChange={(e) => setServiceAccountForm(prev => ({ ...prev, apply_globally: e.target.checked }))}
                    className="h-4 w-4 rounded border-zinc-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <Label htmlFor="apply_globally" className="cursor-pointer font-medium">
                      Apply globally
                    </Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Add this email to the global service account patterns list.
                      All licenses with this email will be automatically marked as service accounts.
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setServiceAccountDialog(null)}>Cancel</Button>
            <Button onClick={handleSaveServiceAccount} disabled={savingServiceAccount}>
              {savingServiceAccount && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Admin Account Dialog */}
      <Dialog open={!!adminAccountDialog} onOpenChange={() => setAdminAccountDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-purple-500" />
              Admin Account Settings
            </DialogTitle>
            <DialogDescription>
              Configure <strong>{adminAccountDialog?.external_user_id}</strong> as an admin account.
              Admin accounts are elevated-privilege accounts linked to employees.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="is_admin_account"
                checked={adminAccountForm.is_admin_account}
                onChange={(e) => setAdminAccountForm(prev => ({ ...prev, is_admin_account: e.target.checked }))}
                className="h-4 w-4 rounded border-zinc-300 text-purple-600 focus:ring-purple-500"
              />
              <Label htmlFor="is_admin_account" className="cursor-pointer">
                Mark as Admin Account
              </Label>
            </div>

            {adminAccountForm.is_admin_account && (
              <>
                <div>
                  <Label className="text-xs font-medium mb-2 block">Admin Account Name (optional)</Label>
                  <Input
                    placeholder="e.g., IT Admin, Root Access, Domain Admin"
                    value={adminAccountForm.admin_account_name}
                    onChange={(e) => setAdminAccountForm(prev => ({ ...prev, admin_account_name: e.target.value }))}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    A descriptive name for this admin account
                  </p>
                </div>

                <div>
                  <Label className="text-xs font-medium mb-2 block">Owner (linked employee)</Label>
                  <Select
                    value={adminAccountForm.admin_account_owner_id}
                    onValueChange={(v) => setAdminAccountForm(prev => ({ ...prev, admin_account_owner_id: v === '__none__' ? '' : v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select employee..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">No owner</SelectItem>
                      {employees.map((emp) => (
                        <SelectItem key={emp.id} value={emp.id}>
                          {emp.full_name} ({emp.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground mt-1">
                    The employee who owns this admin account. If offboarded, a warning will be shown.
                  </p>
                </div>

                <div className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg border border-purple-200">
                  <input
                    type="checkbox"
                    id="apply_globally_admin"
                    checked={adminAccountForm.apply_globally}
                    onChange={(e) => setAdminAccountForm(prev => ({ ...prev, apply_globally: e.target.checked }))}
                    className="h-4 w-4 rounded border-zinc-300 text-purple-600 focus:ring-purple-500"
                  />
                  <div>
                    <Label htmlFor="apply_globally_admin" className="cursor-pointer font-medium">
                      Apply globally
                    </Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Add this email to the global admin account patterns list.
                      All licenses with this email will be automatically marked as admin accounts.
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAdminAccountDialog(null)}>Cancel</Button>
            <Button onClick={handleSaveAdminAccount} disabled={savingAdminAccount}>
              {savingAdminAccount && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* License Package Dialog */}
      <Dialog open={packageDialogOpen} onOpenChange={setPackageDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              {editingPackage ? 'Edit License Package' : 'Add License Package'}
            </DialogTitle>
            <DialogDescription>
              {editingPackage
                ? 'Update the license package details.'
                : 'Define a purchased license package to track seat utilization.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">License Type *</Label>
                <Input
                  placeholder="e.g., Enterprise, Pro, Business"
                  value={packageForm.license_type}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, license_type: e.target.value }))}
                  disabled={!!editingPackage}
                />
              </div>
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">Display Name</Label>
                <Input
                  placeholder="Optional friendly name"
                  value={packageForm.display_name}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, display_name: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">Total Seats *</Label>
                <Input
                  type="number"
                  min="1"
                  placeholder="100"
                  value={packageForm.total_seats}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, total_seats: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">Cost per Seat</Label>
                <div className="flex gap-1">
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="15.00"
                    value={packageForm.cost_per_seat}
                    onChange={(e) => setPackageForm(prev => ({ ...prev, cost_per_seat: e.target.value }))}
                  />
                  <Select value={packageForm.currency} onValueChange={(v) => setPackageForm(prev => ({ ...prev, currency: v }))}>
                    <SelectTrigger className="w-20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="EUR">EUR</SelectItem>
                      <SelectItem value="USD">USD</SelectItem>
                      <SelectItem value="GBP">GBP</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">Billing Cycle</Label>
                <Select value={packageForm.billing_cycle} onValueChange={(v) => setPackageForm(prev => ({ ...prev, billing_cycle: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="monthly">Monthly</SelectItem>
                    <SelectItem value="yearly">Yearly</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">Contract Start</Label>
                <Input
                  type="date"
                  value={packageForm.contract_start}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, contract_start: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">Contract End</Label>
                <Input
                  type="date"
                  value={packageForm.contract_end}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, contract_end: e.target.value }))}
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="auto_renew"
                  checked={packageForm.auto_renew}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, auto_renew: e.target.checked }))}
                  className="h-4 w-4 rounded border-zinc-300"
                />
                <Label htmlFor="auto_renew" className="text-sm cursor-pointer">Auto-renew</Label>
              </div>
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">Notes</Label>
                <Textarea
                  placeholder="Optional notes..."
                  value={packageForm.notes}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, notes: e.target.value }))}
                  rows={2}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPackageDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSavePackage} disabled={savingPackage}>
              {savingPackage && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {editingPackage ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Organization License Dialog */}
      <Dialog open={orgLicenseDialogOpen} onOpenChange={setOrgLicenseDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              {editingOrgLicense ? 'Edit Organization License' : 'Add Organization License'}
            </DialogTitle>
            <DialogDescription>
              {editingOrgLicense
                ? 'Update the organization license details.'
                : 'Add an organization-wide license (e.g., storage, capacity, enterprise features).'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">Name *</Label>
                <Input
                  placeholder="e.g., SharePoint Storage Extension"
                  value={orgLicenseForm.name}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, name: e.target.value }))}
                />
              </div>
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">License Type</Label>
                <Input
                  placeholder="Optional type/SKU"
                  value={orgLicenseForm.license_type}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, license_type: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">Quantity</Label>
                <Input
                  type="number"
                  min="0"
                  placeholder="100"
                  value={orgLicenseForm.quantity}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, quantity: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">Unit</Label>
                <Input
                  placeholder="e.g., GB, TB, users"
                  value={orgLicenseForm.unit}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, unit: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">Monthly Cost</Label>
                <div className="flex gap-1">
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="50.00"
                    value={orgLicenseForm.monthly_cost}
                    onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, monthly_cost: e.target.value }))}
                  />
                  <Select value={orgLicenseForm.currency} onValueChange={(v) => setOrgLicenseForm(prev => ({ ...prev, currency: v }))}>
                    <SelectTrigger className="w-20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="EUR">EUR</SelectItem>
                      <SelectItem value="USD">USD</SelectItem>
                      <SelectItem value="GBP">GBP</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">Billing Cycle</Label>
                <Select value={orgLicenseForm.billing_cycle} onValueChange={(v) => setOrgLicenseForm(prev => ({ ...prev, billing_cycle: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="monthly">Monthly</SelectItem>
                    <SelectItem value="yearly">Yearly</SelectItem>
                    <SelectItem value="one_time">One-time</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">Renewal Date</Label>
                <Input
                  type="date"
                  value={orgLicenseForm.renewal_date}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, renewal_date: e.target.value }))}
                />
              </div>
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">Notes</Label>
                <Textarea
                  placeholder="Optional notes..."
                  value={orgLicenseForm.notes}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, notes: e.target.value }))}
                  rows={2}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOrgLicenseDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveOrgLicense} disabled={savingOrgLicense}>
              {savingOrgLicense && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {editingOrgLicense ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
