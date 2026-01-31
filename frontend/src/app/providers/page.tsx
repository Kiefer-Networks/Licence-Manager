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
import { getLocale } from '@/lib/locale';

const hrisProvider = { value: 'hibob', label: 'HiBob', fields: ['auth_token'] };

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
  api_secret: 'API Secret',
  api_token: 'API Token',
  auth_token: 'Auth Token',
  base_url: 'Server URL (optional, for self-hosted)',
  bot_token: 'Bot Token',
  client_id: 'Client ID',
  client_secret: 'Client Secret',
  customer_code: 'Organization ID (X-Customer-Code)',
  domain: 'Domain (e.g., your-tenant.auth0.com)',
  group_id: 'Group ID',
  org_id: 'Organization ID',
  org_name: 'Organization Name',
  server_url: 'Server URL',
  service_account_json: 'Service Account JSON',
  sign_in_address: 'Sign-in Address',
  technical_account_id: 'Technical Account ID',
  tenant_id: 'Tenant ID',
  user_token: 'User Token',
};

// Detailed setup instructions for providers
const PROVIDER_SETUP: Record<string, { permissions: string[]; steps: string[]; link?: string }> = {
  '1password': {
    permissions: [
      'SCIM bridge token with full provisioning access',
    ],
    steps: [
      '1. Log in to 1Password Business/Teams admin console',
      '2. Go to Integrations → Directory',
      '3. Click "Set up SCIM bridge"',
      '4. Generate a new SCIM bearer token',
      '5. Copy the Sign-in Address (e.g., company.1password.com)',
      '6. Save the bearer token securely - it cannot be viewed again',
    ],
    link: 'https://support.1password.com/scim/',
  },
  adobe: {
    permissions: [
      'User Management API access',
      'Service Account (Server-to-Server) credentials',
    ],
    steps: [
      '1. Go to Adobe Developer Console (developer.adobe.com)',
      '2. Create a new project or select existing',
      '3. Add API → User Management API',
      '4. Select OAuth Server-to-Server credential',
      '5. Copy the Client ID and Client Secret',
      '6. Find Organization ID: Admin Console → Overview',
      '7. Technical Account ID: Found in credential details',
      '8. Ensure the integration has User Management admin role',
    ],
    link: 'https://developer.adobe.com/developer-console/docs/guides/services/services-add-api-oauth-s2s/',
  },
  atlassian: {
    permissions: [
      'Organization admin access',
      'API token with admin privileges',
    ],
    steps: [
      '1. Go to admin.atlassian.com',
      '2. Select your organization',
      '3. Go to Settings → API keys',
      '4. Click "Create API key"',
      '5. Name it (e.g., "License Management")',
      '6. Copy the API key immediately - it cannot be viewed again',
      '7. Find Organization ID: Settings → Organization details',
      '8. Admin Email: Your Atlassian admin account email',
    ],
    link: 'https://support.atlassian.com/organization-administration/docs/manage-an-organization-with-the-admin-apis/',
  },
  cursor: {
    permissions: [
      'Team Admin API Key with member management access',
    ],
    steps: [
      '1. Log in to Cursor as a Team Admin',
      '2. Go to Team Settings → API',
      '3. Generate a new API key',
      '4. Ensure Enterprise plan is active for full API access',
      '5. Copy the API key and store it securely',
    ],
    link: 'https://cursor.sh/settings/team',
  },
  figma: {
    permissions: [
      'org:read - Read organization and team info',
      'file:read - Optional for activity tracking',
    ],
    steps: [
      '1. Go to Figma → Account Settings → Personal Access Tokens',
      '2. Click "Create new token"',
      '3. Name it (e.g., "License Management")',
      '4. Select org:read scope (minimum required)',
      '5. Copy the token immediately - it won\'t be shown again',
      '6. Find Organization ID: Admin → Settings → Organization ID',
    ],
    link: 'https://www.figma.com/developers/api#access-tokens',
  },
  github: {
    permissions: [
      'read:org - Read organization and team membership',
      'read:user - Read user profile data',
      'admin:org (optional) - For seat management',
    ],
    steps: [
      '1. Go to GitHub → Settings → Developer settings → Personal access tokens',
      '2. Click "Generate new token (classic)"',
      '3. Select scopes: read:org, read:user',
      '4. For Enterprise: use admin:org for seat counts',
      '5. Copy the token and store securely',
      '6. Organization name: your GitHub org slug (github.com/ORG_NAME)',
    ],
    link: 'https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens',
  },
  gitlab: {
    permissions: [
      'read_api - Read access to the API',
      'read_user - Read user information',
    ],
    steps: [
      '1. Go to GitLab → User Settings → Access Tokens',
      '2. Create a new Personal Access Token',
      '3. Select scopes: read_api, read_user',
      '4. Set expiration date (recommended: 1 year)',
      '5. Copy the token immediately',
      '6. Group ID: Go to your group → Settings → General → Group ID',
      '7. For self-hosted: Enter your GitLab server URL',
    ],
    link: 'https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html',
  },
  google_workspace: {
    permissions: [
      'admin.directory.user.readonly - Read user directory',
      'admin.directory.group.readonly - Optional for groups',
    ],
    steps: [
      '1. Go to Google Cloud Console → Create new project',
      '2. Enable Admin SDK API',
      '3. Create Service Account with Domain-Wide Delegation',
      '4. Download the JSON key file',
      '5. In Google Admin: Security → API controls → Domain-wide delegation',
      '6. Add the Service Account client ID',
      '7. Add scope: https://www.googleapis.com/auth/admin.directory.user.readonly',
      '8. Admin Email: A super admin email for impersonation',
    ],
    link: 'https://developers.google.com/admin-sdk/directory/v1/guides/delegation',
  },
  hibob: {
    permissions: [
      'API Token with employee read access',
    ],
    steps: [
      '1. Log in to HiBob as Admin',
      '2. Go to Settings → Integrations → Service Users',
      '3. Create a new Service User',
      '4. Grant "People" read permissions',
      '5. Generate API token',
      '6. Copy the token - it cannot be retrieved later',
    ],
    link: 'https://apidocs.hibob.com/reference/getting-started',
  },
  jetbrains: {
    permissions: [
      'Organization API access with license management',
    ],
    steps: [
      '1. Go to JetBrains Account → Organization',
      '2. Navigate to API Keys section',
      '3. Generate new API key',
      '4. Find Organization ID (X-Customer-Code):',
      '   - Go to Organization → Settings',
      '   - Copy the Organization ID/Customer Code',
      '5. The API key provides access to license assignments',
    ],
    link: 'https://sales.jetbrains.com/hc/en-gb/articles/207240845-What-is-a-Customer-Code-',
  },
  mattermost: {
    permissions: [
      'Personal Access Token or Bot Token',
      'System Admin role recommended',
    ],
    steps: [
      '1. Go to Mattermost → Account Settings → Security',
      '2. Create a Personal Access Token',
      '3. For bot tokens: Integrations → Bot Accounts',
      '4. System Admin role provides full user list access',
      '5. Regular users may only see users in their teams',
      '6. Server URL: Your Mattermost instance URL (e.g., https://mattermost.company.com)',
    ],
    link: 'https://developers.mattermost.com/integrate/reference/personal-access-token/',
  },
  microsoft: {
    permissions: [
      'User.Read.All (Application) - Read all user profiles',
      'Directory.Read.All (Application) - Read directory data',
      'AuditLog.Read.All (Application) - Sign-in activity logs',
    ],
    steps: [
      '1. Go to Azure Portal → Azure Active Directory',
      '2. App registrations → New registration',
      '3. Name it (e.g., "License Management")',
      '4. Note the Application (Client) ID and Tenant ID',
      '5. Certificates & secrets → New client secret',
      '6. API permissions → Add permission → Microsoft Graph',
      '7. Add Application permissions:',
      '   - User.Read.All',
      '   - Directory.Read.All',
      '   - AuditLog.Read.All (optional, for activity)',
      '8. Click "Grant admin consent"',
    ],
    link: 'https://learn.microsoft.com/en-us/graph/auth-register-app-v2',
  },
  miro: {
    permissions: [
      'team:read - Read team and member information',
      'boards:read - Optional for activity tracking',
    ],
    steps: [
      '1. Go to Miro → Profile Settings → Your apps',
      '2. Create new app or use existing',
      '3. Install app to your team/organization',
      '4. Generate OAuth access token',
      '5. Required scope: team:read',
      '6. Organization ID: Admin → Organization settings → ID',
      '7. Enterprise plan required for organization-wide access',
    ],
    link: 'https://developers.miro.com/docs/getting-started',
  },
  openai: {
    permissions: [
      'Admin API Key with organization member access',
    ],
    steps: [
      '1. Go to platform.openai.com',
      '2. Click on your profile → Organization settings',
      '3. Note the Organization ID',
      '4. Go to API keys → Create new secret key',
      '5. You must be an Organization Owner to access member list',
      '6. The Admin API provides access to:',
      '   - Organization members',
      '   - Usage data',
      '   - Invite management',
    ],
    link: 'https://platform.openai.com/docs/api-reference/organization',
  },
  slack: {
    permissions: [
      'users:read - Access user list',
      'users:read.email - Access user emails',
      'team:read - Access workspace info',
      'team.billing:read - Optional: paid seat status',
    ],
    steps: [
      '1. Go to api.slack.com/apps → Create New App',
      '2. Choose "From scratch"',
      '3. Name it and select workspace',
      '4. OAuth & Permissions → Add Bot Token Scopes:',
      '   - users:read',
      '   - users:read.email',
      '   - team:read',
      '   - team.billing:read (optional, shows paid seats)',
      '5. Install App to Workspace',
      '6. Copy Bot User OAuth Token (starts with xoxb-)',
      '7. User Token (xoxp-) optional for additional access',
    ],
    link: 'https://api.slack.com/authentication/basics',
  },
  anthropic: {
    permissions: [
      'Admin API Key (starts with sk-ant-admin-)',
      'Organization owner or admin role',
    ],
    steps: [
      '1. Go to console.anthropic.com',
      '2. Navigate to Organization → API Keys',
      '3. Create an Admin API key (not a regular API key)',
      '4. Admin keys start with sk-ant-admin-',
      '5. You must be an Organization owner/admin',
      '6. Copy the key immediately - it cannot be viewed again',
    ],
    link: 'https://docs.anthropic.com/en/api/admin-api',
  },
  auth0: {
    permissions: [
      'Management API - read:users',
      'Management API - read:user_idp_tokens (optional)',
    ],
    steps: [
      '1. Go to Auth0 Dashboard → Applications → APIs',
      '2. Select "Auth0 Management API"',
      '3. Go to Machine to Machine Applications tab',
      '4. Authorize your app and select scopes:',
      '   - read:users',
      '   - read:user_idp_tokens (optional)',
      '5. Applications → Your App → Settings',
      '6. Copy Domain, Client ID, and Client Secret',
      '7. Domain format: your-tenant.auth0.com',
    ],
    link: 'https://auth0.com/docs/api/management/v2',
  },
  mailjet: {
    permissions: [
      'API Key with account access',
      'API Secret (private key)',
    ],
    steps: [
      '1. Go to app.mailjet.com → Account Settings',
      '2. Click on "REST API" → "API Key Management"',
      '3. Copy your API Key (public)',
      '4. Copy your Secret Key (private)',
      '5. Keys are created automatically with your account',
      '6. Master key has full access to all sub-accounts',
    ],
    link: 'https://dev.mailjet.com/email/guides/getting-started/',
  },
};

const getFieldLabel = (field: string) => {
  return FIELD_LABELS[field] || field.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
};

export default function ProvidersPage() {
  const t = useTranslations('providers');
  const tCommon = useTranslations('common');
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
      const providerType = dialogMode === 'hris' ? 'hibob' : newProviderType;
      const isManual = isManualProvider(providerType);

      const config: Record<string, any> = {};
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
      if (isManual && logoFile) {
        try {
          await api.uploadProviderLogo(newProvider.id, logoFile);
        } catch (logoErr) {
          console.error('Failed to upload logo:', logoErr);
        }
      }

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

      // Upload logo if a new file was selected (for manual providers)
      const isManual = editingProvider.config?.provider_type === 'manual' || editingProvider.name === 'manual';
      if (isManual && logoFile) {
        try {
          await api.uploadProviderLogo(editingProvider.id, logoFile);
        } catch (logoErr) {
          console.error('Failed to upload logo:', logoErr);
        }
      }

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
                        {provider.last_sync_at ? `Last sync: ${new Date(provider.last_sync_at).toLocaleString(getLocale())}` : 'Never synced'}
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
                                <span className="font-medium text-zinc-700">{provider.license_stats.active} active</span>
                                {' · '}
                                {provider.license_stats.assigned} assigned
                                {provider.license_stats.external > 0 && (
                                  <span className="text-orange-600"> + {provider.license_stats.external} ext</span>
                                )}
                                {provider.license_stats.not_in_hris > 0 && (
                                  <span className="text-red-600 inline-flex items-center gap-0.5"> + {provider.license_stats.not_in_hris} <AlertTriangle className="h-3 w-3" /> not in HRIS</span>
                                )}
                              </>
                            ) : (
                              <>{provider.license_count} license{provider.license_count !== 1 ? 's' : ''}</>
                            )}
                            {!isManual && provider.last_sync_at && ` · ${new Date(provider.last_sync_at).toLocaleDateString(getLocale())}`}
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
        <DialogContent className="max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{dialogMode === 'hris' ? 'Connect HRIS' : 'Add Provider'}</DialogTitle>
            <DialogDescription>
              {dialogMode === 'hris' ? 'Connect HiBob to sync employee data' : 'Add a new license provider'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2 overflow-y-auto flex-1">
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
            {/* Setup Instructions */}
            {PROVIDER_SETUP[newProviderType] && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3 space-y-3">
                <div>
                  <p className="text-xs font-medium text-blue-800 mb-1">Required Permissions:</p>
                  <ul className="text-xs text-blue-700 space-y-0.5">
                    {PROVIDER_SETUP[newProviderType].permissions.map((perm) => (
                      <li key={perm}>• {perm}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-medium text-blue-800 mb-1">Setup Steps:</p>
                  <ol className="text-xs text-blue-700 space-y-0.5">
                    {PROVIDER_SETUP[newProviderType].steps.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ol>
                </div>
                {PROVIDER_SETUP[newProviderType].link && (
                  <a
                    href={PROVIDER_SETUP[newProviderType].link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:text-blue-800 underline inline-flex items-center gap-1"
                  >
                    View documentation →
                  </a>
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
                <div className="space-y-2">
                  <Label className="text-xs font-medium">Logo (optional)</Label>
                  <div className="flex items-center gap-3">
                    {logoPreview ? (
                      <div className="relative">
                        <img src={logoPreview} alt="Logo preview" className="h-12 w-12 rounded-lg object-contain border bg-white p-1" />
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
                        {logoPreview ? 'Change' : 'Upload'}
                      </span>
                    </label>
                  </div>
                  <p className="text-xs text-muted-foreground">PNG, JPG, SVG or WebP. Max 2MB.</p>
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
            {/* Logo upload for manual providers */}
            {editingProvider && (editingProvider.config?.provider_type === 'manual' || editingProvider.name === 'manual') && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">Logo</Label>
                <div className="flex items-center gap-3">
                  {logoPreview ? (
                    <div className="relative">
                      <img src={logoPreview} alt="Logo preview" className="h-12 w-12 rounded-lg object-contain border bg-white p-1" />
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
                      {logoPreview ? 'Change' : 'Upload'}
                    </span>
                  </label>
                </div>
                <p className="text-xs text-muted-foreground">PNG, JPG, SVG or WebP. Max 2MB.</p>
              </div>
            )}
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
