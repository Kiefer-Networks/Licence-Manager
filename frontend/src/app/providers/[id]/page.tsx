'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { EmployeeAutocomplete } from '@/components/ui/employee-autocomplete';
import { useLocale } from '@/components/locale-provider';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { ImportWizardDialog } from '@/components/import';
import { FIGMA_LICENSE_TYPES } from '@/lib/constants';
import { useProviderDetail } from '@/hooks/use-provider-detail';
import type { Tab } from '@/hooks/use-provider-detail';
import {
  OverviewTab,
  LicensesTab,
  FilesTab,
  PricingTab,
  SettingsTab,
} from '@/components/providers/detail';
import { CancellationDialog } from '@/components/licenses/CancellationDialog';
import {
  Key,
  Package,
  RefreshCw,
  Plus,
  Loader2,
  CheckCircle2,
  XCircle,
  Upload,
  Bot,
  Building2,
  ShieldCheck,
} from 'lucide-react';
import Link from 'next/link';

export default function ProviderDetailPage() {
  const params = useParams();
  const providerId = params.id as string;
  const t = useTranslations('providers');
  const tCommon = useTranslations('common');
  const tLicenses = useTranslations('licenses');
  const tLifecycle = useTranslations('lifecycle');
  const { formatDate, formatDateTimeWithSeconds, formatCurrency, formatNumber } = useLocale();
  const router = useRouter();
  const { hasPermission, isLoading: authLoading } = useAuth();
  const canUpdate = hasPermission(Permissions.PROVIDERS_UPDATE);
  const canDelete = hasPermission(Permissions.PROVIDERS_DELETE);
  const canSync = hasPermission(Permissions.PROVIDERS_SYNC);

  const detail = useProviderDetail(providerId, t, tCommon, tLicenses);

  const {
    provider,
    licenses,
    categorizedLicenses,
    employees,
    loading,
    isManual,
    isSeatBased,
    stats,
    activeTab,
    setActiveTab,
    toast,
    showToast,
    syncing,
    handleSync,
    importDialogOpen,
    setImportDialogOpen,
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
    assignDialog,
    setAssignDialog,
    selectedEmployeeId,
    setSelectedEmployeeId,
    handleAssign,
    deleteDialog,
    setDeleteDialog,
    handleDeleteLicense,
    cancelDialog,
    setCancelDialog,
    handleCancelLicense,
    serviceAccountDialog,
    serviceAccountForm,
    setServiceAccountForm,
    savingServiceAccount,
    handleOpenServiceAccountDialog,
    handleSaveServiceAccount,
    setServiceAccountDialog,
    adminAccountDialog,
    adminAccountForm,
    setAdminAccountForm,
    savingAdminAccount,
    handleOpenAdminAccountDialog,
    handleSaveAdminAccount,
    setAdminAccountDialog,
    licenseTypeDialog,
    selectedLicenseType,
    setSelectedLicenseType,
    savingLicenseType,
    handleOpenLicenseTypeDialog,
    handleSaveLicenseType,
    setLicenseTypeDialog,
    handleConfirmMatch,
    handleRejectMatch,
    settingsForm,
    setSettingsForm,
    savingSettings,
    handleSaveSettings,
    paymentMethods,
    credentialsForm,
    setCredentialsForm,
    savingCredentials,
    showCredentialsEdit,
    setShowCredentialsEdit,
    publicCredentials,
    handleSaveCredentials,
    deleteProviderOpen,
    setDeleteProviderOpen,
    handleDeleteProvider,
    licenseTypes,
    pricingEdits,
    setPricingEdits,
    savingPricing,
    handleSavePricing,
    individualLicenseTypes,
    hasCombinedTypes,
    individualPricingEdits,
    setIndividualPricingEdits,
    savingIndividualPricing,
    handleSaveIndividualPricing,
    files,
    uploadingFile,
    fileDescription,
    setFileDescription,
    fileCategory,
    setFileCategory,
    handleFileUpload,
    handleDeleteFile,
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
    fetchLicenses,
  } = detail;

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.PROVIDERS_VIEW)) {
      router.push('/unauthorized');
      return;
    }
  }, [authLoading, hasPermission, router]);

  if (authLoading || loading) {
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
          <p className="text-muted-foreground">{t('providerNotFound')}</p>
          <Link href="/settings">
            <Button variant="outline" className="mt-4">{t('backToSettings')}</Button>
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
            { label: t('title'), href: '/providers' },
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
                    {isManual ? t('manual') : t('apiIntegrated')}
                  </Badge>
                  {provider.config?.billing_cycle && (
                    <span className="text-xs text-muted-foreground">{provider.config.billing_cycle}</span>
                  )}
                </div>
              </div>
            </div>
          <div className="flex items-center gap-2">
            {!isManual && canSync && (
              <Button variant="outline" size="sm" onClick={handleSync} disabled={syncing}>
                <RefreshCw className={`h-4 w-4 mr-1.5 ${syncing ? 'animate-spin' : ''}`} />
                Sync
              </Button>
            )}
            {isManual && canUpdate && (
              <>
                <Button variant="outline" size="sm" onClick={() => setImportDialogOpen(true)}>
                  <Upload className="h-4 w-4 mr-1.5" />
                  {t('import.title')}
                </Button>
                <Button size="sm" onClick={() => { setAddLicenseOpen(true); setAddLicenseMode('single'); }}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Add License
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <nav className="flex gap-6">
            {(['overview', 'licenses', 'pricing', 'files', 'settings'] as Tab[]).map((tab) => {
              const tabLabels: Record<Tab, string> = {
                overview: t('tabOverview'),
                licenses: t('tabLicenses'),
                pricing: t('tabPricing'),
                files: t('tabFiles'),
                settings: t('tabSettings'),
              };
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab
                      ? 'border-zinc-900 text-zinc-900'
                      : 'border-transparent text-muted-foreground hover:text-zinc-900'
                  }`}
                >
                  {tabLabels[tab]}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <OverviewTab
            provider={provider}
            stats={stats}
            licenseTypes={licenseTypes}
            licenses={licenses}
            isManual={isManual}
            isSeatBased={isSeatBased}
            formatDate={formatDate}
            formatDateTimeWithSeconds={formatDateTimeWithSeconds}
            t={t}
            tCommon={tCommon}
            tLicenses={tLicenses}
          />
        )}

        {activeTab === 'licenses' && (
          <LicensesTab
            provider={provider}
            categorizedLicenses={categorizedLicenses}
            isManual={isManual}
            onAddLicense={(mode) => { setAddLicenseOpen(true); setAddLicenseMode(mode); }}
            onAssign={(license) => setAssignDialog(license)}
            onDelete={(license) => setDeleteDialog(license)}
            onCancel={(license) => setCancelDialog(license)}
            onServiceAccount={handleOpenServiceAccountDialog}
            onAdminAccount={handleOpenAdminAccountDialog}
            onLicenseType={provider?.name === 'figma' ? handleOpenLicenseTypeDialog : undefined}
            onConfirmMatch={handleConfirmMatch}
            onRejectMatch={handleRejectMatch}
            t={t}
          />
        )}

        {activeTab === 'pricing' && (
          <PricingTab
            provider={provider}
            licenseTypes={licenseTypes}
            licenses={licenses}
            totalLicenses={stats.totalLicenses}
            pricingEdits={pricingEdits}
            setPricingEdits={setPricingEdits}
            onSavePricing={handleSavePricing}
            savingPricing={savingPricing}
            licensePackages={licensePackages}
            onAddPackage={() => handleOpenPackageDialog()}
            onEditPackage={(pkg) => handleOpenPackageDialog(pkg)}
            onDeletePackage={handleDeletePackage}
            orgLicenses={orgLicenses}
            onAddOrgLicense={() => handleOpenOrgLicenseDialog()}
            onEditOrgLicense={(lic) => handleOpenOrgLicenseDialog(lic)}
            onDeleteOrgLicense={handleDeleteOrgLicense}
            hasCombinedTypes={hasCombinedTypes}
            individualLicenseTypes={individualLicenseTypes}
            individualPricingEdits={individualPricingEdits}
            setIndividualPricingEdits={setIndividualPricingEdits}
            onSaveIndividualPricing={handleSaveIndividualPricing}
            savingIndividualPricing={savingIndividualPricing}
            formatCurrency={formatCurrency}
            formatDate={formatDate}
            t={t}
            tCommon={tCommon}
          />
        )}

        {activeTab === 'files' && (
          <FilesTab
            providerId={providerId}
            files={files}
            uploadingFile={uploadingFile}
            fileDescription={fileDescription}
            setFileDescription={setFileDescription}
            fileCategory={fileCategory}
            setFileCategory={setFileCategory}
            onFileUpload={handleFileUpload}
            onDeleteFile={handleDeleteFile}
            formatDate={formatDate}
            t={t}
            tCommon={tCommon}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsTab
            provider={provider}
            isManual={isManual}
            settingsForm={settingsForm}
            setSettingsForm={setSettingsForm}
            savingSettings={savingSettings}
            onSaveSettings={handleSaveSettings}
            paymentMethods={paymentMethods}
            publicCredentials={publicCredentials}
            credentialsForm={credentialsForm}
            setCredentialsForm={setCredentialsForm}
            showCredentialsEdit={showCredentialsEdit}
            setShowCredentialsEdit={setShowCredentialsEdit}
            savingCredentials={savingCredentials}
            onSaveCredentials={handleSaveCredentials}
            onDeleteProvider={() => setDeleteProviderOpen(true)}
            t={t}
            tCommon={tCommon}
          />
        )}
      </div>

      {/* Add License Dialog */}
      <Dialog open={addLicenseOpen} onOpenChange={setAddLicenseOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {t('addLicense')}
            </DialogTitle>
            <DialogDescription>
              {t('addLicenseDescription')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('licenseType')}</Label>
              <Input
                value={licenseForm.license_type}
                onChange={(e) => setLicenseForm({ ...licenseForm, license_type: e.target.value })}
                placeholder={t('optionalTypeSku')}
              />
            </div>

            {addLicenseMode === 'single' && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('licenseKeyOptional')}</Label>
                <Input
                  value={licenseForm.license_key}
                  onChange={(e) => setLicenseForm({ ...licenseForm, license_key: e.target.value })}
                  placeholder="e.g., XXXX-YYYY-ZZZZ"
                />
              </div>
            )}

            {addLicenseMode === 'bulk' && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('licenseKeysMultiple')}</Label>
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
                <Label className="text-xs font-medium">{t('numberOfSeats')}</Label>
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
                <Label className="text-xs font-medium">{t('costPerLicenseOptional')}</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={licenseForm.monthly_cost}
                  onChange={(e) => setLicenseForm({ ...licenseForm, monthly_cost: e.target.value })}
                  placeholder={provider?.config?.default_cost || tCommon('optional')}
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('validUntil')}</Label>
                <Input
                  type="date"
                  value={licenseForm.valid_until}
                  onChange={(e) => setLicenseForm({ ...licenseForm, valid_until: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('notesOptional')}</Label>
              <Input
                value={licenseForm.notes}
                onChange={(e) => setLicenseForm({ ...licenseForm, notes: e.target.value })}
                placeholder={t('optionalNotes')}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAddLicenseOpen(false)}>{tCommon('cancel')}</Button>
            <Button onClick={handleAddLicense} disabled={savingLicense}>
              {savingLicense ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              {tCommon('add')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign Dialog */}
      <Dialog open={!!assignDialog} onOpenChange={() => setAssignDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('assignLicense')}</DialogTitle>
            <DialogDescription>
              {t('selectEmployee')}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label className="text-xs font-medium mb-2 block">{t('selectEmployee')}</Label>
            <EmployeeAutocomplete
              employees={employees}
              value={selectedEmployeeId}
              onChange={setSelectedEmployeeId}
              placeholder={t('chooseEmployee')}
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAssignDialog(null)}>{tCommon('cancel')}</Button>
            <Button onClick={handleAssign} disabled={!selectedEmployeeId}>{t('assign')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete License Dialog */}
      <ConfirmationDialog
        open={!!deleteDialog}
        onOpenChange={() => setDeleteDialog(null)}
        title={t('deleteLicense')}
        description={t('deleteConfirmMessage', { email: deleteDialog?.external_user_id || '' })}
        confirmLabel={tCommon('delete')}
        onConfirm={handleDeleteLicense}
      />

      {/* Delete Provider Dialog */}
      <ConfirmationDialog
        open={deleteProviderOpen}
        onOpenChange={setDeleteProviderOpen}
        title={t('deleteProvider')}
        description={t('confirmDeleteProvider', { name: provider?.display_name || '' })}
        confirmLabel={tCommon('delete')}
        onConfirm={handleDeleteProvider}
      />

      {/* Cancel License Dialog */}
      <CancellationDialog
        open={!!cancelDialog}
        onOpenChange={(open) => { if (!open) setCancelDialog(null); }}
        onConfirm={handleCancelLicense}
        title={tLifecycle('cancelLicense')}
        description={tLifecycle('cancelDescription')}
        itemName={cancelDialog?.external_user_id || ''}
      />

      {/* Service Account Dialog */}
      <Dialog open={!!serviceAccountDialog} onOpenChange={() => setServiceAccountDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-blue-500" />
              {t('serviceAccountSettings')}
            </DialogTitle>
            <DialogDescription>
              {t('configureAsServiceAccount', { email: serviceAccountDialog?.external_user_id || '' })}
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
                {t('markAsServiceAccount')}
              </Label>
            </div>

            {serviceAccountForm.is_service_account && (
              <>
                <div>
                  <Label className="text-xs font-medium mb-2 block">{t('serviceAccountNameOptional')}</Label>
                  <Input
                    placeholder={t('serviceAccountNamePlaceholder')}
                    value={serviceAccountForm.service_account_name}
                    onChange={(e) => setServiceAccountForm(prev => ({ ...prev, service_account_name: e.target.value }))}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('serviceAccountNameDescription')}
                  </p>
                </div>

                <div>
                  <Label className="text-xs font-medium mb-2 block">{t('ownerOptional')}</Label>
                  <EmployeeAutocomplete
                    employees={employees}
                    value={serviceAccountForm.service_account_owner_id}
                    onChange={(v) => setServiceAccountForm(prev => ({ ...prev, service_account_owner_id: v }))}
                    placeholder={t('selectResponsibleEmployee')}
                    noOwnerLabel={t('noOwner')}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('responsiblePersonDescription')}
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
                      {t('addToGlobalList')}
                    </Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {t('globalPatternDescription')}
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setServiceAccountDialog(null)}>{tCommon('cancel')}</Button>
            <Button onClick={handleSaveServiceAccount} disabled={savingServiceAccount}>
              {savingServiceAccount && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {tCommon('save')}
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
              {t('adminAccountSettings')}
            </DialogTitle>
            <DialogDescription>
              {t('configureAsAdminAccount', { email: adminAccountDialog?.external_user_id || '' })}
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
                {t('markAsAdminAccount')}
              </Label>
            </div>

            {adminAccountForm.is_admin_account && (
              <>
                <div>
                  <Label className="text-xs font-medium mb-2 block">{t('adminAccountNameOptional')}</Label>
                  <Input
                    placeholder={t('adminAccountNamePlaceholder')}
                    value={adminAccountForm.admin_account_name}
                    onChange={(e) => setAdminAccountForm(prev => ({ ...prev, admin_account_name: e.target.value }))}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('adminAccountNameDescription')}
                  </p>
                </div>

                <div>
                  <Label className="text-xs font-medium mb-2 block">{t('ownerLinkedEmployee')}</Label>
                  <EmployeeAutocomplete
                    employees={employees}
                    value={adminAccountForm.admin_account_owner_id}
                    onChange={(v) => setAdminAccountForm(prev => ({ ...prev, admin_account_owner_id: v }))}
                    placeholder={t('selectEmployee')}
                    noOwnerLabel={t('noOwner')}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('adminResponsibleDescription')}
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
                      {t('addToGlobalAdminList')}
                    </Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {t('globalAdminPatternDescription')}
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAdminAccountDialog(null)}>{tCommon('cancel')}</Button>
            <Button onClick={handleSaveAdminAccount} disabled={savingAdminAccount}>
              {savingAdminAccount && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {tCommon('save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* License Type Dialog (for Figma and similar providers) */}
      <Dialog open={!!licenseTypeDialog} onOpenChange={() => setLicenseTypeDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Key className="h-5 w-5 text-blue-500" />
              {tLicenses('changeLicenseType')}
            </DialogTitle>
            <DialogDescription>
              {licenseTypeDialog?.external_user_id || licenseTypeDialog?.metadata?.name || ''}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-xs font-medium mb-2 block">{tLicenses('selectLicenseType')}</Label>
              <Select value={selectedLicenseType} onValueChange={setSelectedLicenseType}>
                <SelectTrigger>
                  <SelectValue placeholder={tLicenses('selectLicenseType')} />
                </SelectTrigger>
                <SelectContent>
                  {FIGMA_LICENSE_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>{type}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setLicenseTypeDialog(null)}>{tCommon('cancel')}</Button>
            <Button onClick={handleSaveLicenseType} disabled={savingLicenseType || !selectedLicenseType}>
              {savingLicenseType && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {tCommon('save')}
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
              {editingPackage ? t('editPackage') : t('addLicensePackage')}
            </DialogTitle>
            <DialogDescription>
              {editingPackage ? t('editPackageDescription') : t('addPackageDescription')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">{t('licenseTypeRequired2')}</Label>
                <Input
                  placeholder={t('optionalTypeSku')}
                  value={packageForm.license_type}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, license_type: e.target.value }))}
                  disabled={!!editingPackage}
                />
              </div>
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">{t('displayName')}</Label>
                <Input
                  placeholder={t('optionalFriendlyName')}
                  value={packageForm.display_name}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, display_name: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">{t('totalSeatsRequired')}</Label>
                <Input
                  type="number"
                  min="1"
                  placeholder="100"
                  value={packageForm.total_seats}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, total_seats: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">{t('costPerSeat')}</Label>
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
                <Label className="text-xs font-medium mb-2 block">{t('billingCycle')}</Label>
                <Select value={packageForm.billing_cycle} onValueChange={(v) => setPackageForm(prev => ({ ...prev, billing_cycle: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="monthly">{t('monthly')}</SelectItem>
                    <SelectItem value="quarterly">{t('quarterly')}</SelectItem>
                    <SelectItem value="yearly">{t('yearly')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">{t('contractStart')}</Label>
                <Input
                  type="date"
                  value={packageForm.contract_start}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, contract_start: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">{t('contractEnd')}</Label>
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
                <Label htmlFor="auto_renew" className="text-sm cursor-pointer">{t('autoRenew')}</Label>
              </div>
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">{t('notes')}</Label>
                <Textarea
                  placeholder={t('optionalNotes')}
                  value={packageForm.notes}
                  onChange={(e) => setPackageForm(prev => ({ ...prev, notes: e.target.value }))}
                  rows={2}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPackageDialogOpen(false)}>{tCommon('cancel')}</Button>
            <Button onClick={handleSavePackage} disabled={savingPackage}>
              {savingPackage && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {editingPackage ? t('update') : t('create')}
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
              {editingOrgLicense ? t('editOrgLicense') : t('addOrgLicense')}
            </DialogTitle>
            <DialogDescription>
              {editingOrgLicense ? t('editOrgLicenseDescription') : t('addOrgLicenseDescription')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">{tCommon('name')} *</Label>
                <Input
                  placeholder={t('optionalFriendlyName')}
                  value={orgLicenseForm.name}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, name: e.target.value }))}
                />
              </div>
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">{t('licenseType')}</Label>
                <Input
                  placeholder={t('optionalTypeSku')}
                  value={orgLicenseForm.license_type}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, license_type: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">{t('quantity')}</Label>
                <Input
                  type="number"
                  min="0"
                  placeholder="100"
                  value={orgLicenseForm.quantity}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, quantity: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">{t('unit')}</Label>
                <Input
                  placeholder={t('unitPlaceholder')}
                  value={orgLicenseForm.unit}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, unit: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">{t('monthlyCost')}</Label>
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
                <Label className="text-xs font-medium mb-2 block">{t('billingCycle')}</Label>
                <Select value={orgLicenseForm.billing_cycle} onValueChange={(v) => setOrgLicenseForm(prev => ({ ...prev, billing_cycle: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="monthly">{t('monthly')}</SelectItem>
                    <SelectItem value="quarterly">{t('quarterly')}</SelectItem>
                    <SelectItem value="yearly">{t('yearly')}</SelectItem>
                    <SelectItem value="perpetual">{t('perpetual')}</SelectItem>
                    <SelectItem value="one_time">{t('oneTime')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-medium mb-2 block">{t('renewalDate')}</Label>
                <Input
                  type="date"
                  value={orgLicenseForm.renewal_date}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, renewal_date: e.target.value }))}
                />
              </div>
              <div className="col-span-2">
                <Label className="text-xs font-medium mb-2 block">{t('notes')}</Label>
                <Textarea
                  placeholder={t('optionalNotes')}
                  value={orgLicenseForm.notes}
                  onChange={(e) => setOrgLicenseForm(prev => ({ ...prev, notes: e.target.value }))}
                  rows={2}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOrgLicenseDialogOpen(false)}>{tCommon('cancel')}</Button>
            <Button onClick={handleSaveOrgLicense} disabled={savingOrgLicense}>
              {savingOrgLicense && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {editingOrgLicense ? t('update') : t('create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Wizard Dialog */}
      <ImportWizardDialog
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        providerId={providerId}
        onSuccess={() => {
          fetchLicenses();
          showToast('success', t('import.resultTitle'));
        }}
        onError={(error) => showToast('error', error)}
      />
    </AppLayout>
  );
}
