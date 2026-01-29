'use client';

import { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/app-layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
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
import { api, Provider } from '@/lib/api';
import { Plus, Pencil, Trash2, RefreshCw, Users, Key, CheckCircle2, XCircle, Loader2, Building2, Package } from 'lucide-react';
import Link from 'next/link';

const hrisProvider = { value: 'hibob', label: 'HiBob', fields: ['auth_token'] };

const licenseProviderTypes = [
  { value: '1password', label: '1Password', fields: ['api_token', 'sign_in_address'], type: 'api' },
  { value: 'cursor', label: 'Cursor', fields: ['api_key'], type: 'api' },
  { value: 'figma', label: 'Figma', fields: ['access_token', 'org_id'], type: 'api' },
  { value: 'github', label: 'GitHub', fields: ['access_token', 'org_name'], type: 'api' },
  { value: 'gitlab', label: 'GitLab', fields: ['access_token', 'group_id', 'base_url'], type: 'api' },
  { value: 'google_workspace', label: 'Google Workspace', fields: ['service_account_json', 'admin_email', 'domain'], type: 'api' },
  { value: 'jetbrains', label: 'JetBrains', fields: ['api_key', 'customer_code'], type: 'api' },
  { value: 'mattermost', label: 'Mattermost', fields: ['access_token', 'server_url'], type: 'api' },
  { value: 'microsoft', label: 'Microsoft 365 / Azure AD', fields: ['tenant_id', 'client_id', 'client_secret'], type: 'api' },
  { value: 'miro', label: 'Miro', fields: ['access_token', 'org_id'], type: 'api' },
  { value: 'openai', label: 'OpenAI', fields: ['admin_api_key', 'org_id'], type: 'api' },
  { value: 'slack', label: 'Slack', fields: ['bot_token', 'user_token'], type: 'api' },
  { value: 'manual', label: 'Manual (No API)', fields: [], type: 'manual' },
];

const licenseModelOptions = [
  { value: 'seat_based', label: 'Seat-based (per user)' },
  { value: 'license_based', label: 'License-based (transferable)' },
];

// Custom labels for credential fields
const FIELD_LABELS: Record<string, string> = {
  access_token: 'Access Token',
  admin_api_key: 'Admin API Key',
  admin_email: 'Admin Email',
  api_key: 'API Key',
  api_token: 'API Token',
  auth_token: 'Auth Token',
  base_url: 'Server URL (optional, for self-hosted)',
  bot_token: 'Bot Token',
  client_id: 'Application (Client) ID',
  client_secret: 'Client Secret',
  customer_code: 'Organization ID (X-Customer-Code)',
  domain: 'Domain',
  group_id: 'Group ID',
  org_id: 'Organization ID',
  org_name: 'Organization Name',
  server_url: 'Server URL',
  service_account_json: 'Service Account JSON',
  sign_in_address: 'Sign-in Address',
  tenant_id: 'Tenant ID',
  user_token: 'User Token',
};

// Permission hints for providers
const PROVIDER_PERMISSIONS: Record<string, string[]> = {
  '1password': [
    'SCIM bridge token required',
    'Enable SCIM provisioning in 1Password admin console',
  ],
  github: [
    'read:org - Read org and team membership',
    'read:user - Read user profile data',
  ],
  gitlab: [
    'read_api - Read access to the API',
    'read_user - Read user information',
  ],
  mattermost: [
    'Personal access token or bot token',
    'System Admin role recommended for full user list',
  ],
  microsoft: [
    'User.Read.All (Application)',
    'Directory.Read.All (Application)',
    'AuditLog.Read.All (Application) - for sign-in activity',
  ],
  miro: [
    'OAuth access token with team:read scope',
    'Organization ID required for Enterprise plans',
  ],
};

const getFieldLabel = (field: string) => {
  return FIELD_LABELS[field] || field.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
};

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingProvider, setDeletingProvider] = useState<Provider | null>(null);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [dialogMode, setDialogMode] = useState<'hris' | 'license'>('license');
  const [newProviderType, setNewProviderType] = useState('');
  const [newProviderName, setNewProviderName] = useState('');
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [manualConfig, setManualConfig] = useState({
    license_model: 'license_based',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncingProviderId, setSyncingProviderId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchProviders();
  }, []);

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  };

  async function fetchProviders() {
    try {
      const data = await api.getProviders();
      setProviders(data.items);
    } catch (error) {
      console.error('Failed to fetch providers:', error);
    } finally {
      setLoading(false);
    }
  }

  const hrisProviders = providers.filter((p) => p.name === 'hibob');
  const licenseProviders = providers.filter((p) => p.name !== 'hibob').sort((a, b) => a.display_name.localeCompare(b.display_name));

  const getProviderFields = (providerName: string) => {
    if (providerName === 'hibob') return hrisProvider.fields;
    return licenseProviderTypes.find((p) => p.value === providerName)?.fields || [];
  };

  const handleOpenAddDialog = (mode: 'hris' | 'license') => {
    setDialogMode(mode);
    setNewProviderType(mode === 'hris' ? 'hibob' : '');
    setNewProviderName('');
    setCredentials({});
    setManualConfig({
      license_model: 'license_based',
    });
    setError(null);
    setAddDialogOpen(true);
  };

  const isManualProvider = (providerType: string) => providerType === 'manual';

  const handleOpenEditDialog = (provider: Provider) => {
    setEditingProvider(provider);
    setNewProviderName(provider.display_name);
    setCredentials({});
    setError(null);
    setEditDialogOpen(true);
  };

  const handleAddProvider = async () => {
    setSaving(true);
    setError(null);
    try {
      const providerType = dialogMode === 'hris' ? 'hibob' : newProviderType;
      const isManual = isManualProvider(providerType);

      const config: Record<string, any> = {};
      if (isManual) {
        config.provider_type = 'manual';
        config.license_model = manualConfig.license_model;
      }

      await api.createProvider({
        name: providerType,
        display_name: newProviderName,
        credentials: isManual ? {} : credentials,
        config: Object.keys(config).length > 0 ? config : undefined,
      });
      await fetchProviders();
      setAddDialogOpen(false);
      showToast('success', `${newProviderName} added`);
    } catch (err: any) {
      setError(err.message || 'Failed to add provider');
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateProvider = async () => {
    if (!editingProvider) return;
    setSaving(true);
    setError(null);
    try {
      const updates: { display_name?: string; credentials?: Record<string, string> } = {
        display_name: newProviderName,
      };
      // Only include credentials if any were changed
      const hasCredentials = Object.values(credentials).some((v) => v);
      if (hasCredentials) {
        updates.credentials = credentials;
      }
      await api.updateProvider(editingProvider.id, updates);
      await fetchProviders();
      setEditDialogOpen(false);
      showToast('success', 'Provider updated');
    } catch (err: any) {
      setError(err.message || 'Failed to update provider');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteProvider = async () => {
    if (!deletingProvider) return;
    try {
      await api.deleteProvider(deletingProvider.id);
      await fetchProviders();
      setDeleteDialogOpen(false);
      setDeletingProvider(null);
      showToast('success', 'Provider deleted');
    } catch (err: any) {
      showToast('error', err.message || 'Failed to delete provider');
    }
  };

  const handleSyncProvider = async (providerId: string) => {
    setSyncingProviderId(providerId);
    try {
      const result = await api.syncProvider(providerId);
      await fetchProviders();
      showToast(result.success ? 'success' : 'error', result.success ? 'Sync completed' : 'Sync failed');
    } catch (err: any) {
      showToast('error', err.message || 'Sync failed');
    } finally {
      setSyncingProviderId(null);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-8">
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
        <div className="pt-2">
          <h1 className="text-2xl font-semibold tracking-tight">Providers</h1>
          <p className="text-muted-foreground text-sm mt-0.5">Manage HRIS and license provider integrations</p>
        </div>

        {/* HRIS Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">HRIS Connection</h2>
            </div>
            {hrisProviders.length === 0 && (
              <Button size="sm" variant="outline" onClick={() => handleOpenAddDialog('hris')}>
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                Connect HiBob
              </Button>
            )}
          </div>

          {hrisProviders.length > 0 ? (
            <div className="border rounded-lg bg-white">
              {hrisProviders.map((provider) => (
                <div key={provider.id} className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-blue-50 flex items-center justify-center">
                      <Users className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{provider.display_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {provider.last_sync_at ? `Last sync: ${new Date(provider.last_sync_at).toLocaleString('de-DE')}` : 'Never synced'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 border-0">Connected</Badge>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleSyncProvider(provider.id)} disabled={syncingProviderId === provider.id}>
                      <RefreshCw className={`h-4 w-4 ${syncingProviderId === provider.id ? 'animate-spin' : ''}`} />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpenEditDialog(provider)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700" onClick={() => { setDeletingProvider(provider); setDeleteDialogOpen(true); }}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="border rounded-lg bg-zinc-50/50 p-8 text-center">
              <Users className="h-8 w-8 mx-auto mb-2 text-zinc-300" />
              <p className="text-sm text-muted-foreground">Connect HiBob to sync employee data</p>
            </div>
          )}
        </section>

        {/* License Providers Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Key className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">License Providers</h2>
            </div>
            <Button size="sm" variant="outline" onClick={() => handleOpenAddDialog('license')}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              Add Provider
            </Button>
          </div>

          {licenseProviders.length > 0 ? (
            <div className="border rounded-lg bg-white divide-y">
              {licenseProviders.map((provider) => {
                const isManual = provider.config?.provider_type === 'manual' || provider.name === 'manual';
                return (
                  <Link key={provider.id} href={`/providers/${provider.id}`}>
                    <div className="flex items-center justify-between p-4 hover:bg-zinc-50 transition-colors cursor-pointer">
                      <div className="flex items-center gap-3">
                        <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${isManual ? 'bg-purple-50' : 'bg-zinc-100'}`}>
                          {isManual ? <Package className="h-4 w-4 text-purple-600" /> : <Key className="h-4 w-4 text-zinc-600" />}
                        </div>
                        <div>
                          <p className="font-medium text-sm">{provider.display_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {provider.license_count} license{provider.license_count !== 1 ? 's' : ''}
                            {!isManual && provider.last_sync_at && ` · ${new Date(provider.last_sync_at).toLocaleDateString('de-DE')}`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className={isManual ? 'bg-purple-50 text-purple-700 border-0' : provider.enabled ? 'bg-emerald-50 text-emerald-700 border-0' : ''}>
                          {isManual ? 'Manual' : provider.enabled ? 'Active' : 'Disabled'}
                        </Badge>
                        {!isManual && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={(e) => { e.preventDefault(); handleSyncProvider(provider.id); }}
                            disabled={syncingProviderId === provider.id}
                          >
                            <RefreshCw className={`h-4 w-4 ${syncingProviderId === provider.id ? 'animate-spin' : ''}`} />
                          </Button>
                        )}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          ) : (
            <div className="border rounded-lg bg-zinc-50/50 p-8 text-center">
              <Key className="h-8 w-8 mx-auto mb-2 text-zinc-300" />
              <p className="text-sm text-muted-foreground">No license providers configured</p>
            </div>
          )}
        </section>

      </div>

      {/* Add Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialogMode === 'hris' ? 'Connect HRIS' : 'Add Provider'}</DialogTitle>
            <DialogDescription>
              {dialogMode === 'hris' ? 'Connect HiBob to sync employee data' : 'Add a new license provider'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            {dialogMode === 'license' && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">Provider Type</Label>
                <Select value={newProviderType} onValueChange={setNewProviderType}>
                  <SelectTrigger><SelectValue placeholder="Select provider" /></SelectTrigger>
                  <SelectContent>
                    {licenseProviderTypes.map((t) => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-2">
              <Label className="text-xs font-medium">Display Name</Label>
              <Input value={newProviderName} onChange={(e) => setNewProviderName(e.target.value)} placeholder={dialogMode === 'hris' ? 'HiBob' : 'e.g., Google Workspace'} />
            </div>
            {/* API Provider Fields */}
            {!isManualProvider(newProviderType) && getProviderFields(newProviderType).map((field) => (
              <div key={field} className="space-y-2">
                <Label className="text-xs font-medium">{getFieldLabel(field)}</Label>
                <Input
                  type={field.includes('key') || field.includes('token') || field.includes('secret') ? 'password' : 'text'}
                  value={credentials[field] || ''}
                  onChange={(e) => setCredentials({ ...credentials, [field]: e.target.value })}
                />
              </div>
            ))}
            {/* Permission hints */}
            {PROVIDER_PERMISSIONS[newProviderType] && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                <p className="text-xs font-medium text-blue-800 mb-1">Required Permissions:</p>
                <ul className="text-xs text-blue-700 space-y-0.5">
                  {PROVIDER_PERMISSIONS[newProviderType].map((perm) => (
                    <li key={perm}>• {perm}</li>
                  ))}
                </ul>
                {newProviderType === 'microsoft' && (
                  <p className="text-xs text-blue-600 mt-2">
                    Grant these permissions in Azure Portal → App registrations → API permissions → Add permission → Microsoft Graph
                  </p>
                )}
              </div>
            )}
            {/* Manual Provider Fields */}
            {isManualProvider(newProviderType) && (
              <>
                <div className="space-y-2">
                  <Label className="text-xs font-medium">License Model</Label>
                  <Select value={manualConfig.license_model} onValueChange={(v) => setManualConfig({ ...manualConfig, license_model: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {licenseModelOptions.map((o) => (
                        <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <p className="text-xs text-muted-foreground">
                  After creating the provider, you can add license keys or seats and configure pricing in the Pricing tab.
                </p>
              </>
            )}
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAddDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAddProvider} disabled={!newProviderType || !newProviderName || saving}>
              {saving ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Adding...</> : 'Add Provider'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Provider</DialogTitle>
            <DialogDescription>Update settings. Leave credentials empty to keep current values.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-xs font-medium">Display Name</Label>
              <Input value={newProviderName} onChange={(e) => setNewProviderName(e.target.value)} />
            </div>
            {editingProvider && getProviderFields(editingProvider.name).map((field) => (
              <div key={field} className="space-y-2">
                <Label className="text-xs font-medium">{getFieldLabel(field)}</Label>
                <Input
                  type={field.includes('key') || field.includes('token') || field.includes('secret') ? 'password' : 'text'}
                  value={credentials[field] || ''}
                  onChange={(e) => setCredentials({ ...credentials, [field]: e.target.value })}
                  placeholder="Leave empty to keep current"
                />
              </div>
            ))}
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleUpdateProvider} disabled={!newProviderName || saving}>
              {saving ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Saving...</> : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Provider</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deletingProvider?.display_name}</strong>? All associated licenses will be removed. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteProvider}>Delete Provider</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
