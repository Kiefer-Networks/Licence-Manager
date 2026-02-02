'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
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
import { handleSilentError } from '@/lib/error-handler';
import { Plus, Pencil, Trash2, RefreshCw, Users, Key, CheckCircle2, XCircle, Loader2, Building2, Package, AlertTriangle, Upload, X } from 'lucide-react';
import Link from 'next/link';
import { useLocale } from '@/components/locale-provider';

const hrisProviderTypes = [
  { value: 'hibob', label: 'HiBob', fields: ['auth_token'] },
  { value: 'personio', label: 'Personio', fields: ['client_id', 'client_secret'] },
];

const licenseProviderTypes = [
  { value: '1password', label: '1Password', fields: ['api_token', 'sign_in_address'], type: 'api' },
  { value: 'adobe', label: 'Adobe Creative Cloud', fields: ['client_id', 'client_secret', 'org_id', 'technical_account_id'], type: 'api' },
  { value: 'anthropic', label: 'Anthropic (Claude)', fields: ['admin_api_key'], type: 'api' },
  { value: 'atlassian', label: 'Atlassian (Confluence/Jira)', fields: ['api_token', 'org_id', 'admin_email'], type: 'api' },
  { value: 'auth0', label: 'Auth0', fields: ['domain', 'client_id', 'client_secret'], type: 'api' },
  { value: 'cursor', label: 'Cursor', fields: ['api_key'], type: 'api' },
  { value: 'figma', label: 'Figma', fields: ['access_token', 'org_id'], type: 'api' },
  { value: 'github', label: 'GitHub', fields: ['access_token', 'org_name'], type: 'api' },
  { value: 'gitlab', label: 'GitLab', fields: ['access_token', 'group_id', 'base_url'], type: 'api' },
  { value: 'google_workspace', label: 'Google Workspace', fields: ['service_account_json', 'admin_email', 'domain'], type: 'api' },
  { value: 'jetbrains', label: 'JetBrains', fields: ['api_key', 'customer_code'], type: 'api' },
  { value: 'mailjet', label: 'Mailjet', fields: ['api_key', 'api_secret'], type: 'api' },
  { value: 'mattermost', label: 'Mattermost', fields: ['access_token', 'server_url'], type: 'api' },
  { value: 'microsoft', label: 'Microsoft 365 / Azure AD', fields: ['tenant_id', 'client_id', 'client_secret'], type: 'api' },
  { value: 'miro', label: 'Miro', fields: ['access_token', 'org_id'], type: 'api' },
  { value: 'openai', label: 'OpenAI', fields: ['admin_api_key', 'org_id'], type: 'api' },
  { value: 'slack', label: 'Slack', fields: ['bot_token', 'user_token'], type: 'api' },
  { value: 'zoom', label: 'Zoom', fields: ['account_id', 'client_id', 'client_secret'], type: 'api' },
  { value: 'manual', label: 'manual', fields: [], type: 'manual' },
];

// Keys for translatable credential field labels
const FIELD_LABEL_KEYS: Record<string, string> = {
  account_id: 'accountId',
  access_token: 'accessToken',
  admin_api_key: 'adminApiKey',
  admin_email: 'adminEmail',
  api_key: 'apiKey',
  api_secret: 'apiSecret',
  api_token: 'apiToken',
  auth_token: 'authToken',
  base_url: 'baseUrl',
  bot_token: 'botToken',
  client_id: 'clientId',
  client_secret: 'clientSecret',
  customer_code: 'customerCode',
  domain: 'domainField',
  group_id: 'groupId',
  org_id: 'orgId',
  org_name: 'orgName',
  server_url: 'serverUrl',
  service_account_json: 'serviceAccountJson',
  sign_in_address: 'signInAddress',
  technical_account_id: 'technicalAccountId',
  tenant_id: 'tenantId',
  user_token: 'userToken',
};

// Documentation links for providers (not translated)
const PROVIDER_LINKS: Record<string, string> = {
  '1password': 'https://support.1password.com/scim/',
  adobe: 'https://developer.adobe.com/developer-console/docs/guides/services/services-add-api-oauth-s2s/',
  atlassian: 'https://support.atlassian.com/organization-administration/docs/manage-an-organization-with-the-admin-apis/',
  cursor: 'https://cursor.sh/settings/team',
  figma: 'https://www.figma.com/developers/api#access-tokens',
  github: 'https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens',
  gitlab: 'https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html',
  google_workspace: 'https://developers.google.com/admin-sdk/directory/v1/guides/delegation',
  hibob: 'https://apidocs.hibob.com/reference/getting-started',
  personio: 'https://developer.personio.de/docs/getting-started-with-the-personio-api',
  jetbrains: 'https://sales.jetbrains.com/hc/en-gb/articles/207240845-What-is-a-Customer-Code-',
  mattermost: 'https://developers.mattermost.com/integrate/reference/personal-access-token/',
  microsoft: 'https://learn.microsoft.com/en-us/graph/auth-register-app-v2',
  miro: 'https://developers.miro.com/docs/getting-started',
  openai: 'https://platform.openai.com/docs/api-reference/organization',
  slack: 'https://api.slack.com/authentication/basics',
  anthropic: 'https://docs.anthropic.com/en/api/admin-api',
  auth0: 'https://auth0.com/docs/api/management/v2',
  mailjet: 'https://dev.mailjet.com/email/guides/getting-started/',
  zoom: 'https://developers.zoom.us/docs/internal-apps/',
};

// Provider types that have setup instructions
const PROVIDERS_WITH_SETUP = [
  '1password', 'adobe', 'atlassian', 'cursor', 'figma', 'github', 'gitlab',
  'google_workspace', 'hibob', 'jetbrains', 'mattermost', 'microsoft',
  'miro', 'openai', 'personio', 'slack', 'anthropic', 'auth0', 'mailjet', 'zoom'
];

const getFieldLabel = (field: string, t: (key: string) => string) => {
  const key = FIELD_LABEL_KEYS[field];
  if (key) {
    return t(key);
  }
  return field.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
};

export default function ProvidersPage() {
  const t = useTranslations('providers');
  const tCommon = useTranslations('common');
  const tLicenses = useTranslations('licenses');
  const tSetup = useTranslations('providerSetup');
  const { formatDate } = useLocale();
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
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncingProviderId, setSyncingProviderId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchProviders();
  }, []);

  // Clear sensitive credentials on unmount to prevent memory exposure
  useEffect(() => {
    return () => {
      setCredentials({});
    };
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
      handleSilentError('fetchProviders', error);
    } finally {
      setLoading(false);
    }
  }

  const hrisProviderNames = hrisProviderTypes.map((p) => p.value);
  const hrisProviders = providers.filter((p) => hrisProviderNames.includes(p.name));
  const licenseProviders = providers.filter((p) => !hrisProviderNames.includes(p.name)).sort((a, b) => a.display_name.localeCompare(b.display_name));

  const getProviderFields = (providerName: string) => {
    const hrisType = hrisProviderTypes.find((p) => p.value === providerName);
    if (hrisType) return hrisType.fields;
    return licenseProviderTypes.find((p) => p.value === providerName)?.fields || [];
  };

  const handleOpenAddDialog = (mode: 'hris' | 'license') => {
    setDialogMode(mode);
    setNewProviderType('');
    setNewProviderName('');
    setCredentials({});
    setManualConfig({
      license_model: 'license_based',
    });
    setLogoFile(null);
    setLogoPreview(null);
    setError(null);
    setAddDialogOpen(true);
  };

  const isManualProvider = (providerType: string) => providerType === 'manual';

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setLogoFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setLogoPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const clearLogo = () => {
    setLogoFile(null);
    setLogoPreview(null);
  };

  const handleOpenEditDialog = (provider: Provider) => {
    setEditingProvider(provider);
    setNewProviderName(provider.display_name);
    setCredentials({});
    setLogoFile(null);
    setLogoPreview(provider.logo_url || null);
    setError(null);
    setEditDialogOpen(true);
  };

  const handleAddProvider = async () => {
    setSaving(true);
    setError(null);
    try {
      const providerType = newProviderType;
      const isManual = isManualProvider(providerType);

      const config: { provider_type?: string; license_model?: string } = {};
      if (isManual) {
        config.provider_type = 'manual';
        config.license_model = manualConfig.license_model;
      }

      const newProvider = await api.createProvider({
        name: providerType,
        display_name: newProviderName,
        credentials: isManual ? {} : credentials,
        config: Object.keys(config).length > 0 ? config : undefined,
      });

      // Upload logo if provided (for manual providers)
      // Logo upload failure is non-critical - provider was created successfully
      if (isManual && logoFile) {
        try {
          await api.uploadProviderLogo(newProvider.id, logoFile);
        } catch {
          // Logo upload failed but provider was created - continue silently
        }
      }

      await fetchProviders();
      setAddDialogOpen(false);
      showToast('success', `${newProviderName} added`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('failedToCreate'));
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

      // Upload logo if a new file was selected (for manual providers)
      // Logo upload failure is non-critical - provider was updated successfully
      const isManual = editingProvider.config?.provider_type === 'manual' || editingProvider.name === 'manual';
      if (isManual && logoFile) {
        try {
          await api.uploadProviderLogo(editingProvider.id, logoFile);
        } catch {
          // Logo upload failed but provider was updated - continue silently
        }
      }

      await fetchProviders();
      setEditDialogOpen(false);
      showToast('success', t('providerUpdated'));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('failedToUpdate'));
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
      showToast('success', t('providerDeleted'));
    } catch (err) {
      showToast('error', err instanceof Error ? err.message : t('failedToDelete'));
    }
  };

  const handleSyncProvider = async (providerId: string) => {
    setSyncingProviderId(providerId);
    try {
      const result = await api.syncProvider(providerId);
      await fetchProviders();
      showToast(result.success ? 'success' : 'error', result.success ? t('syncSuccess') : t('syncFailed'));
    } catch (err) {
      showToast('error', err instanceof Error ? err.message : t('syncFailed'));
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
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{t('pageDescription')}</p>
        </div>

        {/* HRIS Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('hrisConnection')}</h2>
            </div>
            {hrisProviders.length === 0 && (
              <Button size="sm" variant="outline" onClick={() => handleOpenAddDialog('hris')}>
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                {t('connectHris')}
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
                        {provider.last_sync_at ? t('lastSyncTime', { time: formatDate(provider.last_sync_at) }) : t('neverSynced')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 border-0">{t('connected')}</Badge>
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
              <p className="text-sm text-muted-foreground">{t('connectHiBobDescription')}</p>
            </div>
          )}
        </section>

        {/* License Providers Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Key className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('licenseProvidersSection')}</h2>
            </div>
            <Button size="sm" variant="outline" onClick={() => handleOpenAddDialog('license')}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              {t('addProvider')}
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
                        {provider.logo_url ? (
                          <img
                            src={provider.logo_url}
                            alt={provider.display_name}
                            className="h-9 w-9 rounded-lg object-contain bg-white border p-1"
                          />
                        ) : (
                          <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${isManual ? 'bg-purple-50' : 'bg-zinc-100'}`}>
                            {isManual ? <Package className="h-4 w-4 text-purple-600" /> : <Key className="h-4 w-4 text-zinc-600" />}
                          </div>
                        )}
                        <div>
                          <p className="font-medium text-sm">{provider.display_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {provider.license_stats ? (
                              <>
                                <span className="font-medium text-zinc-700">{provider.license_stats.active} {tLicenses('active').toLowerCase()}</span>
                                {' · '}
                                {provider.license_stats.assigned} {tLicenses('assigned').toLowerCase()}
                                {provider.license_stats.external > 0 && (
                                  <span className="text-orange-600"> + {provider.license_stats.external} {tLicenses('ext')}</span>
                                )}
                                {provider.license_stats.not_in_hris > 0 && (
                                  <span className="text-red-600 inline-flex items-center gap-0.5"> + {provider.license_stats.not_in_hris} <AlertTriangle className="h-3 w-3" /> {tLicenses('notInHRISShort')}</span>
                                )}
                              </>
                            ) : (
                              <>{tLicenses('licenseCount', { count: provider.license_count })}</>
                            )}
                            {!isManual && provider.last_sync_at && ` · ${formatDate(provider.last_sync_at)}`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className={isManual ? 'bg-purple-50 text-purple-700 border-0' : provider.enabled ? 'bg-emerald-50 text-emerald-700 border-0' : ''}>
                          {isManual ? t('manual') : provider.enabled ? t('active') : t('disabled')}
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
              <p className="text-sm text-muted-foreground">{t('noLicenseProviders')}</p>
            </div>
          )}
        </section>

      </div>

      {/* Add Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{dialogMode === 'hris' ? t('connectHris') : t('addProvider')}</DialogTitle>
            <DialogDescription>
              {dialogMode === 'hris' ? t('connectHrisDescription') : t('addNewLicenseProvider')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2 overflow-y-auto flex-1">
            {/* Provider Type Selection */}
            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('providerType')}</Label>
              <Select value={newProviderType} onValueChange={setNewProviderType}>
                <SelectTrigger><SelectValue placeholder={t('selectProviderType')} /></SelectTrigger>
                <SelectContent>
                  {dialogMode === 'hris' ? (
                    hrisProviderTypes.map((pt) => (
                      <SelectItem key={pt.value} value={pt.value}>
                        {t(pt.value)}
                      </SelectItem>
                    ))
                  ) : (
                    licenseProviderTypes.map((pt) => (
                      <SelectItem key={pt.value} value={pt.value}>
                        {pt.value === 'manual' ? t('manualNoApi') : t(pt.value)}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('displayName')}</Label>
              <Input value={newProviderName} onChange={(e) => setNewProviderName(e.target.value)} placeholder={newProviderType ? t(newProviderType) : t('displayNamePlaceholder')} />
            </div>
            {/* API Provider Fields */}
            {!isManualProvider(newProviderType) && getProviderFields(newProviderType).map((field) => (
              <div key={field} className="space-y-2">
                <Label className="text-xs font-medium">{getFieldLabel(field, t)}</Label>
                <Input
                  type={field.includes('key') || field.includes('token') || field.includes('secret') ? 'password' : 'text'}
                  value={credentials[field] || ''}
                  onChange={(e) => setCredentials({ ...credentials, [field]: e.target.value })}
                />
              </div>
            ))}
            {/* Setup Instructions */}
            {PROVIDERS_WITH_SETUP.includes(newProviderType) && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3 space-y-3">
                <div>
                  <p className="text-xs font-medium text-blue-800 mb-1">{t('requiredPermissions')}</p>
                  <ul className="text-xs text-blue-700 space-y-0.5">
                    {(tSetup.raw(`${newProviderType}.permissions`) as string[]).map((perm) => (
                      <li key={perm}>• {perm}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-medium text-blue-800 mb-1">{t('setupSteps')}</p>
                  <ol className="text-xs text-blue-700 space-y-0.5">
                    {(tSetup.raw(`${newProviderType}.steps`) as string[]).map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ol>
                </div>
                {PROVIDER_LINKS[newProviderType] && (
                  <a
                    href={PROVIDER_LINKS[newProviderType]}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:text-blue-800 underline inline-flex items-center gap-1"
                  >
                    {t('viewDocumentation')}
                  </a>
                )}
              </div>
            )}
            {/* Manual Provider Fields */}
            {isManualProvider(newProviderType) && (
              <>
                <div className="space-y-2">
                  <Label className="text-xs font-medium">{t('licenseModel')}</Label>
                  <Select value={manualConfig.license_model} onValueChange={(v) => setManualConfig({ ...manualConfig, license_model: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="seat_based">{t('seatBased')}</SelectItem>
                      <SelectItem value="license_based">{t('licenseBased')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-medium">{t('logoOptional')}</Label>
                  <div className="flex items-center gap-3">
                    {logoPreview ? (
                      <div className="relative">
                        <img src={logoPreview} alt={t('logoPreview')} className="h-12 w-12 rounded-lg object-contain border bg-white p-1" />
                        <button
                          type="button"
                          onClick={clearLogo}
                          className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-0.5 hover:bg-red-600"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ) : (
                      <div className="h-12 w-12 rounded-lg border-2 border-dashed border-zinc-200 flex items-center justify-center">
                        <Package className="h-5 w-5 text-zinc-300" />
                      </div>
                    )}
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        accept=".png,.jpg,.jpeg,.svg,.webp"
                        onChange={handleLogoChange}
                        className="hidden"
                      />
                      <span className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1">
                        <Upload className="h-3 w-3" />
                        {logoPreview ? t('change') : tCommon('upload')}
                      </span>
                    </label>
                  </div>
                  <p className="text-xs text-muted-foreground">{t('logoFormats')}</p>
                </div>
                <p className="text-xs text-muted-foreground">
                  {t('manualProviderNote')}
                </p>
              </>
            )}
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAddDialogOpen(false)}>{tCommon('cancel')}</Button>
            <Button onClick={handleAddProvider} disabled={!newProviderType || !newProviderName || saving}>
              {saving ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> {t('adding')}</> : t('addProvider')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('editProvider')}</DialogTitle>
            <DialogDescription>{t('editDescription')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('displayName')}</Label>
              <Input value={newProviderName} onChange={(e) => setNewProviderName(e.target.value)} />
            </div>
            {editingProvider && getProviderFields(editingProvider.name).map((field) => (
              <div key={field} className="space-y-2">
                <Label className="text-xs font-medium">{getFieldLabel(field, t)}</Label>
                <Input
                  type={field.includes('key') || field.includes('token') || field.includes('secret') ? 'password' : 'text'}
                  value={credentials[field] || ''}
                  onChange={(e) => setCredentials({ ...credentials, [field]: e.target.value })}
                  placeholder={t('leaveEmptyToKeep')}
                />
              </div>
            ))}
            {/* Logo upload for manual providers */}
            {editingProvider && (editingProvider.config?.provider_type === 'manual' || editingProvider.name === 'manual') && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('logo')}</Label>
                <div className="flex items-center gap-3">
                  {logoPreview ? (
                    <div className="relative">
                      <img src={logoPreview} alt={t('logoPreview')} className="h-12 w-12 rounded-lg object-contain border bg-white p-1" />
                      <button
                        type="button"
                        onClick={clearLogo}
                        className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-0.5 hover:bg-red-600"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ) : (
                    <div className="h-12 w-12 rounded-lg border-2 border-dashed border-zinc-200 flex items-center justify-center">
                      <Package className="h-5 w-5 text-zinc-300" />
                    </div>
                  )}
                  <label className="cursor-pointer">
                    <input
                      type="file"
                      accept=".png,.jpg,.jpeg,.svg,.webp"
                      onChange={handleLogoChange}
                      className="hidden"
                    />
                    <span className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1">
                      <Upload className="h-3 w-3" />
                      {logoPreview ? t('changeLogo') : tCommon('upload')}
                    </span>
                  </label>
                </div>
                <p className="text-xs text-muted-foreground">{t('logoFormats')}</p>
              </div>
            )}
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditDialogOpen(false)}>{tCommon('cancel')}</Button>
            <Button onClick={handleUpdateProvider} disabled={!newProviderName || saving}>
              {saving ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> {t('saving')}</> : t('saveChanges')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('deleteProvider')}</DialogTitle>
            <DialogDescription>
              {t('deleteConfirmation', { name: deletingProvider?.display_name || '' })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteDialogOpen(false)}>{tCommon('cancel')}</Button>
            <Button variant="destructive" onClick={handleDeleteProvider}>{t('deleteProvider')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
