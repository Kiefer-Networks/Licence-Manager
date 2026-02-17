/**
 * Shared types for provider detail page components.
 */

import type {
  Provider,
  License,
  Employee,
  LicenseTypeInfo,
  LicenseTypePricing,
  ProviderFile,
  CategorizedLicensesResponse,
  IndividualLicenseTypeInfo,
  PaymentMethod,
  LicensePackage,
  OrganizationLicense,
} from '@/lib/api';

/**
 * Locale formatting functions from useLocale hook.
 */
export interface LocaleFormatters {
  formatDate: (date: string | Date | null | undefined) => string;
  formatDateTimeWithSeconds: (date: string | Date | null | undefined) => string;
  formatCurrency: (value: number | string | null | undefined) => string;
  formatNumber: (value: number | null | undefined) => string;
}

/**
 * License statistics computed from licenses array.
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
 * Props for the Overview tab component.
 */
export interface OverviewTabProps {
  provider: Provider;
  stats: LicenseStats;
  licenseTypes?: LicenseTypeInfo[];
  isManual: boolean;
  isSeatBased: boolean;
  formatDate: LocaleFormatters['formatDate'];
  formatDateTimeWithSeconds: LocaleFormatters['formatDateTimeWithSeconds'];
  t: (key: string) => string;
  tCommon: (key: string) => string;
  tLicenses: (key: string) => string;
}

/**
 * Props for the Licenses tab component.
 */
export interface LicensesTabProps {
  provider: Provider;
  categorizedLicenses: CategorizedLicensesResponse | null;
  isManual: boolean;
  isSeatBased: boolean;
  onAddLicense: (mode: 'single' | 'bulk' | 'seats') => void;
  onAssignLicense: (license: License) => void;
  onDeleteLicense: (license: License) => void;
  onServiceAccount: (license: License) => void;
  onAdminAccount: (license: License) => void;
  onLicenseType: (license: License) => void;
  formatCurrency: LocaleFormatters['formatCurrency'];
  t: (key: string) => string;
  tCommon: (key: string) => string;
  tLicenses: (key: string) => string;
}

/**
 * Pricing edit form state.
 */
export interface PricingEditState {
  cost: string;
  currency: string;
  billing_cycle: string;
  payment_frequency: string;
  display_name: string;
  next_billing_date: string;
  notes: string;
  purchased_quantity: string;
}

/**
 * Props for the Pricing tab component.
 */
export interface PricingTabProps {
  provider: Provider;
  licenseTypes: LicenseTypeInfo[];
  licenses: License[];
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
  formatCurrency: LocaleFormatters['formatCurrency'];
  formatDate: LocaleFormatters['formatDate'];
  t: (key: string) => string;
  tCommon: (key: string) => string;
}

/**
 * Props for the Files tab component.
 */
export interface FilesTabProps {
  provider: Provider;
  files: ProviderFile[];
  uploadingFile: boolean;
  fileDescription: string;
  setFileDescription: (value: string) => void;
  fileCategory: string;
  setFileCategory: (value: string) => void;
  onUploadFile: (file: File) => Promise<void>;
  onDeleteFile: (file: ProviderFile) => Promise<void>;
  onDownloadFile: (file: ProviderFile) => void;
  formatDate: LocaleFormatters['formatDate'];
  t: (key: string) => string;
  tCommon: (key: string) => string;
}

/**
 * Props for the Settings tab component.
 */
export interface SettingsTabProps {
  provider: Provider;
  isManual: boolean;
  settingsForm: {
    display_name: string;
    license_model: string;
    payment_method_id: string | null;
  };
  setSettingsForm: React.Dispatch<React.SetStateAction<{
    display_name: string;
    license_model: string;
    payment_method_id: string | null;
  }>>;
  savingSettings: boolean;
  onSaveSettings: () => Promise<void>;
  paymentMethods: PaymentMethod[];
  // Credentials
  publicCredentials: Record<string, string>;
  credentialsForm: Record<string, string>;
  setCredentialsForm: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  showCredentialsEdit: boolean;
  setShowCredentialsEdit: (value: boolean) => void;
  savingCredentials: boolean;
  onSaveCredentials: () => Promise<void>;
  onDeleteProvider: () => void;
  t: (key: string) => string;
  tCommon: (key: string) => string;
}
