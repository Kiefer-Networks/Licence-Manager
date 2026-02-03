const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// CSRF token cache with expiration tracking
let csrfToken: string | null = null;
let csrfTokenTimestamp: number = 0;
const CSRF_TOKEN_MAX_AGE_MS = 7 * 60 * 60 * 1000; // 7 hours (before 8h backend expiry)

/**
 * Check if cached CSRF token is still valid.
 */
function isCsrfTokenValid(): boolean {
  if (!csrfToken || !csrfTokenTimestamp) return false;
  return Date.now() - csrfTokenTimestamp < CSRF_TOKEN_MAX_AGE_MS;
}

/**
 * Clear CSRF token cache.
 */
function clearCsrfToken(): void {
  csrfToken = null;
  csrfTokenTimestamp = 0;
}

/**
 * Get CSRF token from cookie or fetch a new one.
 * Required for all state-changing requests (POST, PUT, DELETE).
 */
async function getCsrfToken(): Promise<string> {
  // Try to get from cookie first (always freshest source)
  if (typeof window !== 'undefined') {
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrf_token='))
      ?.split('=')[1];
    if (cookieValue) {
      const decodedToken = decodeURIComponent(cookieValue);
      // Update cache if token differs or cache is stale
      if (decodedToken !== csrfToken || !isCsrfTokenValid()) {
        csrfToken = decodedToken;
        csrfTokenTimestamp = Date.now();
      }
      return csrfToken;
    }
  }

  // Fetch new token if not in cookie or cache is stale
  if (!csrfToken || !isCsrfTokenValid()) {
    const response = await fetch(`${API_BASE}/api/v1/auth/csrf-token`, {
      method: 'GET',
      credentials: 'include',
    });
    if (response.ok) {
      const data = await response.json();
      csrfToken = data.csrf_token;
      csrfTokenTimestamp = Date.now();
    }
  }

  return csrfToken || '';
}

async function getAuthHeaders(method: string = 'GET'): Promise<HeadersInit> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Add CSRF token for state-changing requests
  if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
    const token = await getCsrfToken();
    if (token) {
      headers['X-CSRF-Token'] = token;
    }
  }

  return headers;
}

// Token refresh helper using httpOnly cookies
async function refreshAccessToken(): Promise<boolean> {
  if (typeof window === 'undefined') return false;

  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // Send httpOnly cookies
    });

    return response.ok;
  } catch {
    return false;
  }
}

// Default request timeout in milliseconds (30 seconds)
const REQUEST_TIMEOUT_MS = 30000;

// File upload validation constants
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024; // 2 MB for logos
const MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB for avatars
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'];
const ALLOWED_DOCUMENT_TYPES = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
const ALLOWED_UPLOAD_TYPES = [...ALLOWED_IMAGE_TYPES, ...ALLOWED_DOCUMENT_TYPES];

/**
 * Sanitize a filename to prevent path traversal and special characters.
 * Only allows alphanumeric characters, hyphens, underscores, and dots.
 */
function sanitizeFilename(filename: string): string {
  // Remove any path components
  const baseName = filename.split(/[/\\]/).pop() || filename;
  // Replace any characters that aren't alphanumeric, hyphen, underscore, or dot
  return baseName.replace(/[^a-zA-Z0-9\-_.]/g, '_');
}

/**
 * Validate file before upload.
 * Throws an error if validation fails.
 */
function validateFileUpload(file: File, options: {
  maxSize?: number;
  allowedTypes?: string[];
} = {}): void {
  const maxSize = options.maxSize || MAX_FILE_SIZE_BYTES;
  const allowedTypes = options.allowedTypes || ALLOWED_UPLOAD_TYPES;

  if (file.size > maxSize) {
    const maxMB = Math.round(maxSize / (1024 * 1024));
    throw new Error(`File size exceeds ${maxMB} MB limit`);
  }

  if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
    throw new Error('File type not allowed');
  }
}

async function fetchApi<T>(endpoint: string, options: RequestInit = {}, retry = true): Promise<T> {
  const method = options.method || 'GET';
  const headers = await getAuthHeaders(method);
  const url = `${API_BASE}/api/v1${endpoint}`;

  // Create AbortController for timeout handling
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      ...options,
      credentials: 'include', // Always include cookies
      headers: {
        ...headers,
        ...options.headers,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Handle 401 - attempt token refresh
    if (response.status === 401 && retry && typeof window !== 'undefined') {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        // Retry the request with new token from cookies
        return fetchApi<T>(endpoint, options, false);
      }
      // No valid token - let AuthProvider/AppLayout handle redirect
      // Don't redirect here to avoid conflicts with React Router
      throw new Error('Session expired');
    }

    // Handle 403 CSRF errors - refresh token and retry
    if (response.status === 403 && retry) {
      const error = await response.json().catch(() => ({ detail: '' }));
      if (error.detail?.includes('CSRF')) {
        csrfToken = null; // Clear cached token
        return fetchApi<T>(endpoint, options, false);
      }
      throw new Error(error.detail || 'Access denied');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || 'Request failed');
    }

    // Handle 204 No Content (e.g., DELETE responses)
    if (response.status === 204) {
      return undefined as T;
    }

    // Validate Content-Type header before parsing JSON
    const contentType = response.headers.get('Content-Type') || '';
    if (!contentType.includes('application/json')) {
      throw new Error('Unexpected response format');
    }

    return response.json();
  } catch (error) {
    clearTimeout(timeoutId);

    // Handle timeout (AbortError)
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timeout');
    }

    throw error;
  }
}

// Types
export interface SetupStatus {
  is_complete: boolean;
  has_hibob: boolean;
  has_providers: boolean;
  has_admin: boolean;
}

export interface DashboardData {
  total_employees: number;
  active_employees: number;
  offboarded_employees: number;
  total_licenses: number;
  active_licenses: number;
  unassigned_licenses: number;
  external_licenses: number;
  total_monthly_cost: string;
  potential_savings: string;
  currency: string;
  providers: ProviderSummary[];
  recent_offboardings: RecentOffboarding[];
  unassigned_license_samples: UnassignedLicense[];
}

export interface ProviderSummary {
  id: string;
  name: string;
  display_name: string;
  total_licenses: number;
  active_licenses: number;
  inactive_licenses: number;
  monthly_cost?: string;
  currency?: string;
  last_sync_at?: string;
}

export interface RecentOffboarding {
  employee_id: string;
  employee_name: string;
  employee_email: string;
  termination_date?: string;
  pending_licenses: number;
  provider_names: string[];
}

export interface UnassignedLicense {
  id: string;
  provider_name: string;
  provider_type: string;
  external_user_id: string;
  license_type?: string;
  monthly_cost?: string;
}

export interface PaymentMethodSummary {
  id: string;
  name: string;
  type: string;
  is_expiring: boolean;
}

export interface NotificationRule {
  id: string;
  event_type: string;
  slack_channel: string;
  enabled: boolean;
  template?: string;
}

export const NOTIFICATION_EVENT_TYPES = [
  { value: 'employee_offboarded', label: 'Employee Offboarded', description: 'When an employee with active licenses is offboarded' },
  { value: 'license_inactive', label: 'Inactive License', description: 'When a license has been inactive for 30+ days' },
  { value: 'sync_error', label: 'Sync Error', description: 'When a provider sync fails' },
  { value: 'payment_expiring', label: 'Payment Expiring', description: 'When a payment method is about to expire' },
  { value: 'license_expiring', label: 'License Expiring', description: 'When a license is about to expire within the configured threshold' },
] as const;

export interface ProviderLicenseInfo {
  is_licensed?: boolean;
  is_trial?: boolean;
  license_id?: string;
  sku_name?: string;
  company?: string;
  licensee_name?: string;
  licensee_email?: string;
  max_users?: number;
  starts_at?: string;
  expires_at?: string;
  features?: Record<string, boolean>;
}

// Typed interfaces for replacing 'any' usage
export interface LicenseTypePricingConfig {
  cost_per_seat?: string;
  display_name?: string;
  billing_cycle?: string;
  payment_frequency?: string;
}

export interface ProviderConfig {
  provider_license_info?: ProviderLicenseInfo;
  license_pricing?: Record<string, LicenseTypePricingConfig>;
  license_model?: string;
  provider_type?: string;
  package_pricing?: PackagePricing;
  default_cost?: string;
  currency?: string;
  billing_cycle?: string;
  [key: string]: ProviderLicenseInfo | Record<string, LicenseTypePricingConfig> | PackagePricing | string | number | boolean | null | undefined;
}

export interface PaymentMethodDetails {
  // Credit card
  card_last_four?: string;
  card_brand?: string;
  card_expiry_month?: number;
  card_expiry_year?: number;
  cardholder_name?: string;
  card_holder?: string;
  expiry_month?: string;
  expiry_year?: string;
  // Bank account
  bank_name?: string;
  account_last_four?: string;
  account_holder_name?: string;
  account_holder?: string;
  iban_last_four?: string;
  // Other
  provider_name?: string;
  // Generic
  [key: string]: string | number | boolean | undefined;
}

export interface SyncResults {
  synced?: number;
  added?: number;
  updated?: number;
  removed?: number;
  errors?: string[];
  [key: string]: number | string[] | undefined;
}

export interface LicenseMetadata {
  last_login?: string;
  role?: string;
  department?: string;
  email?: string;
  assignee_name?: string;
  [key: string]: string | number | boolean | undefined;
}

export interface AuditLogChanges {
  old?: Record<string, string | number | boolean | null>;
  new?: Record<string, string | number | boolean | null>;
  [key: string]: string | number | boolean | null | Record<string, string | number | boolean | null> | undefined;
}

export interface ProviderCredentials {
  api_key?: string;
  api_secret?: string;
  client_id?: string;
  client_secret?: string;
  access_token?: string;
  refresh_token?: string;
  bot_token?: string;
  admin_api_key?: string;
  tenant_id?: string;
  [key: string]: string | undefined;
}

export interface SlackConfig {
  bot_token?: string;
  default_channel?: string;
  webhook_url?: string;
  configured?: boolean;
}

export interface ProviderLicenseStats {
  active: number;
  assigned: number;  // Internal assigned (matched to HRIS)
  external: number;  // External email domains
  not_in_hris: number;  // Has user (internal email) but not found in HRIS
  unassigned: number;  // No user assigned (empty external_user_id)
  service_accounts: number;  // Service accounts (intentionally not linked to HRIS)
}

export interface Provider {
  id: string;
  name: string;
  display_name: string;
  logo_url?: string | null;
  enabled: boolean;
  config?: ProviderConfig;
  last_sync_at?: string;
  last_sync_status?: string;
  license_count: number;
  license_stats?: ProviderLicenseStats | null;
  payment_method_id?: string | null;
  payment_method?: PaymentMethodSummary | null;
  created_at: string;
  updated_at: string;
}

export interface ProviderListResponse {
  items: Provider[];
  total: number;
}

export interface License {
  id: string;
  provider_id: string;
  provider_name: string;
  employee_id?: string;
  employee_email?: string;
  employee_name?: string;
  external_user_id: string;
  license_type?: string;
  license_type_display_name?: string;
  status: string;
  assigned_at?: string;
  last_activity_at?: string;
  monthly_cost?: string;
  currency: string;
  metadata?: LicenseMetadata;
  synced_at: string;
  is_external_email?: boolean;
  employee_status?: string;
  // Service account fields
  is_service_account?: boolean;
  service_account_name?: string;
  service_account_owner_id?: string;
  service_account_owner_name?: string;
  // Admin account fields
  is_admin_account?: boolean;
  admin_account_name?: string;
  admin_account_owner_id?: string;
  admin_account_owner_name?: string;
  admin_account_owner_status?: string;
  // Match fields
  suggested_employee_id?: string;
  suggested_employee_name?: string;
  suggested_employee_email?: string;
  match_confidence?: number;
  match_status?: string;  // auto_matched, suggested, confirmed, rejected, external_guest, external_review
  match_method?: string;  // exact_email, alias, local_part, fuzzy_name
  // Expiration tracking
  expires_at?: string;
  needs_reorder?: boolean;
  // Cancellation tracking
  cancelled_at?: string;
  cancellation_effective_date?: string;
  cancellation_reason?: string;
  cancelled_by?: string;
}

export interface LicenseListResponse {
  items: License[];
  total: number;
  page: number;
  page_size: number;
}

export interface LicenseStats {
  total_active: number;
  total_assigned: number;
  total_unassigned: number;  // Licenses with no user assigned (empty external_user_id)
  total_not_in_hris: number;  // Has user (internal email) but not found in HRIS
  total_inactive: number;
  total_external: number;
  total_service_accounts: number;
  total_suggested: number;
  total_external_review: number;
  total_external_guest: number;
  monthly_cost: string;
  potential_savings: string;
  currency: string;
  has_currency_mix: boolean;
  currencies_found: string[];
}

export interface CategorizedLicensesResponse {
  assigned: License[];
  unassigned: License[];  // Licenses with no user assigned (empty external_user_id)
  not_in_hris: License[];  // Has user (internal email) but not found in HRIS
  external: License[];
  service_accounts: License[];
  // New categories for match workflow
  suggested: License[];
  external_review: License[];
  external_guest: License[];
  stats: LicenseStats;
}

export interface MatchActionResponse {
  success: boolean;
  message: string;
  license?: License;
}

export interface ManagerInfo {
  id: string;
  email: string;
  full_name: string;
  avatar?: string;  // Base64 data URL or null
}

export type EmployeeSource = 'hibob' | 'personio' | 'manual';

export interface Employee {
  id: string;
  hibob_id: string;
  email: string;
  full_name: string;
  department?: string;
  status: string;
  source: EmployeeSource;
  start_date?: string;
  termination_date?: string;
  avatar?: string;  // Base64 data URL or null
  license_count: number;
  owned_admin_account_count?: number;  // Number of admin accounts owned by this employee
  manager?: ManagerInfo;
  synced_at: string;
  is_manual: boolean;
}

export interface EmployeeListResponse {
  items: Employee[];
  total: number;
  page: number;
  page_size: number;
}

export interface EmployeeCreate {
  email: string;
  full_name: string;
  department?: string;
  status?: 'active' | 'offboarded';
  start_date?: string;
  termination_date?: string;
  manager_email?: string;
}

export interface EmployeeUpdate {
  email?: string;
  full_name?: string;
  department?: string;
  status?: 'active' | 'offboarded';
  start_date?: string;
  termination_date?: string;
  manager_email?: string;
}

export interface EmployeeBulkImportItem {
  email: string;
  full_name: string;
  department?: string;
  status?: 'active' | 'offboarded';
  start_date?: string;
  manager_email?: string;
}

export interface EmployeeBulkImportResponse {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
}

export interface InactiveLicenseEntry {
  license_id: string;
  provider_id: string;
  provider_name: string;
  employee_id?: string;
  employee_name?: string;
  employee_email?: string;
  employee_status?: string;
  external_user_id: string;
  last_activity_at?: string;
  days_inactive: number;
  monthly_cost?: string;
  is_external_email: boolean;
}

export interface InactiveLicenseReport {
  threshold_days: number;
  total_inactive: number;
  potential_savings: string;
  currency: string;
  licenses: InactiveLicenseEntry[];
}

export interface LicenseRecommendation {
  license_id: string;
  provider_id: string;
  provider_name: string;
  external_user_id: string;
  license_type?: string;
  employee_id?: string;
  employee_name?: string;
  employee_email?: string;
  employee_status?: string;
  days_inactive: number;
  last_activity_at?: string;
  monthly_cost?: string;
  yearly_savings?: string;
  recommendation_type: 'cancel' | 'reassign' | 'review';
  recommendation_reason: string;
  priority: 'high' | 'medium' | 'low';
  is_external_email: boolean;
}

export interface LicenseRecommendationsReport {
  total_recommendations: number;
  high_priority_count: number;
  medium_priority_count: number;
  low_priority_count: number;
  total_monthly_savings: string;
  total_yearly_savings: string;
  currency: string;
  recommendations: LicenseRecommendation[];
}

export interface BulkActionResult {
  license_id: string;
  success: boolean;
  message: string;
}

export interface BulkActionResponse {
  total: number;
  successful: number;
  failed: number;
  results: BulkActionResult[];
}

export interface OffboardedEmployee {
  employee_name: string;
  employee_email: string;
  termination_date?: string;
  days_since_offboarding: number;
  pending_licenses: Array<{ provider: string; type: string; external_id: string }>;
}

export interface OffboardingReport {
  total_offboarded_with_licenses: number;
  employees: OffboardedEmployee[];
}

export interface ExternalUserLicense {
  license_id: string;
  provider_id: string;
  provider_name: string;
  external_user_id: string;
  employee_id?: string;
  employee_name?: string;
  employee_email?: string;
  employee_status?: string;
  license_type?: string;
  monthly_cost?: string;
}

export interface ExternalUsersReport {
  total_external: number;
  licenses: ExternalUserLicense[];
}

export interface MonthlyCost {
  month: string;
  provider_name: string;
  cost: string;
  currency: string;
  license_count: number;
}

export interface CostReport {
  start_date: string;
  end_date: string;
  total_cost: string;
  currency: string;
  monthly_costs: MonthlyCost[];
  has_currency_mix: boolean;
  currencies_found: string[];
}

// Quick Win Report Types
export interface ExpiringContract {
  package_id: string;
  provider_id: string;
  provider_name: string;
  license_type: string;
  display_name?: string;
  total_seats: number;
  contract_end: string;
  days_until_expiry: number;
  auto_renew: boolean;
  total_cost?: string;
  currency: string;
}

export interface ExpiringContractsReport {
  total_expiring: number;
  contracts: ExpiringContract[];
}

export interface ProviderUtilization {
  provider_id: string;
  provider_name: string;
  license_type?: string;
  purchased_seats: number;
  active_seats: number;
  assigned_seats: number;
  unassigned_seats: number;
  external_seats: number;
  utilization_percent: number;
  monthly_cost?: string;
  monthly_waste?: string;
  external_cost?: string;
  currency: string;
}

export interface UtilizationReport {
  total_purchased: number;
  total_active: number;
  total_assigned: number;
  total_unassigned: number;
  total_external: number;
  overall_utilization: number;
  total_monthly_cost: string;
  total_monthly_waste: string;
  total_external_cost: string;
  currency: string;
  providers: ProviderUtilization[];
}

export interface CostTrendEntry {
  month: string;
  total_cost: string;
  license_count: number;
  currency: string;
}

export interface CostTrendReport {
  months: CostTrendEntry[];
  trend_direction: 'up' | 'down' | 'stable';
  percent_change: number;
  currency: string;
  has_data: boolean;
}

export interface DuplicateAccount {
  email: string;
  occurrences: number;
  providers: string[];
  names: string[];
  license_ids: string[];
  total_monthly_cost?: string;
}

export interface DuplicateAccountsReport {
  total_duplicates: number;
  potential_savings: string;
  currency: string;
  duplicates: DuplicateAccount[];
}

// Cost Breakdown Reports
export interface DepartmentCost {
  department: string;
  employee_count: number;
  license_count: number;
  total_monthly_cost: string;
  cost_per_employee: string;
  top_providers: string[];
  currency: string;
}

export interface CostsByDepartmentReport {
  total_departments: number;
  total_monthly_cost: string;
  average_cost_per_employee: string;
  currency: string;
  departments: DepartmentCost[];
}

export interface EmployeeLicenseInfo {
  provider_name: string;
  license_type?: string;
  monthly_cost?: string;
}

export interface EmployeeCost {
  employee_id: string;
  employee_name: string;
  employee_email: string;
  department?: string;
  status: string;
  license_count: number;
  total_monthly_cost: string;
  licenses: EmployeeLicenseInfo[];
  currency: string;
}

export interface CostsByEmployeeReport {
  total_employees: number;
  total_monthly_cost: string;
  average_cost_per_employee: string;
  median_cost_per_employee: string;
  max_cost_employee?: string;
  currency: string;
  employees: EmployeeCost[];
}

// License Lifecycle Types
export interface ExpiringLicense {
  license_id: string;
  provider_id: string;
  provider_name: string;
  external_user_id: string;
  license_type?: string;
  employee_id?: string;
  employee_name?: string;
  expires_at: string;
  days_until_expiry: number;
  monthly_cost?: string;
  needs_reorder: boolean;
  status: string;
}

export interface ExpiringLicensesReport {
  total_expiring: number;
  expiring_within_30_days: number;
  expiring_within_90_days: number;
  needs_reorder_count: number;
  licenses: ExpiringLicense[];
}

export interface CancelledLicense {
  license_id: string;
  provider_id: string;
  provider_name: string;
  external_user_id: string;
  license_type?: string;
  employee_id?: string;
  employee_name?: string;
  cancelled_at: string;
  cancellation_effective_date: string;
  cancellation_reason?: string;
  cancelled_by_name?: string;
  monthly_cost?: string;
  is_effective: boolean;
}

export interface CancelledLicensesReport {
  total_cancelled: number;
  pending_effective: number;
  already_effective: number;
  licenses: CancelledLicense[];
}

export interface LicenseLifecycleOverview {
  total_active: number;
  total_expiring_soon: number;
  total_expired: number;
  total_cancelled: number;
  total_needs_reorder: number;
  expiring_licenses: ExpiringLicense[];
  cancelled_licenses: CancelledLicense[];
}

// Cancellation Request/Response Types
export interface CancellationRequest {
  effective_date: string;
  reason?: string;
}

export interface CancellationResponse {
  id: string;
  cancelled_at: string;
  cancellation_effective_date: string;
  cancellation_reason?: string;
  cancelled_by?: string;
}

export interface RenewRequest {
  new_expiration_date: string;
  clear_cancellation?: boolean;
}

export interface NeedsReorderUpdate {
  needs_reorder: boolean;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
}

export interface LicenseTypePricing {
  license_type: string;
  display_name?: string | null;  // Custom display name
  cost: string;
  currency: string;
  billing_cycle: string;  // yearly, monthly, perpetual, one_time
  payment_frequency: string;  // yearly, monthly, one_time
  next_billing_date?: string | null;  // ISO date
  notes?: string | null;
}

export interface PackagePricing {
  cost: string;
  currency: string;
  billing_cycle: string;  // yearly, monthly
  next_billing_date?: string | null;
  notes?: string | null;
}

// Payment Methods
export interface PaymentMethod {
  id: string;
  name: string;
  type: string;  // credit_card, bank_account, stripe, paypal, invoice, other
  details: PaymentMethodDetails;
  is_default: boolean;
  notes?: string | null;
  is_expiring: boolean;
  days_until_expiry?: number | null;
}

export interface PaymentMethodCreate {
  name: string;
  type: string;
  details: PaymentMethodDetails;
  is_default?: boolean;
  notes?: string | null;
}

// Provider Files
export interface ProviderFile {
  id: string;
  provider_id: string;
  filename: string;
  original_name: string;
  file_type: string;
  file_size: number;
  description?: string | null;
  category?: string | null;
  created_at: string;
  viewable: boolean;  // Whether file can be viewed inline in browser (PDFs, images)
}

export interface LicenseTypeInfo {
  license_type: string;
  count: number;
  pricing: LicenseTypePricing | null;
}

// Individual license type info (extracted from combined strings like "E5, Power BI, Teams")
export interface IndividualLicenseTypeInfo {
  license_type: string;
  display_name?: string | null;
  user_count: number;
  pricing: LicenseTypePricing | null;
}

export interface IndividualLicenseTypesResponse {
  license_types: IndividualLicenseTypeInfo[];
  has_combined_types: boolean;  // True if any license_type contains commas
}

export interface SyncResponse {
  success: boolean;
  results: SyncResults;
}

// License Packages (for seat tracking)
export interface LicensePackage {
  id: string;
  provider_id: string;
  license_type: string;
  display_name?: string;
  total_seats: number;
  assigned_seats: number;
  available_seats: number;
  utilization_percent: number;
  cost_per_seat?: string;
  total_monthly_cost?: string;
  billing_cycle?: string;
  payment_frequency?: string;
  currency: string;
  contract_start?: string;
  contract_end?: string;
  auto_renew: boolean;
  notes?: string;
  // Cancellation tracking
  cancelled_at?: string;
  cancellation_effective_date?: string;
  cancellation_reason?: string;
  cancelled_by?: string;
  needs_reorder?: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface LicensePackageCreate {
  license_type: string;
  display_name?: string;
  total_seats: number;
  cost_per_seat?: string;
  billing_cycle?: string;
  payment_frequency?: string;
  currency?: string;
  contract_start?: string;
  contract_end?: string;
  auto_renew?: boolean;
  notes?: string;
}

export interface LicensePackageListResponse {
  items: LicensePackage[];
  total: number;
}

// Organization-wide Licenses
export interface OrganizationLicense {
  id: string;
  provider_id: string;
  name: string;
  license_type?: string;
  quantity?: number;
  unit?: string;
  monthly_cost?: string;
  currency: string;
  billing_cycle?: string;
  renewal_date?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationLicenseCreate {
  name: string;
  license_type?: string;
  quantity?: number;
  unit?: string;
  monthly_cost?: string;
  currency?: string;
  billing_cycle?: string;
  renewal_date?: string;
  notes?: string;
}

export interface OrganizationLicenseListResponse {
  items: OrganizationLicense[];
  total: number;
  total_monthly_cost: string;
}

// Service Account Update
export interface ServiceAccountUpdate {
  is_service_account: boolean;
  service_account_name?: string;
  service_account_owner_id?: string;
  apply_globally?: boolean;  // Add email to global service account patterns
}

// Service Account Patterns
export interface ServiceAccountPattern {
  id: string;
  email_pattern: string;
  name?: string | null;
  owner_id?: string | null;
  owner_name?: string | null;
  notes?: string | null;
  created_at: string;
  created_by?: string | null;
  created_by_name?: string | null;
  match_count: number;
}

export interface ServiceAccountPatternCreate {
  email_pattern: string;
  name?: string;
  owner_id?: string;
  notes?: string;
}

export interface ServiceAccountPatternListResponse {
  items: ServiceAccountPattern[];
  total: number;
}

export interface ApplyPatternsResponse {
  updated_count: number;
  patterns_applied: number;
}

export interface ServiceAccountLicenseListResponse {
  items: License[];
  total: number;
  page: number;
  page_size: number;
}

// Service Account License Types
export interface ServiceAccountLicenseType {
  id: string;
  license_type: string;
  name?: string | null;
  owner_id?: string | null;
  owner_name?: string | null;
  notes?: string | null;
  created_at: string;
  created_by?: string | null;
  created_by_name?: string | null;
  match_count: number;
}

export interface ServiceAccountLicenseTypeCreate {
  license_type: string;
  name?: string;
  owner_id?: string;
  notes?: string;
}

export interface ServiceAccountLicenseTypeListResponse {
  items: ServiceAccountLicenseType[];
  total: number;
}

export interface ApplyLicenseTypesResponse {
  updated_count: number;
  license_types_applied: number;
}

// Admin Account Update
export interface AdminAccountUpdate {
  is_admin_account: boolean;
  admin_account_name?: string;
  admin_account_owner_id?: string;
  apply_globally?: boolean;
}

// Admin Account Patterns
export interface AdminAccountPattern {
  id: string;
  email_pattern: string;
  name?: string | null;
  owner_id?: string | null;
  owner_name?: string | null;
  notes?: string | null;
  created_at: string;
  created_by?: string | null;
  created_by_name?: string | null;
  match_count: number;
}

export interface AdminAccountPatternCreate {
  email_pattern: string;
  name?: string;
  owner_id?: string;
  notes?: string;
}

export interface AdminAccountPatternListResponse {
  items: AdminAccountPattern[];
  total: number;
}

export interface AdminAccountLicenseListResponse {
  items: License[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrphanedAdminAccountWarning {
  license_id: string;
  external_user_id: string;
  provider_id: string;
  provider_name: string;
  admin_account_name?: string | null;
  owner_id: string;
  owner_name: string;
  owner_email: string;
  offboarded_at?: string | null;
}

export interface OrphanedAdminAccountsResponse {
  items: OrphanedAdminAccountWarning[];
  total: number;
}

// ============================================================================
// RBAC Types
// ============================================================================

export interface Permission {
  id: string;
  code: string;
  name: string;
  description?: string;
  category: string;
}

export interface PermissionCategory {
  category: string;
  permissions: Permission[];
}

export type PermissionsByCategory = Record<string, Permission[]>;

export interface Role {
  id: string;
  code: string;
  name: string;
  description?: string;
  is_system: boolean;
  priority: number;
  permissions: string[];  // Permission codes, not full objects
}

export interface RoleListResponse {
  items: Role[];
  total: number;
}

export interface RoleCreateRequest {
  code: string;
  name: string;
  description?: string;
  permission_codes: string[];
}

export interface RoleUpdateRequest {
  name?: string;
  description?: string;
  permission_codes?: string[];
}

export interface AdminUser {
  id: string;
  email: string;
  name?: string;
  picture_url?: string;
  auth_provider: string;
  is_active: boolean;
  require_password_change: boolean;
  roles: string[];  // Role codes
  permissions: string[];  // Permission codes
  last_login_at?: string;
}

export interface AdminUserListResponse {
  items: AdminUser[];
  total: number;
}

export interface AdminUserCreateRequest {
  email: string;
  name?: string;
  password: string;
  role_codes: string[];
}

export interface AdminUserUpdateRequest {
  name?: string;
  is_active?: boolean;
  role_codes?: string[];
}

export interface UserSession {
  id: string;
  user_agent?: string;
  ip_address?: string;
  created_at: string;
  expires_at: string;
  last_used_at?: string;
}

export interface CurrentUserInfo {
  id: string;
  email: string;
  name?: string;
  picture_url?: string;
  auth_provider: string;
  roles: string[];
  permissions: string[];
  is_superadmin: boolean;
  // Locale preferences
  date_format?: string;
  number_format?: string;
  currency?: string;
}

export interface ProfileUpdateRequest {
  name?: string;
  date_format?: string;
  number_format?: string;
  currency?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

// ============================================================================
// Threshold Settings Types
// ============================================================================

export interface ThresholdSettings {
  inactive_days: number;
  expiring_days: number;
  low_utilization_percent: number;
  cost_increase_percent: number;
  max_unassigned_licenses: number;
}

// ============================================================================
// User Notification Preferences Types
// ============================================================================

export interface NotificationEventType {
  code: string;
  name: string;
  description: string;
  category: string;
}

export interface UserNotificationPreference {
  id: string;
  event_type: string;
  event_name: string;
  event_description: string;
  enabled: boolean;
  slack_dm: boolean;
  slack_channel?: string;
}

export interface UserNotificationPreferenceUpdate {
  event_type: string;
  enabled: boolean;
  slack_dm: boolean;
  slack_channel?: string;
}

export interface UserNotificationPreferencesResponse {
  preferences: UserNotificationPreference[];
  available_event_types: NotificationEventType[];
}

// ============================================================================
// Audit Log Types
// ============================================================================

export interface AuditLogEntry {
  id: string;
  admin_user_id?: string;
  admin_user_email?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  changes?: AuditLogChanges;
  ip_address?: string;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ============================================================================
// Backup & Restore Types
// ============================================================================

export interface BackupInfoResponse {
  valid_format: boolean;
  version?: string;
  created_at?: string;
  requires_password: boolean;
  error?: string;
}

export interface BackupRestoreImportCounts {
  providers: number;
  licenses: number;
  employees: number;
  license_packages: number;
  organization_licenses: number;
  payment_methods: number;
  provider_files: number;
  cost_snapshots: number;
  settings: number;
  notification_rules: number;
}

export interface BackupRestoreValidation {
  providers_tested: number;
  providers_valid: number;
  providers_failed: string[];
}

export interface BackupRestoreResponse {
  success: boolean;
  imported: BackupRestoreImportCounts;
  validation: BackupRestoreValidation;
  error?: string;
}

// API Functions
export const api = {
  // Setup
  async getSetupStatus(): Promise<SetupStatus> {
    return fetchApi<SetupStatus>('/settings/status');
  },

  // Dashboard
  async getDashboard(department?: string): Promise<DashboardData> {
    const params = new URLSearchParams();
    if (department) params.set('department', department);
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetchApi<DashboardData>(`/dashboard${query}`);
  },

  // Providers
  async getProviders(): Promise<ProviderListResponse> {
    return fetchApi<ProviderListResponse>('/providers');
  },

  async getProvider(providerId: string): Promise<Provider> {
    return fetchApi<Provider>(`/providers/${providerId}`);
  },

  async createProvider(data: {
    name: string;
    display_name: string;
    credentials: ProviderCredentials;
    config?: ProviderConfig;
  }): Promise<Provider> {
    return fetchApi<Provider>('/providers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async deleteProvider(providerId: string): Promise<void> {
    await fetchApi(`/providers/${providerId}`, { method: 'DELETE' });
  },

  async updateProvider(
    providerId: string,
    data: {
      display_name?: string;
      enabled?: boolean;
      credentials?: ProviderCredentials;
      config?: ProviderConfig;
    }
  ): Promise<Provider> {
    return fetchApi<Provider>(`/providers/${providerId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async testProviderConnection(
    name: string,
    credentials: ProviderCredentials
  ): Promise<TestConnectionResponse> {
    return fetchApi<TestConnectionResponse>('/providers/test-connection', {
      method: 'POST',
      body: JSON.stringify({ name, credentials }),
    });
  },

  async syncProvider(providerId: string): Promise<SyncResponse> {
    return fetchApi<SyncResponse>(`/providers/${providerId}/sync`, { method: 'POST' });
  },

  async uploadProviderLogo(providerId: string, file: File): Promise<{ logo_url: string }> {
    // Validate file before upload
    validateFileUpload(file, {
      maxSize: MAX_LOGO_SIZE_BYTES,
      allowedTypes: ALLOWED_IMAGE_TYPES,
    });

    const formData = new FormData();
    formData.append('file', file);
    return fetchApi<{ logo_url: string }>(`/providers/${providerId}/logo`, {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type with boundary
    });
  },

  async deleteProviderLogo(providerId: string): Promise<void> {
    return fetchApi<void>(`/providers/${providerId}/logo`, { method: 'DELETE' });
  },

  async getProviderLicenseTypes(providerId: string): Promise<{ license_types: LicenseTypeInfo[] }> {
    return fetchApi<{ license_types: LicenseTypeInfo[] }>(`/providers/${providerId}/license-types`);
  },

  async getProviderPricing(providerId: string): Promise<{ pricing: LicenseTypePricing[]; package_pricing?: PackagePricing | null }> {
    return fetchApi<{ pricing: LicenseTypePricing[]; package_pricing?: PackagePricing | null }>(`/providers/${providerId}/pricing`);
  },

  async updateProviderPricing(
    providerId: string,
    pricing: LicenseTypePricing[],
    packagePricing?: PackagePricing | null
  ): Promise<{ pricing: LicenseTypePricing[]; package_pricing?: PackagePricing | null }> {
    return fetchApi<{ pricing: LicenseTypePricing[]; package_pricing?: PackagePricing | null }>(`/providers/${providerId}/pricing`, {
      method: 'PUT',
      body: JSON.stringify({ pricing, package_pricing: packagePricing }),
    });
  },

  // Individual license type pricing (for providers with combined license types like Microsoft 365)
  async getProviderIndividualLicenseTypes(providerId: string): Promise<IndividualLicenseTypesResponse> {
    return fetchApi<IndividualLicenseTypesResponse>(`/providers/${providerId}/individual-license-types`);
  },

  async updateProviderIndividualPricing(
    providerId: string,
    pricing: LicenseTypePricing[]
  ): Promise<IndividualLicenseTypesResponse> {
    return fetchApi<IndividualLicenseTypesResponse>(`/providers/${providerId}/individual-pricing`, {
      method: 'PUT',
      body: JSON.stringify({ pricing }),
    });
  },

  // Provider Files
  async getProviderFiles(providerId: string): Promise<{ items: ProviderFile[]; total: number }> {
    return fetchApi<{ items: ProviderFile[]; total: number }>(`/providers/${providerId}/files`);
  },

  async uploadProviderFile(providerId: string, file: File, description?: string, category?: string): Promise<ProviderFile> {
    // Validate file before upload
    validateFileUpload(file, {
      maxSize: MAX_FILE_SIZE_BYTES,
      allowedTypes: ALLOWED_UPLOAD_TYPES,
    });

    const formData = new FormData();
    formData.append('file', file);
    if (description) formData.append('description', description);
    if (category) formData.append('category', category);

    // Get CSRF token for file upload
    const csrfTokenValue = await getCsrfToken();

    const url = `${API_BASE}/api/v1/providers/${providerId}/files`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRF-Token': csrfTokenValue,
      },
      credentials: 'include', // Send auth cookies
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  },

  async deleteProviderFile(providerId: string, fileId: string): Promise<void> {
    await fetchApi(`/providers/${providerId}/files/${fileId}`, { method: 'DELETE' });
  },

  getProviderFileDownloadUrl(providerId: string, fileId: string): string {
    return `${API_BASE}/api/v1/providers/${providerId}/files/${fileId}/download`;
  },

  getProviderFileViewUrl(providerId: string, fileId: string): string {
    return `${API_BASE}/api/v1/providers/${providerId}/files/${fileId}/view`;
  },

  // Payment Methods
  async getPaymentMethods(): Promise<{ items: PaymentMethod[]; total: number }> {
    return fetchApi<{ items: PaymentMethod[]; total: number }>('/payment-methods');
  },

  async createPaymentMethod(data: PaymentMethodCreate): Promise<PaymentMethod> {
    return fetchApi<PaymentMethod>('/payment-methods', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updatePaymentMethod(id: string, data: Partial<PaymentMethodCreate>): Promise<PaymentMethod> {
    return fetchApi<PaymentMethod>(`/payment-methods/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deletePaymentMethod(id: string): Promise<void> {
    await fetchApi(`/payment-methods/${id}`, { method: 'DELETE' });
  },

  async triggerSync(providerId?: string): Promise<SyncResponse> {
    const endpoint = providerId ? `/providers/${providerId}/sync` : '/providers/sync';
    return fetchApi<SyncResponse>(endpoint, { method: 'POST' });
  },

  // Licenses
  async getCategorizedLicenses(params: {
    provider_id?: string;
    sort_by?: string;
    sort_dir?: 'asc' | 'desc';
  } = {}): Promise<CategorizedLicensesResponse> {
    const searchParams = new URLSearchParams();
    if (params.provider_id) searchParams.set('provider_id', params.provider_id);
    if (params.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params.sort_dir) searchParams.set('sort_dir', params.sort_dir);

    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return fetchApi<CategorizedLicensesResponse>(`/licenses/categorized${query}`);
  },

  async getPendingSuggestions(providerId?: string): Promise<{ total: number; items: License[] }> {
    const query = providerId ? `?provider_id=${providerId}` : '';
    return fetchApi<{ total: number; items: License[] }>(`/licenses/suggestions/pending${query}`);
  },

  async getLicenses(params: {
    page?: number;
    page_size?: number;
    provider_id?: string;
    employee_id?: string;
    status?: string;
    unassigned?: boolean;
    external?: boolean;
    search?: string;
    department?: string;
    sort_by?: string;
    sort_dir?: 'asc' | 'desc';
  }): Promise<LicenseListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params.provider_id) searchParams.set('provider_id', params.provider_id);
    if (params.employee_id) searchParams.set('employee_id', params.employee_id);
    if (params.status) searchParams.set('status', params.status);
    if (params.unassigned) searchParams.set('unassigned', 'true');
    if (params.external) searchParams.set('external', 'true');
    if (params.search) searchParams.set('search', params.search);
    if (params.department) searchParams.set('department', params.department);
    if (params.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params.sort_dir) searchParams.set('sort_dir', params.sort_dir);

    return fetchApi<LicenseListResponse>(`/licenses?${searchParams.toString()}`);
  },

  async removeLicenseFromProvider(licenseId: string): Promise<{ success: boolean; message: string }> {
    return fetchApi<{ success: boolean; message: string }>(`/licenses/${licenseId}/remove-from-provider`, {
      method: 'POST',
    });
  },

  async bulkRemoveFromProvider(licenseIds: string[]): Promise<BulkActionResponse> {
    return fetchApi<BulkActionResponse>('/licenses/bulk/remove-from-provider', {
      method: 'POST',
      body: JSON.stringify({ license_ids: licenseIds }),
    });
  },

  async bulkDeleteLicenses(licenseIds: string[]): Promise<BulkActionResponse> {
    return fetchApi<BulkActionResponse>('/licenses/bulk/delete', {
      method: 'POST',
      body: JSON.stringify({ license_ids: licenseIds }),
    });
  },

  async bulkUnassignLicenses(licenseIds: string[]): Promise<BulkActionResponse> {
    return fetchApi<BulkActionResponse>('/licenses/bulk/unassign', {
      method: 'POST',
      body: JSON.stringify({ license_ids: licenseIds }),
    });
  },

  // Service Account Management
  async updateLicenseServiceAccount(licenseId: string, data: ServiceAccountUpdate): Promise<License> {
    return fetchApi<License>(`/licenses/${licenseId}/service-account`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Service Account Patterns
  async getServiceAccountPatterns(): Promise<ServiceAccountPatternListResponse> {
    return fetchApi<ServiceAccountPatternListResponse>('/service-accounts/patterns');
  },

  async createServiceAccountPattern(data: ServiceAccountPatternCreate): Promise<ServiceAccountPattern> {
    return fetchApi<ServiceAccountPattern>('/service-accounts/patterns', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async deleteServiceAccountPattern(patternId: string): Promise<void> {
    await fetchApi(`/service-accounts/patterns/${patternId}`, { method: 'DELETE' });
  },

  async applyServiceAccountPatterns(): Promise<ApplyPatternsResponse> {
    return fetchApi<ApplyPatternsResponse>('/service-accounts/apply', {
      method: 'POST',
    });
  },

  async getServiceAccountLicenses(params: {
    search?: string;
    provider_id?: string;
    sort_by?: string;
    sort_dir?: 'asc' | 'desc';
    page?: number;
    page_size?: number;
  } = {}): Promise<ServiceAccountLicenseListResponse> {
    const searchParams = new URLSearchParams();
    if (params.search) searchParams.set('search', params.search);
    if (params.provider_id) searchParams.set('provider_id', params.provider_id);
    if (params.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params.sort_dir) searchParams.set('sort_dir', params.sort_dir);
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());

    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return fetchApi<ServiceAccountLicenseListResponse>(`/service-accounts/licenses${query}`);
  },

  // Service Account License Types
  async getServiceAccountLicenseTypes(): Promise<ServiceAccountLicenseTypeListResponse> {
    return fetchApi<ServiceAccountLicenseTypeListResponse>('/service-accounts/license-types');
  },

  async createServiceAccountLicenseType(data: ServiceAccountLicenseTypeCreate): Promise<ServiceAccountLicenseType> {
    return fetchApi<ServiceAccountLicenseType>('/service-accounts/license-types', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async deleteServiceAccountLicenseType(entryId: string): Promise<void> {
    await fetchApi(`/service-accounts/license-types/${entryId}`, { method: 'DELETE' });
  },

  async applyServiceAccountLicenseTypes(): Promise<ApplyLicenseTypesResponse> {
    return fetchApi<ApplyLicenseTypesResponse>('/service-accounts/apply-license-types', {
      method: 'POST',
    });
  },

  // Admin Account Management
  async updateLicenseAdminAccount(licenseId: string, data: AdminAccountUpdate): Promise<License> {
    return fetchApi<License>(`/licenses/${licenseId}/admin-account`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Admin Account Patterns
  async getAdminAccountPatterns(): Promise<AdminAccountPatternListResponse> {
    return fetchApi<AdminAccountPatternListResponse>('/admin-accounts/patterns');
  },

  async createAdminAccountPattern(data: AdminAccountPatternCreate): Promise<AdminAccountPattern> {
    return fetchApi<AdminAccountPattern>('/admin-accounts/patterns', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async deleteAdminAccountPattern(patternId: string): Promise<void> {
    await fetchApi(`/admin-accounts/patterns/${patternId}`, { method: 'DELETE' });
  },

  async applyAdminAccountPatterns(): Promise<ApplyPatternsResponse> {
    return fetchApi<ApplyPatternsResponse>('/admin-accounts/apply', {
      method: 'POST',
    });
  },

  async getAdminAccountLicenses(params: {
    search?: string;
    provider_id?: string;
    owner_id?: string;
    sort_by?: string;
    sort_dir?: 'asc' | 'desc';
    page?: number;
    page_size?: number;
  } = {}): Promise<AdminAccountLicenseListResponse> {
    const searchParams = new URLSearchParams();
    if (params.search) searchParams.set('search', params.search);
    if (params.provider_id) searchParams.set('provider_id', params.provider_id);
    if (params.owner_id) searchParams.set('owner_id', params.owner_id);
    if (params.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params.sort_dir) searchParams.set('sort_dir', params.sort_dir);
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());

    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return fetchApi<AdminAccountLicenseListResponse>(`/admin-accounts/licenses${query}`);
  },

  async getOrphanedAdminAccounts(): Promise<OrphanedAdminAccountsResponse> {
    return fetchApi<OrphanedAdminAccountsResponse>('/admin-accounts/orphaned');
  },

  // License Match Management (GDPR-compliant: no private emails stored)
  async confirmLicenseMatch(licenseId: string): Promise<MatchActionResponse> {
    return fetchApi<MatchActionResponse>(`/licenses/${licenseId}/match/confirm`, {
      method: 'POST',
    });
  },

  async rejectLicenseMatch(licenseId: string): Promise<MatchActionResponse> {
    return fetchApi<MatchActionResponse>(`/licenses/${licenseId}/match/reject`, {
      method: 'POST',
    });
  },

  async markAsExternalGuest(licenseId: string): Promise<MatchActionResponse> {
    return fetchApi<MatchActionResponse>(`/licenses/${licenseId}/match/external-guest`, {
      method: 'POST',
    });
  },

  async assignLicenseToEmployee(
    licenseId: string,
    employeeId: string,
  ): Promise<MatchActionResponse> {
    return fetchApi<MatchActionResponse>(`/licenses/${licenseId}/match/assign`, {
      method: 'POST',
      body: JSON.stringify({ employee_id: employeeId }),
    });
  },

  // License Packages
  async getLicensePackages(providerId: string): Promise<LicensePackageListResponse> {
    return fetchApi<LicensePackageListResponse>(`/providers/${providerId}/packages`);
  },

  async createLicensePackage(providerId: string, data: LicensePackageCreate): Promise<LicensePackage> {
    return fetchApi<LicensePackage>(`/providers/${providerId}/packages`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateLicensePackage(
    providerId: string,
    packageId: string,
    data: Partial<LicensePackageCreate>
  ): Promise<LicensePackage> {
    return fetchApi<LicensePackage>(`/providers/${providerId}/packages/${packageId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteLicensePackage(providerId: string, packageId: string): Promise<void> {
    await fetchApi(`/providers/${providerId}/packages/${packageId}`, { method: 'DELETE' });
  },

  // Organization Licenses
  async getOrganizationLicenses(providerId: string): Promise<OrganizationLicenseListResponse> {
    return fetchApi<OrganizationLicenseListResponse>(`/providers/${providerId}/org-licenses`);
  },

  async createOrganizationLicense(providerId: string, data: OrganizationLicenseCreate): Promise<OrganizationLicense> {
    return fetchApi<OrganizationLicense>(`/providers/${providerId}/org-licenses`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateOrganizationLicense(
    providerId: string,
    licenseId: string,
    data: Partial<OrganizationLicenseCreate>
  ): Promise<OrganizationLicense> {
    return fetchApi<OrganizationLicense>(`/providers/${providerId}/org-licenses/${licenseId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteOrganizationLicense(providerId: string, licenseId: string): Promise<void> {
    await fetchApi(`/providers/${providerId}/org-licenses/${licenseId}`, { method: 'DELETE' });
  },

  // Manual Licenses
  async createManualLicenses(data: {
    provider_id: string;
    license_type?: string;
    license_key?: string;
    quantity?: number;
    monthly_cost?: string;
    currency?: string;
    valid_until?: string;
    notes?: string;
    employee_id?: string;
  }): Promise<License[]> {
    return fetchApi<License[]>('/manual-licenses', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async createManualLicensesBulk(data: {
    provider_id: string;
    license_type?: string;
    license_keys: string[];
    monthly_cost?: string;
    currency?: string;
    valid_until?: string;
    notes?: string;
  }): Promise<License[]> {
    return fetchApi<License[]>('/manual-licenses/bulk', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateManualLicense(
    licenseId: string,
    data: {
      license_type?: string;
      license_key?: string;
      monthly_cost?: string;
      currency?: string;
      valid_until?: string;
      notes?: string;
      employee_id?: string | null;
    }
  ): Promise<License> {
    return fetchApi<License>(`/manual-licenses/${licenseId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async assignManualLicense(licenseId: string, employeeId: string): Promise<License> {
    return fetchApi<License>(`/manual-licenses/${licenseId}/assign`, {
      method: 'POST',
      body: JSON.stringify({ employee_id: employeeId }),
    });
  },

  async unassignManualLicense(licenseId: string): Promise<License> {
    return fetchApi<License>(`/manual-licenses/${licenseId}/unassign`, {
      method: 'POST',
    });
  },

  async deleteManualLicense(licenseId: string): Promise<void> {
    await fetchApi(`/manual-licenses/${licenseId}`, { method: 'DELETE' });
  },

  // Employees
  async getEmployees(params: {
    page?: number;
    page_size?: number;
    status?: string;
    department?: string;
    source?: EmployeeSource;
    search?: string;
    sort_by?: string;
    sort_dir?: 'asc' | 'desc';
  }): Promise<EmployeeListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params.status) searchParams.set('status', params.status);
    if (params.department) searchParams.set('department', params.department);
    if (params.source) searchParams.set('source', params.source);
    if (params.search) searchParams.set('search', params.search);
    if (params.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params.sort_dir) searchParams.set('sort_dir', params.sort_dir);

    return fetchApi<EmployeeListResponse>(`/users/employees?${searchParams.toString()}`);
  },

  async getEmployee(employeeId: string): Promise<Employee> {
    return fetchApi<Employee>(`/users/employees/${employeeId}`);
  },

  async createEmployee(data: EmployeeCreate): Promise<Employee> {
    return fetchApi<Employee>('/users/employees', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateEmployee(employeeId: string, data: EmployeeUpdate): Promise<Employee> {
    return fetchApi<Employee>(`/users/employees/${employeeId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteEmployee(employeeId: string): Promise<void> {
    await fetchApi(`/users/employees/${employeeId}`, { method: 'DELETE' });
  },

  async bulkImportEmployees(employees: EmployeeBulkImportItem[]): Promise<EmployeeBulkImportResponse> {
    return fetchApi<EmployeeBulkImportResponse>('/users/employees/import', {
      method: 'POST',
      body: JSON.stringify({ employees }),
    });
  },

  // Reports
  async getInactiveLicenseReport(days: number = 30, department?: string): Promise<InactiveLicenseReport> {
    const params = new URLSearchParams();
    params.set('days', days.toString());
    if (department) params.set('department', department);
    return fetchApi<InactiveLicenseReport>(`/reports/inactive?${params.toString()}`);
  },

  async getLicenseRecommendations(options?: {
    min_days_inactive?: number;
    department?: string;
    provider_id?: string;
    limit?: number;
  }): Promise<LicenseRecommendationsReport> {
    const params = new URLSearchParams();
    if (options?.min_days_inactive) params.set('min_days_inactive', options.min_days_inactive.toString());
    if (options?.department) params.set('department', options.department);
    if (options?.provider_id) params.set('provider_id', options.provider_id);
    if (options?.limit) params.set('limit', options.limit.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetchApi<LicenseRecommendationsReport>(`/reports/recommendations${query}`);
  },

  async getOffboardingReport(department?: string): Promise<OffboardingReport> {
    const params = new URLSearchParams();
    if (department) params.set('department', department);
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetchApi<OffboardingReport>(`/reports/offboarding${query}`);
  },

  async getExternalUsersReport(department?: string): Promise<ExternalUsersReport> {
    const params = new URLSearchParams();
    if (department) params.set('department', department);
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetchApi<ExternalUsersReport>(`/reports/external-users${query}`);
  },

  async getCostReport(startDate?: string, endDate?: string, department?: string): Promise<CostReport> {
    const params = new URLSearchParams();
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    if (department) params.set('department', department);
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetchApi<CostReport>(`/reports/costs${query}`);
  },

  // Quick Win Reports
  async getExpiringContractsReport(days: number = 90): Promise<ExpiringContractsReport> {
    return fetchApi<ExpiringContractsReport>(`/reports/expiring-contracts?days=${days}`);
  },

  async getUtilizationReport(): Promise<UtilizationReport> {
    return fetchApi<UtilizationReport>('/reports/utilization');
  },

  async getCostTrendReport(months: number = 6): Promise<CostTrendReport> {
    return fetchApi<CostTrendReport>(`/reports/cost-trend?months=${months}`);
  },

  async getDuplicateAccountsReport(): Promise<DuplicateAccountsReport> {
    return fetchApi<DuplicateAccountsReport>('/reports/duplicate-accounts');
  },

  // Cost Breakdown Reports
  async getCostsByDepartmentReport(): Promise<CostsByDepartmentReport> {
    return fetchApi<CostsByDepartmentReport>('/reports/costs-by-department');
  },

  async getCostsByEmployeeReport(department?: string, minCost?: number, limit: number = 100): Promise<CostsByEmployeeReport> {
    const params = new URLSearchParams();
    if (department) params.set('department', department);
    if (minCost !== undefined) params.set('min_cost', minCost.toString());
    params.set('limit', limit.toString());
    return fetchApi<CostsByEmployeeReport>(`/reports/costs-by-employee?${params.toString()}`);
  },

  // License Lifecycle Reports
  async getExpiringLicensesReport(days: number = 90): Promise<ExpiringLicensesReport> {
    return fetchApi<ExpiringLicensesReport>(`/reports/expiring-licenses?days=${days}`);
  },

  async getCancelledLicensesReport(): Promise<CancelledLicensesReport> {
    return fetchApi<CancelledLicensesReport>('/reports/cancelled-licenses');
  },

  async getLicenseLifecycleOverview(): Promise<LicenseLifecycleOverview> {
    return fetchApi<LicenseLifecycleOverview>('/reports/lifecycle-overview');
  },

  // Cancellation & Renewal
  async cancelLicense(licenseId: string, request: CancellationRequest): Promise<CancellationResponse> {
    return fetchApi<CancellationResponse>(`/licenses/${licenseId}/cancel`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async renewLicense(licenseId: string, request: RenewRequest): Promise<{ success: boolean; expires_at?: string; status: string }> {
    return fetchApi<{ success: boolean; expires_at?: string; status: string }>(`/licenses/${licenseId}/renew`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async setLicenseNeedsReorder(licenseId: string, needsReorder: boolean): Promise<{ success: boolean; needs_reorder: boolean }> {
    return fetchApi<{ success: boolean; needs_reorder: boolean }>(`/licenses/${licenseId}/needs-reorder`, {
      method: 'PATCH',
      body: JSON.stringify({ needs_reorder: needsReorder }),
    });
  },

  async cancelPackage(packageId: string, request: CancellationRequest): Promise<CancellationResponse> {
    return fetchApi<CancellationResponse>(`/packages/${packageId}/cancel`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async renewPackage(packageId: string, request: RenewRequest): Promise<{ success: boolean; contract_end?: string; status: string }> {
    return fetchApi<{ success: boolean; contract_end?: string; status: string }>(`/packages/${packageId}/renew`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async setPackageNeedsReorder(packageId: string, needsReorder: boolean): Promise<{ success: boolean; needs_reorder: boolean }> {
    return fetchApi<{ success: boolean; needs_reorder: boolean }>(`/packages/${packageId}/needs-reorder`, {
      method: 'PATCH',
      body: JSON.stringify({ needs_reorder: needsReorder }),
    });
  },

  async cancelOrgLicense(orgLicenseId: string, request: CancellationRequest): Promise<CancellationResponse> {
    return fetchApi<CancellationResponse>(`/org-licenses/${orgLicenseId}/cancel`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Departments
  async getDepartments(): Promise<string[]> {
    return fetchApi<string[]>('/users/employees/departments');
  },

  // Company Domains
  async getCompanyDomains(): Promise<string[]> {
    const response = await fetchApi<{ domains: string[] }>('/settings/company-domains');
    return response.domains;
  },

  async setCompanyDomains(domains: string[]): Promise<string[]> {
    const response = await fetchApi<{ domains: string[] }>('/settings/company-domains', {
      method: 'PUT',
      body: JSON.stringify({ domains }),
    });
    return response.domains;
  },

  // Notification Rules (Slack)
  async getNotificationRules(): Promise<NotificationRule[]> {
    return fetchApi<NotificationRule[]>('/settings/notifications/rules');
  },

  async createNotificationRule(data: {
    event_type: string;
    slack_channel: string;
    template?: string;
  }): Promise<NotificationRule> {
    return fetchApi<NotificationRule>('/settings/notifications/rules', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateNotificationRule(
    ruleId: string,
    data: {
      slack_channel?: string;
      template?: string;
      enabled?: boolean;
    }
  ): Promise<NotificationRule> {
    return fetchApi<NotificationRule>(`/settings/notifications/rules/${ruleId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteNotificationRule(ruleId: string): Promise<void> {
    await fetchApi(`/settings/notifications/rules/${ruleId}`, { method: 'DELETE' });
  },

  // Slack Settings
  async getSlackConfig(): Promise<{ webhook_url?: string; bot_token?: string; configured: boolean }> {
    const response = await fetchApi<SlackConfig | null>('/settings/slack');
    if (!response) {
      return { configured: false };
    }
    return {
      webhook_url: response.webhook_url,
      bot_token: response.bot_token ? '••••••••' : undefined,
      configured: !!response.bot_token,
    };
  },

  async setSlackConfig(data: { bot_token: string }): Promise<void> {
    await fetchApi('/settings/slack', {
      method: 'PUT',
      body: JSON.stringify({ value: data }),
    });
  },

  async testSlackNotification(channel: string): Promise<{ success: boolean; message: string }> {
    return fetchApi<{ success: boolean; message: string }>('/settings/notifications/test', {
      method: 'POST',
      body: JSON.stringify({ channel }),
    });
  },

  // ============================================================================
  // Authentication
  // ============================================================================

  async login(email: string, password: string): Promise<LoginResponse> {
    // First get CSRF token for the login request
    const csrfTokenValue = await getCsrfToken();

    const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfTokenValue,
      },
      credentials: 'include', // Receive httpOnly cookies
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Login failed');
    }

    // Tokens are now stored in httpOnly cookies by the server
    return response.json();
  },

  async logout(): Promise<void> {
    try {
      // Server reads refresh token from httpOnly cookie
      await fetchApi('/auth/logout', {
        method: 'POST',
      });
    } catch {
      // Ignore errors during logout
    }
    // Cookies are cleared by the server
    // Clear CSRF token cache
    clearCsrfToken();
  },

  async logoutAllSessions(): Promise<{ sessions_revoked: number }> {
    const result = await fetchApi<{ sessions_revoked: number }>('/auth/logout-all', {
      method: 'POST',
    });

    // Clear CSRF token cache
    clearCsrfToken();

    return result;
  },

  async getCurrentUser(): Promise<CurrentUserInfo> {
    return fetchApi<CurrentUserInfo>('/auth/me');
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await fetchApi('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
  },

  // Profile Update
  async updateProfile(data: ProfileUpdateRequest): Promise<CurrentUserInfo> {
    return fetchApi<CurrentUserInfo>('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async uploadAvatar(file: File): Promise<{ picture_url: string; message: string }> {
    // Validate file before upload
    validateFileUpload(file, {
      maxSize: MAX_AVATAR_SIZE_BYTES,
      allowedTypes: ALLOWED_IMAGE_TYPES,
    });

    const formData = new FormData();
    formData.append('file', file);

    // Get CSRF token for file upload
    const csrfTokenValue = await getCsrfToken();

    const url = `${API_BASE}/api/v1/auth/me/avatar`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRF-Token': csrfTokenValue,
      },
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to upload avatar');
    }

    return response.json();
  },

  async deleteAvatar(): Promise<void> {
    await fetchApi('/auth/me/avatar', { method: 'DELETE' });
  },

  // User Notification Preferences
  async getNotificationPreferences(): Promise<UserNotificationPreferencesResponse> {
    return fetchApi<UserNotificationPreferencesResponse>('/auth/me/notification-preferences');
  },

  async updateNotificationPreferences(preferences: UserNotificationPreferenceUpdate[]): Promise<UserNotificationPreferencesResponse> {
    return fetchApi<UserNotificationPreferencesResponse>('/auth/me/notification-preferences', {
      method: 'PUT',
      body: JSON.stringify({ preferences }),
    });
  },

  async updateSingleNotificationPreference(
    eventType: string,
    data: UserNotificationPreferenceUpdate
  ): Promise<UserNotificationPreference> {
    return fetchApi<UserNotificationPreference>(`/auth/me/notification-preferences/${eventType}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  // ============================================================================
  // Threshold Settings
  // ============================================================================

  async getThresholdSettings(): Promise<ThresholdSettings> {
    return fetchApi<ThresholdSettings>('/settings/thresholds');
  },

  async updateThresholdSettings(settings: ThresholdSettings): Promise<ThresholdSettings> {
    return fetchApi<ThresholdSettings>('/settings/thresholds', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  },

  // ============================================================================
  // RBAC - Admin Users
  // ============================================================================

  async getAdminUsers(params: {
    page?: number;
    page_size?: number;
    search?: string;
    is_active?: boolean;
    role?: string;
  } = {}): Promise<AdminUserListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params.search) searchParams.set('search', params.search);
    if (params.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
    if (params.role) searchParams.set('role', params.role);

    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return fetchApi<AdminUserListResponse>(`/rbac/users${query}`);
  },

  async getAdminUser(userId: string): Promise<AdminUser> {
    return fetchApi<AdminUser>(`/rbac/users/${userId}`);
  },

  async createAdminUser(data: {
    email: string;
    name?: string;
    password: string;
    role_ids: string[];
  }): Promise<AdminUser> {
    // Convert role_ids to role_codes by fetching roles first
    const rolesResponse = await this.getRoles();
    const roleCodes = data.role_ids
      .map(id => rolesResponse.items.find(r => r.id === id)?.code)
      .filter((code): code is string => !!code);

    return fetchApi<AdminUser>('/rbac/users', {
      method: 'POST',
      body: JSON.stringify({
        email: data.email,
        name: data.name,
        password: data.password,
        role_codes: roleCodes,
      }),
    });
  },

  async updateAdminUser(userId: string, data: {
    name?: string;
    is_active?: boolean;
    role_ids?: string[];
  }): Promise<AdminUser> {
    let roleCodes: string[] | undefined;

    if (data.role_ids) {
      const rolesResponse = await this.getRoles();
      roleCodes = data.role_ids
        .map(id => rolesResponse.items.find(r => r.id === id)?.code)
        .filter((code): code is string => !!code);
    }

    return fetchApi<AdminUser>(`/rbac/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify({
        name: data.name,
        is_active: data.is_active,
        role_codes: roleCodes,
      }),
    });
  },

  async deleteAdminUser(userId: string): Promise<void> {
    await fetchApi(`/rbac/users/${userId}`, { method: 'DELETE' });
  },

  async resetAdminUserPassword(userId: string): Promise<{ temporary_password: string }> {
    return fetchApi<{ temporary_password: string }>(`/rbac/users/${userId}/reset-password`, {
      method: 'POST',
    });
  },

  async unlockAdminUser(userId: string): Promise<AdminUser> {
    return fetchApi<AdminUser>(`/rbac/users/${userId}/unlock`, {
      method: 'POST',
    });
  },

  async getAdminUserSessions(userId: string): Promise<{ sessions: UserSession[] }> {
    return fetchApi<{ sessions: UserSession[] }>(`/rbac/users/${userId}/sessions`);
  },

  async revokeAdminUserSession(userId: string, sessionId: string): Promise<void> {
    await fetchApi(`/rbac/users/${userId}/sessions/${sessionId}`, { method: 'DELETE' });
  },

  // ============================================================================
  // RBAC - Roles
  // ============================================================================

  async getRoles(): Promise<RoleListResponse> {
    return fetchApi<RoleListResponse>('/rbac/roles');
  },

  async getRole(roleId: string): Promise<Role> {
    return fetchApi<Role>(`/rbac/roles/${roleId}`);
  },

  async createRole(data: {
    code: string;
    name: string;
    description?: string;
    permission_ids: string[];
  }): Promise<Role> {
    // Convert permission_ids to permission_codes by fetching permissions first
    const permissionsResponse = await this.getPermissions();
    const permissionCodes = data.permission_ids
      .map(id => permissionsResponse.items.find(p => p.id === id)?.code)
      .filter((code): code is string => !!code);

    return fetchApi<Role>('/rbac/roles', {
      method: 'POST',
      body: JSON.stringify({
        code: data.code,
        name: data.name,
        description: data.description,
        permission_codes: permissionCodes,
      }),
    });
  },

  async updateRole(roleId: string, data: {
    name?: string;
    description?: string;
    permission_ids?: string[];
  }): Promise<Role> {
    let permissionCodes: string[] | undefined;

    if (data.permission_ids) {
      const permissionsResponse = await this.getPermissions();
      permissionCodes = data.permission_ids
        .map(id => permissionsResponse.items.find(p => p.id === id)?.code)
        .filter((code): code is string => !!code);
    }

    return fetchApi<Role>(`/rbac/roles/${roleId}`, {
      method: 'PUT',
      body: JSON.stringify({
        name: data.name,
        description: data.description,
        permission_codes: permissionCodes,
      }),
    });
  },

  async deleteRole(roleId: string): Promise<void> {
    await fetchApi(`/rbac/roles/${roleId}`, { method: 'DELETE' });
  },

  // ============================================================================
  // RBAC - Permissions
  // ============================================================================

  async getPermissions(): Promise<{ items: Permission[]; total: number }> {
    return fetchApi<{ items: Permission[]; total: number }>('/rbac/permissions');
  },

  async getPermissionsByCategory(): Promise<PermissionsByCategory> {
    // Backend returns array of {category, permissions}, convert to Record
    const data = await fetchApi<PermissionCategory[]>('/rbac/permissions/by-category');
    const result: PermissionsByCategory = {};
    for (const item of data) {
      result[item.category] = item.permissions;
    }
    return result;
  },

  // ============================================================================
  // Audit Logs
  // ============================================================================

  async getAuditLogs(params: {
    page?: number;
    page_size?: number;
    action?: string;
    resource_type?: string;
    admin_user_id?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
  } = {}): Promise<AuditLogListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params.action) searchParams.set('action', params.action);
    if (params.resource_type) searchParams.set('resource_type', params.resource_type);
    if (params.admin_user_id) searchParams.set('admin_user_id', params.admin_user_id);
    if (params.date_from) searchParams.set('date_from', params.date_from);
    if (params.date_to) searchParams.set('date_to', params.date_to);
    if (params.search) searchParams.set('search', params.search);

    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return fetchApi<AuditLogListResponse>(`/audit${query}`);
  },

  async getAuditLog(logId: string): Promise<AuditLogEntry> {
    return fetchApi<AuditLogEntry>(`/audit/${logId}`);
  },

  async getAuditResourceTypes(): Promise<string[]> {
    const response = await fetchApi<{ resource_types: string[] }>('/audit/resource-types');
    return response.resource_types;
  },

  async getAuditActions(): Promise<string[]> {
    const response = await fetchApi<{ actions: string[] }>('/audit/actions');
    return response.actions;
  },

  async getAuditUsers(): Promise<Array<{ id: string; email: string }>> {
    const response = await fetchApi<{ items: Array<{ id: string; email: string }> }>('/audit/users');
    return response.items;
  },

  async exportAuditLogs(params: {
    format?: 'csv' | 'json';
    limit?: number;
    action?: string;
    resource_type?: string;
    admin_user_id?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
  } = {}): Promise<Blob> {
    const searchParams = new URLSearchParams();
    searchParams.set('format', params.format || 'csv');
    if (params.limit) searchParams.set('limit', params.limit.toString());
    if (params.action) searchParams.set('action', params.action);
    if (params.resource_type) searchParams.set('resource_type', params.resource_type);
    if (params.admin_user_id) searchParams.set('admin_user_id', params.admin_user_id);
    if (params.date_from) searchParams.set('date_from', params.date_from);
    if (params.date_to) searchParams.set('date_to', params.date_to);
    if (params.search) searchParams.set('search', params.search);

    const response = await fetch(`${API_BASE}/api/v1/audit/export?${searchParams.toString()}`, {
      method: 'GET',
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Export failed');
    }

    return response.blob();
  },

  // ============================================================================
  // Exports
  // ============================================================================

  /**
   * Get export URL with query parameters.
   */
  getExportUrl(
    type: 'licenses' | 'costs' | 'full-report',
    format: 'csv' | 'excel',
    params?: { providerId?: string; department?: string; status?: string; startDate?: string; endDate?: string }
  ): string {
    const searchParams = new URLSearchParams();

    if (params?.providerId) searchParams.set('provider_id', params.providerId);
    if (params?.department) searchParams.set('department', params.department);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.startDate) searchParams.set('start_date', params.startDate);
    if (params?.endDate) searchParams.set('end_date', params.endDate);

    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';

    switch (type) {
      case 'licenses':
        return `${API_BASE}/api/v1/exports/licenses/csv${query}`;
      case 'costs':
        return `${API_BASE}/api/v1/exports/costs/csv${query}`;
      case 'full-report':
        return `${API_BASE}/api/v1/exports/full-report/excel`;
    }
  },

  /**
   * Download an export file.
   * Filename is sanitized to prevent path traversal and special characters.
   */
  async downloadExport(url: string, filename: string): Promise<void> {
    const response = await fetch(url, {
      method: 'GET',
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Export failed');
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    // Sanitize filename to prevent path traversal
    link.download = sanitizeFilename(filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  },

  // ============================================================================
  // Auth Helpers
  // ============================================================================

  /**
   * Check if user appears to be authenticated.
   * Note: This checks for the presence of the auth indicator cookie,
   * not the actual httpOnly token (which is not accessible from JS).
   * The server is the source of truth for authentication.
   */
  isAuthenticated(): boolean {
    if (typeof window === 'undefined') return false;
    // Check for auth indicator cookie (set alongside httpOnly tokens)
    // or check if we have a CSRF token (indicates active session)
    const hasCsrfCookie = document.cookie.includes('csrf_token=');
    return hasCsrfCookie;
  },

  /**
   * Clear client-side auth state.
   * Note: httpOnly cookies can only be cleared by the server via logout.
   */
  clearAuth(): void {
    csrfToken = null;
    // Note: httpOnly cookies are cleared server-side
  },

  /**
   * Fetch a fresh CSRF token. Call this after login or when CSRF errors occur.
   */
  async refreshCsrfToken(): Promise<string> {
    csrfToken = null;
    return getCsrfToken();
  },

  // ============================================================================
  // Backup & Restore
  // ============================================================================

  /**
   * Create an encrypted backup of all system data.
   * Returns the backup file as a Blob.
   */
  async createBackup(password: string): Promise<Blob> {
    const csrfTokenValue = await getCsrfToken();

    const response = await fetch(`${API_BASE}/api/v1/backup/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfTokenValue,
      },
      credentials: 'include',
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Backup failed' }));
      throw new Error(error.detail || 'Backup failed');
    }

    return response.blob();
  },

  /**
   * Restore system from an encrypted backup.
   * WARNING: This deletes ALL existing data!
   */
  async restoreBackup(file: File, password: string): Promise<BackupRestoreResponse> {
    const csrfTokenValue = await getCsrfToken();

    const formData = new FormData();
    formData.append('file', file);
    formData.append('password', password);

    const response = await fetch(`${API_BASE}/api/v1/backup/restore`, {
      method: 'POST',
      headers: {
        'X-CSRF-Token': csrfTokenValue,
      },
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Restore failed' }));
      throw new Error(error.detail || 'Restore failed');
    }

    return response.json();
  },

  /**
   * Get information about a backup file without decrypting.
   */
  async getBackupInfo(file: File): Promise<BackupInfoResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/api/v1/backup/info`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get backup info' }));
      throw new Error(error.detail || 'Failed to get backup info');
    }

    return response.json();
  },
};
