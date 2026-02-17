'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth, Permissions } from '@/components/auth-provider';
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
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { PageLoader } from '@/components/ui/loading-spinner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Plus, Pencil, Trash2, RefreshCw, Users, Key, CheckCircle2, XCircle, Loader2, Building2, Package, AlertTriangle, Upload, X, Info, ChevronDown } from 'lucide-react';
import Link from 'next/link';
import { useLocale } from '@/components/locale-provider';
import {
  useProviders,
  hrisProviderTypes,
  licenseProviderTypes,
  PROVIDER_LINKS,
  PROVIDERS_WITH_SETUP,
  getFieldLabel,
  hasOAuthSupport,
} from '@/hooks/use-providers';
import { api } from '@/lib/api';

export default function ProvidersPage() {
  const t = useTranslations('providers');
  const tCommon = useTranslations('common');
  const tLicenses = useTranslations('licenses');
  const tSetup = useTranslations('providerSetup');
  const { formatDate } = useLocale();
  const router = useRouter();
  const { hasPermission, isLoading: authLoading } = useAuth();
  const canCreate = hasPermission(Permissions.PROVIDERS_CREATE);
  const canUpdate = hasPermission(Permissions.PROVIDERS_UPDATE);
  const canDelete = hasPermission(Permissions.PROVIDERS_DELETE);
  const canSync = hasPermission(Permissions.PROVIDERS_SYNC);

  const searchParams = useSearchParams();
  const [manualExpanded, setManualExpanded] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);

  const {
    hrisProviders,
    licenseProviders,
    loading,
    addDialogOpen,
    setAddDialogOpen,
    editDialogOpen,
    setEditDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    deletingProvider,
    setDeletingProvider,
    editingProvider,
    dialogMode,
    newProviderType,
    setNewProviderType,
    newProviderName,
    setNewProviderName,
    credentials,
    setCredentials,
    manualConfig,
    setManualConfig,
    logoPreview,
    saving,
    error,
    syncingProviderId,
    toast,
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
    showToast,
    fetchProviders,
  } = useProviders({ t, tCommon });

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.PROVIDERS_VIEW)) {
      router.push('/unauthorized');
      return;
    }
  }, [authLoading, hasPermission, router]);

  // Handle OAuth callback URL params
  useEffect(() => {
    const connected = searchParams.get('connected');
    const error = searchParams.get('error');
    if (connected === 'google_workspace') {
      showToast('success', t('googleWorkspaceConnected'));
      fetchProviders();
      router.replace('/providers');
    } else if (error === 'google_workspace_failed') {
      showToast('error', t('connectionFailed'));
      router.replace('/providers');
    }
  }, [searchParams]);

  if (authLoading || loading) {
    return (
      <AppLayout>
        <PageLoader />
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
            {hrisProviders.length === 0 && canCreate && (
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
                    {canSync && (
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleSyncProvider(provider.id)} disabled={syncingProviderId === provider.id}>
                        <RefreshCw className={`h-4 w-4 ${syncingProviderId === provider.id ? 'animate-spin' : ''}`} />
                      </Button>
                    )}
                    {canUpdate && (
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpenEditDialog(provider)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                    )}
                    {canDelete && (
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700" onClick={() => { setDeletingProvider(provider); setDeleteDialogOpen(true); }}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
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
            {canCreate && (
              <Button size="sm" variant="outline" onClick={() => handleOpenAddDialog('license')}>
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                {t('addProvider')}
              </Button>
            )}
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
                                {provider.license_stats.unassigned > 0 && (
                                  <span className="text-amber-600 inline-flex items-center gap-0.5"> + {provider.license_stats.unassigned} {tLicenses('unassignedShort')}</span>
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
                        {!isManual && canSync && (
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
              <Select value={newProviderType} onValueChange={(v) => { setNewProviderType(v); setManualExpanded(false); }}>
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
            {/* OAuth Provider: Dual-mode UI */}
            {hasOAuthSupport(newProviderType) && (
              <>
                {/* OAuth Section */}
                <div className="space-y-3">
                  <Button
                    type="button"
                    className="w-full bg-[#4285F4] hover:bg-[#3367D6] text-white"
                    disabled={!newProviderName || oauthLoading}
                    onClick={async () => {
                      setOauthLoading(true);
                      try {
                        const { authorize_url } = await api.getGoogleWorkspaceAuthUrl(newProviderName || 'Google Workspace');
                        window.location.href = authorize_url;
                      } catch {
                        setOauthLoading(false);
                      }
                    }}
                  >
                    {oauthLoading ? (
                      <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> {t('connectWithGoogle')}</>
                    ) : (
                      <>{t('connectWithGoogle')}</>
                    )}
                  </Button>
                  <div className="flex items-start gap-2 bg-blue-50 border border-blue-200 rounded-md p-3">
                    <Info className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                    <p className="text-xs text-blue-700">{t('googleAdminRequired')}</p>
                  </div>
                </div>

                {/* Divider + Manual Section (collapsible) */}
                <div>
                  <button
                    type="button"
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors w-full"
                    onClick={() => setManualExpanded(!manualExpanded)}
                  >
                    <ChevronDown className={`h-3.5 w-3.5 transition-transform ${manualExpanded ? 'rotate-0' : '-rotate-90'}`} />
                    {t('orConnectManually')}
                  </button>
                  {manualExpanded && (
                    <div className="space-y-4 mt-3 pt-3 border-t">
                      {getProviderFields(newProviderType).map((field) => (
                        <div key={field} className="space-y-2">
                          <Label className="text-xs font-medium">{getFieldLabel(field, t)}</Label>
                          <Input
                            type={field.includes('key') || field.includes('token') || field.includes('secret') ? 'password' : 'text'}
                            value={credentials[field] || ''}
                            onChange={(e) => setCredentials({ ...credentials, [field]: e.target.value })}
                          />
                        </div>
                      ))}
                      {/* Setup Instructions for manual mode */}
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
                    </div>
                  )}
                </div>
              </>
            )}
            {/* Non-OAuth API Provider Fields */}
            {!isManualProvider(newProviderType) && !hasOAuthSupport(newProviderType) && getProviderFields(newProviderType).map((field) => (
              <div key={field} className="space-y-2">
                <Label className="text-xs font-medium">{getFieldLabel(field, t)}</Label>
                <Input
                  type={field.includes('key') || field.includes('token') || field.includes('secret') ? 'password' : 'text'}
                  value={credentials[field] || ''}
                  onChange={(e) => setCredentials({ ...credentials, [field]: e.target.value })}
                />
              </div>
            ))}
            {/* Setup Instructions (non-OAuth providers) */}
            {PROVIDERS_WITH_SETUP.includes(newProviderType) && !hasOAuthSupport(newProviderType) && (
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
      <ConfirmationDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('deleteProvider')}
        description={t('deleteConfirmation', { name: deletingProvider?.display_name || '' })}
        confirmLabel={t('deleteProvider')}
        onConfirm={handleDeleteProvider}
      />
    </AppLayout>
  );
}
