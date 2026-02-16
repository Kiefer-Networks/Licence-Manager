'use client';

import { useEffect, useState } from 'react';
import { api, Provider } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import {
  hrisProviderTypes,
  licenseProviderTypes,
  getProviderFields as getProviderFieldsFromLib,
  getFieldLabel,
} from '@/lib/provider-fields';

// Re-export constants and helpers used by the page component
export { hrisProviderTypes, licenseProviderTypes, getFieldLabel } from '@/lib/provider-fields';

/**
 * Documentation links for providers (not translated).
 */
export const PROVIDER_LINKS: Record<string, string> = {
  '1password': 'https://support.1password.com/scim/',
  adobe: 'https://developer.adobe.com/developer-console/docs/guides/services/services-add-api-oauth-s2s/',
  atlassian: 'https://support.atlassian.com/organization-administration/docs/manage-an-organization-with-the-admin-apis/',
  cursor: 'https://cursor.sh/settings/team',
  figma: 'https://www.figma.com/developers/api#access-tokens',
  github: 'https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens',
  gitlab: 'https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html',
  google_workspace: 'https://developers.google.com/admin-sdk/directory/v1/guides/delegation',
  hibob: 'https://apidocs.hibob.com/reference/getting-started',
  huggingface: 'https://huggingface.co/docs/hub/en/api',
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

/**
 * Provider types that have setup instructions.
 */
export const PROVIDERS_WITH_SETUP = [
  '1password', 'adobe', 'anthropic', 'atlassian', 'auth0', 'cursor', 'figma',
  'github', 'gitlab', 'google_workspace', 'hibob', 'huggingface', 'jetbrains',
  'mailjet', 'mattermost', 'microsoft', 'miro', 'openai', 'personio', 'slack', 'zoom'
];

/**
 * Translation functions required by the useProviders hook.
 */
interface ProvidersTranslations {
  t: (key: string, params?: Record<string, string | number>) => string;
  tCommon: (key: string) => string;
}

/**
 * Return type for the useProviders hook.
 */
export interface UseProvidersReturn {
  // Data
  providers: Provider[];
  hrisProviders: Provider[];
  licenseProviders: Provider[];
  loading: boolean;

  // Dialog state
  addDialogOpen: boolean;
  setAddDialogOpen: (v: boolean) => void;
  editDialogOpen: boolean;
  setEditDialogOpen: (v: boolean) => void;
  deleteDialogOpen: boolean;
  setDeleteDialogOpen: (v: boolean) => void;
  deletingProvider: Provider | null;
  setDeletingProvider: (v: Provider | null) => void;
  editingProvider: Provider | null;

  // Form state
  dialogMode: 'hris' | 'license';
  newProviderType: string;
  setNewProviderType: (v: string) => void;
  newProviderName: string;
  setNewProviderName: (v: string) => void;
  credentials: Record<string, string>;
  setCredentials: (v: Record<string, string>) => void;
  manualConfig: { license_model: string };
  setManualConfig: (v: { license_model: string }) => void;
  logoFile: File | null;
  logoPreview: string | null;
  saving: boolean;
  error: string | null;
  syncingProviderId: string | null;
  toast: { type: 'success' | 'error'; text: string } | null;

  // Handlers
  fetchProviders: () => Promise<void>;
  getProviderFields: (providerName: string) => string[];
  handleOpenAddDialog: (mode: 'hris' | 'license') => void;
  handleOpenEditDialog: (provider: Provider) => void;
  handleAddProvider: () => Promise<void>;
  handleUpdateProvider: () => Promise<void>;
  handleDeleteProvider: () => Promise<void>;
  handleSyncProvider: (providerId: string) => Promise<void>;
  handleLogoChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  clearLogo: () => void;
  isManualProvider: (providerType: string) => boolean;
}

/**
 * Custom hook that encapsulates all business logic for the Providers page.
 * Manages provider list, CRUD operations, sync, and dialog state.
 */
export function useProviders(
  { t, tCommon }: ProvidersTranslations,
): UseProvidersReturn {
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
    return getProviderFieldsFromLib(providerName);
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

      // Manual providers need a unique name derived from display_name
      // API providers use the fixed type name (e.g. 'adobe', 'slack')
      const providerName = isManual
        ? `manual_${newProviderName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '')}`
        : providerType;

      const newProvider = await api.createProvider({
        name: providerName,
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
      showToast('success', t('providerAdded', { name: newProviderName }));
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

  return {
    // Data
    providers,
    hrisProviders,
    licenseProviders,
    loading,

    // Dialog state
    addDialogOpen,
    setAddDialogOpen,
    editDialogOpen,
    setEditDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    deletingProvider,
    setDeletingProvider,
    editingProvider,

    // Form state
    dialogMode,
    newProviderType,
    setNewProviderType,
    newProviderName,
    setNewProviderName,
    credentials,
    setCredentials,
    manualConfig,
    setManualConfig,
    logoFile,
    logoPreview,
    saving,
    error,
    syncingProviderId,
    toast,

    // Handlers
    fetchProviders,
    getProviderFields,
    handleOpenAddDialog,
    handleOpenEditDialog,
    handleAddProvider,
    handleUpdateProvider,
    handleDeleteProvider,
    handleSyncProvider,
    handleLogoChange,
    clearLogo,
    isManualProvider,
  };
}
