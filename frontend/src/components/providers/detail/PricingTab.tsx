'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Package,
  Plus,
  Calendar,
  Settings,
  Trash2,
  Building2,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import type {
  LicenseTypeInfo,
  IndividualLicenseTypeInfo,
  LicensePackage,
  OrganizationLicense,
  License,
  Provider,
} from '@/lib/api';
import type { PricingEditState, LocaleFormatters } from './types';

export interface PricingTabProps {
  provider: Provider;
  licenseTypes: LicenseTypeInfo[];
  licenses: License[];
  totalLicenses: number;
  pricingEdits: Record<string, PricingEditState>;
  setPricingEdits: React.Dispatch<React.SetStateAction<Record<string, PricingEditState>>>;
  onSavePricing: () => Promise<void>;
  savingPricing: boolean;
  // Package pricing
  licensePackages: LicensePackage[];
  onAddPackage: () => void;
  onEditPackage: (pkg: LicensePackage) => void;
  onDeletePackage: (pkg: LicensePackage) => void;
  // Org licenses
  orgLicenses: OrganizationLicense[];
  onAddOrgLicense: () => void;
  onEditOrgLicense: (license: OrganizationLicense) => void;
  onDeleteOrgLicense: (license: OrganizationLicense) => void;
  // Individual pricing (Microsoft/Azure)
  hasCombinedTypes: boolean;
  individualLicenseTypes: IndividualLicenseTypeInfo[];
  individualPricingEdits: Record<string, Omit<PricingEditState, 'next_billing_date'>>;
  setIndividualPricingEdits: React.Dispatch<React.SetStateAction<Record<string, Omit<PricingEditState, 'next_billing_date'>>>>;
  onSaveIndividualPricing: () => Promise<void>;
  savingIndividualPricing: boolean;
  // Formatters
  formatCurrency: (value: number | string | null | undefined, currency?: string) => string;
  formatDate: LocaleFormatters['formatDate'];
  t: (key: string, params?: Record<string, string>) => string;
  tCommon: (key: string) => string;
}

/**
 * Pricing tab component for provider detail page.
 * Handles license type pricing, packages, and organization licenses.
 */
export function PricingTab({
  provider,
  licenseTypes,
  licenses,
  totalLicenses,
  pricingEdits,
  setPricingEdits,
  onSavePricing,
  savingPricing,
  licensePackages,
  onAddPackage,
  onEditPackage,
  onDeletePackage,
  orgLicenses,
  onAddOrgLicense,
  onEditOrgLicense,
  onDeleteOrgLicense,
  hasCombinedTypes,
  individualLicenseTypes,
  individualPricingEdits,
  setIndividualPricingEdits,
  onSaveIndividualPricing,
  savingIndividualPricing,
  formatCurrency,
  formatDate,
  t,
  tCommon,
}: PricingTabProps) {
  const licenseInfo = provider.config?.provider_license_info;
  const hasPackageLicense = !!licenseInfo?.max_users;

  return (
    <div className="space-y-6">
      {/* Package-based Pricing Overview (e.g., Mattermost) */}
      {hasPackageLicense && (
        <PackagePricingSection
          provider={provider}
          totalLicenses={totalLicenses}
          pricingEdits={pricingEdits}
          setPricingEdits={setPricingEdits}
          onSavePricing={onSavePricing}
          savingPricing={savingPricing}
          formatCurrency={formatCurrency}
          formatDate={formatDate}
          t={t}
          tCommon={tCommon}
        />
      )}

      {/* Individual License Type Pricing (Microsoft/Azure) */}
      {hasCombinedTypes && individualLicenseTypes.length > 0 && (
        <IndividualPricingSection
          individualLicenseTypes={individualLicenseTypes}
          individualPricingEdits={individualPricingEdits}
          setIndividualPricingEdits={setIndividualPricingEdits}
          onSaveIndividualPricing={onSaveIndividualPricing}
          savingIndividualPricing={savingIndividualPricing}
          t={t}
          tCommon={tCommon}
        />
      )}

      {/* Regular License Type Pricing */}
      {!hasCombinedTypes && licenseTypes.length > 0 && (
        <RegularPricingSection
          provider={provider}
          licenseTypes={licenseTypes}
          pricingEdits={pricingEdits}
          setPricingEdits={setPricingEdits}
          onSavePricing={onSavePricing}
          savingPricing={savingPricing}
          t={t}
          tCommon={tCommon}
        />
      )}

      {!hasCombinedTypes && licenseTypes.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {t('monthlyCalculationNote')}
        </p>
      )}

      {hasCombinedTypes && individualLicenseTypes.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {t('individualPriceCalculationNote')}
        </p>
      )}

      {/* License Packages Section */}
      <LicensePackagesSection
        licensePackages={licensePackages}
        onAddPackage={onAddPackage}
        onEditPackage={onEditPackage}
        onDeletePackage={onDeletePackage}
        formatDate={formatDate}
        t={t}
        tCommon={tCommon}
      />

      {/* Organization Licenses Section */}
      <OrganizationLicensesSection
        orgLicenses={orgLicenses}
        onAddOrgLicense={onAddOrgLicense}
        onEditOrgLicense={onEditOrgLicense}
        onDeleteOrgLicense={onDeleteOrgLicense}
        formatDate={formatDate}
        t={t}
        tCommon={tCommon}
      />
    </div>
  );
}

/**
 * Package pricing section for providers with max_users (package licenses).
 */
function PackagePricingSection({
  provider,
  totalLicenses,
  pricingEdits,
  setPricingEdits,
  onSavePricing,
  savingPricing,
  formatCurrency,
  formatDate,
  t,
  tCommon,
}: {
  provider: Provider;
  totalLicenses: number;
  pricingEdits: Record<string, PricingEditState>;
  setPricingEdits: React.Dispatch<React.SetStateAction<Record<string, PricingEditState>>>;
  onSavePricing: () => Promise<void>;
  savingPricing: boolean;
  formatCurrency: (value: number | string | null | undefined, currency?: string) => string;
  formatDate: LocaleFormatters['formatDate'];
  t: (key: string) => string;
  tCommon: (key: string) => string;
}) {
  const licenseInfo = provider.config?.provider_license_info;
  const packagePricing = provider.config?.package_pricing;

  const packageEdit = pricingEdits['__package__'] || {
    cost: packagePricing?.cost || '',
    currency: packagePricing?.currency || 'EUR',
    billing_cycle: packagePricing?.billing_cycle || 'yearly',
    payment_frequency: 'monthly',
    display_name: '',
    next_billing_date: packagePricing?.next_billing_date || '',
    notes: packagePricing?.notes || '',
  };

  const updatePackageEdit = (updates: Partial<typeof packageEdit>) => {
    setPricingEdits((prev) => ({
      ...prev,
      ['__package__']: { ...packageEdit, ...updates },
    }));
  };

  const packageCost = parseFloat(packageEdit.cost) || 0;
  const maxUsers = licenseInfo?.max_users || 0;
  const isYearly = packageEdit.billing_cycle === 'yearly';
  const isQuarterly = packageEdit.billing_cycle === 'quarterly';

  // Get expiration date from license info
  const expiresAt = licenseInfo?.expires_at ? new Date(licenseInfo.expires_at) : null;
  const expiresAtStr = expiresAt ? expiresAt.toISOString().split('T')[0] : '';
  const nextBillingDate = packageEdit.next_billing_date || expiresAtStr;

  // Cost per user based on package size
  const costPerUser = maxUsers > 0 ? packageCost / maxUsers : 0;
  const monthlyCostPerUser = isYearly ? costPerUser / 12 : isQuarterly ? costPerUser / 3 : costPerUser;

  return (
    <Card className="border-blue-200 bg-blue-50/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Package className="h-4 w-4" />
          Package License Pricing
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          This provider uses a package license for {maxUsers} users.
          Enter the total package cost and it will be distributed across all active users.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 p-4 bg-white rounded-lg border">
          <div className="text-center">
            <p className="text-xs text-muted-foreground uppercase">{t('packageSize')}</p>
            <p className="text-xl font-semibold">{maxUsers} Users</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground uppercase">{t('activeUsers')}</p>
            <p className="text-xl font-semibold">{totalLicenses}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground uppercase">
              {isYearly ? t('yearly') : isQuarterly ? t('quarterly') : t('monthly')} {t('cost')}
            </p>
            <p className="text-xl font-semibold">{formatCurrency(packageCost, packageEdit.currency)}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground uppercase">{t('costPerUser')}</p>
            <p className="text-xl font-semibold text-emerald-600">
              {packageEdit.currency} {costPerUser.toFixed(2)}
              {isYearly ? t('perYearShort') : isQuarterly ? t('perQuarterShort') : t('perMonthShort')}
            </p>
            {(isYearly || isQuarterly) && (
              <p className="text-xs text-muted-foreground">
                ({packageEdit.currency} {monthlyCostPerUser.toFixed(2)}{t('perMonthShort')})
              </p>
            )}
          </div>
          {expiresAt && (
            <div className="text-center">
              <p className="text-xs text-muted-foreground uppercase">{t('expires')}</p>
              <p className="text-xl font-semibold">{formatDate(expiresAt)}</p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">{t('totalPackageCost')}</Label>
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
            <Label className="text-xs text-muted-foreground">{t('billingCycle')}</Label>
            <Select value={packageEdit.billing_cycle} onValueChange={(v) => updatePackageEdit({ billing_cycle: v })}>
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

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">{t('nextBillingRenewal')}</Label>
            <Input
              type="date"
              value={nextBillingDate}
              onChange={(e) => updatePackageEdit({ next_billing_date: e.target.value })}
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">{t('notes')}</Label>
            <Input
              placeholder={t('optionalNotes')}
              value={packageEdit.notes}
              onChange={(e) => updatePackageEdit({ notes: e.target.value })}
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button size="sm" onClick={onSavePricing} disabled={savingPricing}>
            {savingPricing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
            Apply Package Pricing
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Individual license type pricing section for Microsoft/Azure.
 */
function IndividualPricingSection({
  individualLicenseTypes,
  individualPricingEdits,
  setIndividualPricingEdits,
  onSaveIndividualPricing,
  savingIndividualPricing,
  t,
  tCommon,
}: {
  individualLicenseTypes: IndividualLicenseTypeInfo[];
  individualPricingEdits: Record<string, Omit<PricingEditState, 'next_billing_date'>>;
  setIndividualPricingEdits: React.Dispatch<React.SetStateAction<Record<string, Omit<PricingEditState, 'next_billing_date'>>>>;
  onSaveIndividualPricing: () => Promise<void>;
  savingIndividualPricing: boolean;
  t: (key: string) => string;
  tCommon: (key: string) => string;
}) {
  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-medium">{t('licenseTypePricing')}</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {tCommon('description')}
          </p>
        </div>
        <Button
          size="sm"
          onClick={onSaveIndividualPricing}
          disabled={savingIndividualPricing}
        >
          {savingIndividualPricing && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          {tCommon('save')} {t('pricing')}
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
            setIndividualPricingEdits((prev) => ({
              ...prev,
              [lt.license_type]: { ...edit, ...updates },
            }));
          };

          // Calculate monthly equivalent for display
          let monthlyEquivalent = '';
          if (edit.cost && parseFloat(edit.cost) > 0) {
            const cost = parseFloat(edit.cost);
            if (edit.billing_cycle === 'yearly') {
              monthlyEquivalent = `≈ ${(cost / 12).toFixed(2)} ${edit.currency}${t('perMonthSuffix')}`;
            } else if (edit.billing_cycle === 'quarterly') {
              monthlyEquivalent = `≈ ${(cost / 3).toFixed(2)} ${edit.currency}${t('perMonthSuffix')}`;
            } else if (edit.billing_cycle === 'monthly') {
              monthlyEquivalent = `${cost.toFixed(2)} ${edit.currency}${t('perMonthSuffix')}`;
            }
          }

          return (
            <Card key={lt.license_type}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-xs text-muted-foreground font-mono">{lt.license_type}</p>
                    <h3 className="font-medium text-sm">
                      {edit.display_name || lt.display_name || lt.license_type}
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
                    <Label className="text-xs text-muted-foreground">{t('displayName')}</Label>
                    <Input
                      placeholder={lt.license_type}
                      value={edit.display_name}
                      onChange={(e) => updateEdit({ display_name: e.target.value })}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{t('cost')}</Label>
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
                    <Label className="text-xs text-muted-foreground">{t('billingCycle')}</Label>
                    <Select value={edit.billing_cycle} onValueChange={(v) => updateEdit({ billing_cycle: v })}>
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

                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{t('payment')}</Label>
                    <Select value={edit.payment_frequency} onValueChange={(v) => updateEdit({ payment_frequency: v })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="monthly">{t('monthly')}</SelectItem>
                        <SelectItem value="yearly">{t('yearly')}</SelectItem>
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
  );
}

/**
 * Regular license type pricing section.
 */
function RegularPricingSection({
  provider,
  licenseTypes,
  pricingEdits,
  setPricingEdits,
  onSavePricing,
  savingPricing,
  t,
  tCommon,
}: {
  provider: Provider;
  licenseTypes: LicenseTypeInfo[];
  pricingEdits: Record<string, PricingEditState>;
  setPricingEdits: React.Dispatch<React.SetStateAction<Record<string, PricingEditState>>>;
  onSavePricing: () => Promise<void>;
  savingPricing: boolean;
  t: (key: string) => string;
  tCommon: (key: string) => string;
}) {
  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-medium">{t('licenseTypePricing')}</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {provider.config?.provider_license_info?.max_users
              ? t('individualPricesNote')
              : t('setPricesDescription')}
          </p>
        </div>
        <Button size="sm" onClick={onSavePricing} disabled={savingPricing}>
          {savingPricing && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          {tCommon('save')} {t('pricing')}
        </Button>
      </div>

      <div className="grid gap-4">
        {licenseTypes.map((licType) => {
          const existingPricing = licType.pricing;
          const edit = pricingEdits[licType.license_type] || {
            cost: existingPricing?.cost || '',
            currency: existingPricing?.currency || 'EUR',
            billing_cycle: existingPricing?.billing_cycle || 'monthly',
            payment_frequency: existingPricing?.payment_frequency || 'monthly',
            display_name: existingPricing?.display_name || '',
            next_billing_date: existingPricing?.next_billing_date || '',
            notes: existingPricing?.notes || '',
          };

          const updateEdit = (updates: Partial<typeof edit>) => {
            setPricingEdits((prev) => ({
              ...prev,
              [licType.license_type]: { ...edit, ...updates },
            }));
          };

          return (
            <Card key={licType.license_type}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-medium text-sm">
                      {edit.display_name || licType.license_type}
                    </h3>
                    <p className="text-xs text-muted-foreground font-mono">{licType.license_type}</p>
                  </div>
                  <Badge variant="secondary">{licType.count} {t('licenses')}</Badge>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{t('displayName')}</Label>
                    <Input
                      placeholder={licType.license_type}
                      value={edit.display_name}
                      onChange={(e) => updateEdit({ display_name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{t('costPerLicense')}</Label>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      value={edit.cost}
                      onChange={(e) => updateEdit({ cost: e.target.value })}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{t('currency')}</Label>
                    <Select value={edit.currency} onValueChange={(v) => updateEdit({ currency: v })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="EUR">EUR</SelectItem>
                        <SelectItem value="USD">USD</SelectItem>
                        <SelectItem value="GBP">GBP</SelectItem>
                        <SelectItem value="CHF">CHF</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{t('billingCycle')}</Label>
                    <Select value={edit.billing_cycle} onValueChange={(v) => updateEdit({ billing_cycle: v })}>
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
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{t('paymentFrequency')}</Label>
                    <Select value={edit.payment_frequency} onValueChange={(v) => updateEdit({ payment_frequency: v })}>
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
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{t('nextBillingDate')}</Label>
                    <Input
                      type="date"
                      value={edit.next_billing_date}
                      onChange={(e) => updateEdit({ next_billing_date: e.target.value })}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{t('notes')}</Label>
                    <Input
                      placeholder={t('optionalNotes')}
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
    </>
  );
}

/**
 * License packages section for tracking package-based licenses.
 */
function LicensePackagesSection({
  licensePackages,
  onAddPackage,
  onEditPackage,
  onDeletePackage,
  formatDate,
  t,
  tCommon,
}: {
  licensePackages: LicensePackage[];
  onAddPackage: () => void;
  onEditPackage: (pkg: LicensePackage) => void;
  onDeletePackage: (pkg: LicensePackage) => void;
  formatDate: LocaleFormatters['formatDate'];
  t: (key: string, params?: Record<string, string>) => string;
  tCommon: (key: string) => string;
}) {
  return (
    <div className="border-t pt-6 mt-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-medium flex items-center gap-2">
            <Package className="h-4 w-4" />
            {t('licensePackages')}
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {t('licensePackagesDescription')}
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={onAddPackage}>
          <Plus className="h-4 w-4 mr-1" />
          {tCommon('add')}
        </Button>
      </div>

      {licensePackages.length === 0 ? (
        <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground">
          <Package className="h-8 w-8 mx-auto mb-2 opacity-30" />
          <p className="text-sm">{t('noLicensePackages')}</p>
          <p className="text-xs mt-1">{t('addPackageToTrack')}</p>
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
                        className={
                          pkg.utilization_percent > 90
                            ? 'text-red-600 border-red-200 bg-red-50'
                            : pkg.utilization_percent > 70
                            ? 'text-amber-600 border-amber-200 bg-amber-50'
                            : 'text-emerald-600 border-emerald-200 bg-emerald-50'
                        }
                      >
                        {pkg.utilization_percent}% used
                      </Badge>
                      {pkg.status === 'cancelled' && (
                        <Badge variant="destructive">{t('cancelled')}</Badge>
                      )}
                      {pkg.status === 'expired' && (
                        <Badge variant="secondary">{t('expired')}</Badge>
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
                        <span className="text-muted-foreground">{t('seats')}:</span>{' '}
                        <span className="font-medium">{pkg.assigned_seats}</span>
                        <span className="text-muted-foreground"> / {pkg.total_seats}</span>
                        {pkg.available_seats > 0 && (
                          <span className="text-emerald-600 ml-1">
                            ({pkg.available_seats} {t('available')})
                          </span>
                        )}
                      </div>
                      {pkg.cost_per_seat && (
                        <div>
                          <span className="text-muted-foreground">{t('costPerSeat')}:</span>{' '}
                          <span className="font-medium">
                            {pkg.currency} {pkg.cost_per_seat}
                          </span>
                        </div>
                      )}
                      {pkg.total_monthly_cost && (
                        <div>
                          <span className="text-muted-foreground">{t('total')}:</span>{' '}
                          <span className="font-medium">
                            {pkg.currency} {pkg.total_monthly_cost}
                            {t('perMonthShort')}
                          </span>
                        </div>
                      )}
                    </div>

                    {(pkg.contract_start || pkg.contract_end) && (
                      <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        {pkg.contract_start && (
                          <span>{t('fromDate', { date: formatDate(pkg.contract_start) })}</span>
                        )}
                        {pkg.contract_end && (
                          <span>{t('toDate', { date: formatDate(pkg.contract_end) })}</span>
                        )}
                        {pkg.auto_renew && (
                          <Badge variant="secondary" className="text-xs">
                            {t('autoRenew')}
                          </Badge>
                        )}
                      </div>
                    )}
                    {pkg.cancelled_at && pkg.cancellation_effective_date && (
                      <div className="flex items-center gap-2 mt-2 text-xs text-red-600">
                        <AlertTriangle className="h-3 w-3" />
                        <span>
                          {t('cancellationEffective', { date: formatDate(pkg.cancellation_effective_date) })}
                          {pkg.cancellation_reason && ` - ${pkg.cancellation_reason}`}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => onEditPackage(pkg)}>
                      <Settings className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onDeletePackage(pkg)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>

                {/* Utilization bar */}
                <div className="mt-3 h-2 bg-zinc-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      pkg.utilization_percent > 90
                        ? 'bg-red-500'
                        : pkg.utilization_percent > 70
                        ? 'bg-amber-500'
                        : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, pkg.utilization_percent)}%` }}
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Organization licenses section for tracking org-wide licenses.
 */
function OrganizationLicensesSection({
  orgLicenses,
  onAddOrgLicense,
  onEditOrgLicense,
  onDeleteOrgLicense,
  formatDate,
  t,
  tCommon,
}: {
  orgLicenses: OrganizationLicense[];
  onAddOrgLicense: () => void;
  onEditOrgLicense: (license: OrganizationLicense) => void;
  onDeleteOrgLicense: (license: OrganizationLicense) => void;
  formatDate: LocaleFormatters['formatDate'];
  t: (key: string, params?: Record<string, string>) => string;
  tCommon: (key: string) => string;
}) {
  return (
    <div className="border-t pt-6 mt-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-medium flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            {t('organizationLicenses')}
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {t('orgLicenseDescription')}
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={onAddOrgLicense}>
          <Plus className="h-4 w-4 mr-1" />
          {t('addLicense')}
        </Button>
      </div>

      {orgLicenses.length === 0 ? (
        <div className="border border-dashed rounded-lg p-6 text-center text-muted-foreground">
          <Building2 className="h-8 w-8 mx-auto mb-2 opacity-30" />
          <p className="text-sm">{t('noOrgLicenses')}</p>
          <p className="text-xs mt-1">{t('addOrgLicenseNote')}</p>
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
                          <span className="text-muted-foreground">{t('quantity')}:</span>{' '}
                          <span className="font-medium">
                            {lic.quantity} {lic.unit || 'units'}
                          </span>
                        </div>
                      )}
                      {lic.monthly_cost && (
                        <div>
                          <span className="text-muted-foreground">{t('cost')}:</span>{' '}
                          <span className="font-medium">
                            {lic.currency} {lic.monthly_cost}
                            {t('perMonthShort')}
                          </span>
                        </div>
                      )}
                    </div>

                    {lic.renewal_date && (
                      <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        <span>{t('renewsDate', { date: formatDate(lic.renewal_date) })}</span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => onEditOrgLicense(lic)}>
                      <Settings className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onDeleteOrgLicense(lic)}>
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
  );
}
