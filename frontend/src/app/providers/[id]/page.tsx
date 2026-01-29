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
import { api, Provider, License, Employee, LicenseTypeInfo, LicenseTypePricing, ProviderFile } from '@/lib/api';
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

  // Files
  const [files, setFiles] = useState<ProviderFile[]>([]);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [fileDescription, setFileDescription] = useState('');
  const [fileCategory, setFileCategory] = useState('other');

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  };

  const isManual = provider?.config?.provider_type === 'manual' || provider?.name === 'manual';

  const fetchProvider = useCallback(async () => {
    try {
      const p = await api.getProvider(providerId);
      setProvider(p);
      setSettingsForm({
        display_name: p.display_name,
        license_model: p.config?.license_model || 'license_based',
      });
    } catch (error) {
      console.error('Failed to fetch provider:', error);
    }
  }, [providerId]);

  const fetchLicenses = useCallback(async () => {
    try {
      const data = await api.getLicenses({ provider_id: providerId, page_size: 200 });
      setLicenses(data.items);
    } catch (error) {
      console.error('Failed to fetch licenses:', error);
    }
  }, [providerId]);

  const fetchEmployees = useCallback(async () => {
    try {
      const data = await api.getEmployees({ status: 'active', page_size: 200 });
      setEmployees(data.items);
    } catch (error) {
      console.error('Failed to fetch employees:', error);
    }
  }, []);

  const fetchLicenseTypes = useCallback(async () => {
    try {
      const data = await api.getProviderLicenseTypes(providerId);
      setLicenseTypes(data.license_types);
      // Initialize pricing edits with current values
      const edits: Record<string, { cost: string; currency: string; billing_cycle: string; payment_frequency: string; display_name: string; next_billing_date: string; notes: string }> = {};
      for (const lt of data.license_types) {
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
      setPricingEdits(edits);
    } catch (error) {
      console.error('Failed to fetch license types:', error);
    }
  }, [providerId]);

  const fetchFiles = useCallback(async () => {
    try {
      const data = await api.getProviderFiles(providerId);
      setFiles(data.items);
    } catch (error) {
      console.error('Failed to fetch files:', error);
    }
  }, [providerId]);

  useEffect(() => {
    Promise.all([fetchProvider(), fetchLicenses(), fetchEmployees(), fetchLicenseTypes(), fetchFiles()]).finally(() =>
      setLoading(false)
    );
  }, [fetchProvider, fetchLicenses, fetchEmployees, fetchLicenseTypes]);

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
      await fetchProvider();
    } catch (error: any) {
      showToast('error', error.message || 'Failed to delete');
    }
  };

  const handleSavePricing = async () => {
    if (!provider) return;
    setSavingPricing(true);
    try {
      const pricing: LicenseTypePricing[] = [];
      for (const [licenseType, edit] of Object.entries(pricingEdits)) {
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
      await api.updateProviderPricing(provider.id, pricing);
      await fetchLicenseTypes();
      await fetchLicenses();
      showToast('success', 'Pricing saved and applied to licenses');
    } catch (error: any) {
      showToast('error', error.message || 'Failed to save pricing');
    } finally {
      setSavingPricing(false);
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

  // Stats
  const totalLicenses = licenses.length;
  const assignedLicenses = licenses.filter((l) => l.employee_id).length;
  const unassignedLicenses = totalLicenses - assignedLicenses;
  const totalMonthlyCost = licenses.reduce((sum, l) => sum + (parseFloat(l.monthly_cost || '0') || 0), 0);

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

        {/* Header */}
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-4">
            <Link href="/settings">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${isManual ? 'bg-purple-50' : 'bg-zinc-100'}`}>
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
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-center gap-2 text-muted-foreground mb-1">
                    <Key className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase">Licenses</span>
                  </div>
                  <p className="text-2xl font-semibold">{totalLicenses}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-center gap-2 text-muted-foreground mb-1">
                    <Users className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase">Assigned</span>
                  </div>
                  <p className="text-2xl font-semibold">{assignedLicenses}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-center gap-2 text-muted-foreground mb-1">
                    <Package className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase">Unassigned</span>
                  </div>
                  <p className="text-2xl font-semibold text-amber-600">{unassignedLicenses}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-center gap-2 text-muted-foreground mb-1">
                    <DollarSign className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase">Monthly Cost</span>
                  </div>
                  <p className="text-2xl font-semibold">
                    {provider.config?.currency || 'EUR'} {totalMonthlyCost.toFixed(2)}
                  </p>
                </CardContent>
              </Card>
            </div>

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
                  <span>{provider.config?.license_model === 'seat_based' ? 'Seat-based' : 'License-based'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Billing Cycle</span>
                  <span className="capitalize">{provider.config?.billing_cycle || 'Not set'}</span>
                </div>
                {provider.config?.default_cost && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Default Cost</span>
                    <span>{provider.config.currency || 'EUR'} {provider.config.default_cost}</span>
                  </div>
                )}
                {!isManual && provider.last_sync_at && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Sync</span>
                    <span>{new Date(provider.last_sync_at).toLocaleString('de-DE')}</span>
                  </div>
                )}
              </CardContent>
            </Card>
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

            <div className="border rounded-lg bg-white">
              {licenses.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Key className="h-8 w-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No licenses yet</p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-zinc-50/50">
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">License</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">Assigned To</th>
                      <th className="text-left px-4 py-3 font-medium text-muted-foreground">Type</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">Cost</th>
                      <th className="text-right px-4 py-3 font-medium text-muted-foreground">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {licenses.map((license) => {
                      // Determine license status for badge display
                      const isExternal = license.is_external_email;
                      const isOffboarded = license.employee_status === 'offboarded';
                      const isUnassigned = !license.employee_id;

                      return (
                        <tr key={license.id} className="border-b last:border-0">
                          <td className="px-4 py-3">
                            <div>
                              <p className="font-medium">{license.external_user_id}</p>
                              {license.metadata?.notes && (
                                <p className="text-xs text-muted-foreground">{license.metadata.notes}</p>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            {/* Priority: External > Offboarded > Assigned > Unassigned */}
                            {isExternal ? (
                              <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50">
                                <Globe className="h-3 w-3 mr-1" />
                                External
                              </Badge>
                            ) : isOffboarded ? (
                              <div className="flex items-center gap-2">
                                <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-zinc-900 group">
                                  <div className="h-6 w-6 rounded-full bg-red-100 flex items-center justify-center">
                                    <span className="text-xs font-medium text-red-600">{license.employee_name?.charAt(0)}</span>
                                  </div>
                                  <span className="hover:underline text-muted-foreground line-through">{license.employee_name}</span>
                                </Link>
                                <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50">
                                  <Skull className="h-3 w-3 mr-1" />
                                  Offboarded
                                </Badge>
                              </div>
                            ) : isUnassigned ? (
                              <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50">
                                Unassigned
                              </Badge>
                            ) : (
                              <Link href={`/users/${license.employee_id}`} className="flex items-center gap-2 hover:text-zinc-900 group">
                                <div className="h-6 w-6 rounded-full bg-zinc-100 flex items-center justify-center group-hover:bg-zinc-200 transition-colors">
                                  <span className="text-xs font-medium">{license.employee_name?.charAt(0)}</span>
                                </div>
                                <span className="hover:underline">{license.employee_name}</span>
                              </Link>
                            )}
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">
                            <div>
                              <span>{license.license_type_display_name || license.license_type || '-'}</span>
                              {license.license_type_display_name && license.license_type && (
                                <span className="block text-xs text-muted-foreground/60 font-mono">{license.license_type}</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {license.monthly_cost ? `${license.currency} ${license.monthly_cost}` : '-'}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              {license.employee_id ? (
                                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleUnassign(license)} title="Unassign">
                                  <UserMinus className="h-3.5 w-3.5" />
                                </Button>
                              ) : (
                                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setAssignDialog(license)} title="Assign">
                                  <UserPlus className="h-3.5 w-3.5" />
                                </Button>
                              )}
                              {isManual && (
                                <Button variant="ghost" size="icon" className="h-7 w-7 text-red-600" onClick={() => setDeleteDialog(license)} title="Delete">
                                  <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {activeTab === 'pricing' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-medium">License Type Pricing</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Set prices for each license type. Prices will be applied to existing and new licenses.
                </p>
              </div>
              <Button size="sm" onClick={handleSavePricing} disabled={savingPricing}>
                {savingPricing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Save Pricing
              </Button>
            </div>

            {licenseTypes.length === 0 ? (
              <div className="border rounded-lg bg-white p-8 text-center text-muted-foreground">
                <DollarSign className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No license types found</p>
                <p className="text-xs mt-1">Sync the provider to discover license types</p>
              </div>
            ) : (
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
                            <p className="text-xs text-muted-foreground">{lt.count} licenses</p>
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

            {licenseTypes.length > 0 && (
              <p className="text-xs text-muted-foreground">
                The monthly cost shown on licenses is calculated from the billing cycle.
                Yearly costs are divided by 12, perpetual/one-time show as €0/month.
              </p>
            )}
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

                  <div>
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
                      onChange={handleFileUpload}
                      disabled={uploadingFile}
                    />
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
                            <a
                              href={api.getProviderFileDownloadUrl(providerId, file.id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-zinc-100 transition-colors"
                              title="View/Download"
                            >
                              <Eye className="h-3.5 w-3.5" />
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
              Assign <strong>{assignDialog?.external_user_id}</strong> to an employee
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
    </AppLayout>
  );
}
