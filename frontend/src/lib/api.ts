import { getSession } from 'next-auth/react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

async function getAuthHeaders(): Promise<HeadersInit> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Get session and add authorization header if available
  const session = await getSession();
  if (session?.accessToken) {
    headers['Authorization'] = `Bearer ${session.accessToken}`;
  }

  return headers;
}

async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = await getAuthHeaders();
  const url = `${API_BASE}/api/v1${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
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

export interface Provider {
  id: string;
  name: string;
  display_name: string;
  enabled: boolean;
  config?: Record<string, any>;
  last_sync_at?: string;
  last_sync_status?: string;
  license_count: number;
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
  metadata?: Record<string, any>;
  synced_at: string;
  is_external_email?: boolean;
  employee_status?: string;
}

export interface LicenseListResponse {
  items: License[];
  total: number;
  page: number;
  page_size: number;
}

export interface Employee {
  id: string;
  hibob_id: string;
  email: string;
  full_name: string;
  department?: string;
  status: string;
  start_date?: string;
  termination_date?: string;
  avatar?: string;  // Base64 data URL or null
  license_count: number;
  synced_at: string;
}

export interface EmployeeListResponse {
  items: Employee[];
  total: number;
  page: number;
  page_size: number;
}

export interface InactiveLicenseEntry {
  license_id: string;
  provider_name: string;
  employee_name?: string;
  employee_email?: string;
  external_user_id: string;
  last_activity_at?: string;
  days_inactive: number;
  monthly_cost?: string;
}

export interface InactiveLicenseReport {
  threshold_days: number;
  total_inactive: number;
  potential_savings: string;
  currency: string;
  licenses: InactiveLicenseEntry[];
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

// Payment Methods
export interface PaymentMethod {
  id: string;
  name: string;
  type: string;  // credit_card, bank_account, stripe, paypal, invoice, other
  details: Record<string, any>;
  is_default: boolean;
  notes?: string | null;
  is_expiring: boolean;
  days_until_expiry?: number | null;
}

export interface PaymentMethodCreate {
  name: string;
  type: string;
  details: Record<string, any>;
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
}

export interface LicenseTypeInfo {
  license_type: string;
  count: number;
  pricing: LicenseTypePricing | null;
}

export interface SyncResponse {
  success: boolean;
  results: Record<string, any>;
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
    credentials: Record<string, any>;
    config?: Record<string, any>;
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
      credentials?: Record<string, any>;
      config?: Record<string, any>;
    }
  ): Promise<Provider> {
    return fetchApi<Provider>(`/providers/${providerId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async testProviderConnection(
    name: string,
    credentials: Record<string, any>
  ): Promise<TestConnectionResponse> {
    return fetchApi<TestConnectionResponse>('/providers/test-connection', {
      method: 'POST',
      body: JSON.stringify({ name, credentials }),
    });
  },

  async syncProvider(providerId: string): Promise<SyncResponse> {
    return fetchApi<SyncResponse>(`/providers/${providerId}/sync`, { method: 'POST' });
  },

  async getProviderLicenseTypes(providerId: string): Promise<{ license_types: LicenseTypeInfo[] }> {
    return fetchApi<{ license_types: LicenseTypeInfo[] }>(`/providers/${providerId}/license-types`);
  },

  async getProviderPricing(providerId: string): Promise<{ pricing: LicenseTypePricing[] }> {
    return fetchApi<{ pricing: LicenseTypePricing[] }>(`/providers/${providerId}/pricing`);
  },

  async updateProviderPricing(providerId: string, pricing: LicenseTypePricing[]): Promise<{ pricing: LicenseTypePricing[] }> {
    return fetchApi<{ pricing: LicenseTypePricing[] }>(`/providers/${providerId}/pricing`, {
      method: 'PUT',
      body: JSON.stringify({ pricing }),
    });
  },

  // Provider Files
  async getProviderFiles(providerId: string): Promise<{ items: ProviderFile[]; total: number }> {
    return fetchApi<{ items: ProviderFile[]; total: number }>(`/providers/${providerId}/files`);
  },

  async uploadProviderFile(providerId: string, file: File, description?: string, category?: string): Promise<ProviderFile> {
    const formData = new FormData();
    formData.append('file', file);
    if (description) formData.append('description', description);
    if (category) formData.append('category', category);

    const url = `${API_BASE}/api/v1/providers/${providerId}/files`;
    const response = await fetch(url, {
      method: 'POST',
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
    return fetchApi<License>(`/manual-licenses/${licenseId}/assign?employee_id=${employeeId}`, {
      method: 'POST',
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
    search?: string;
    sort_by?: string;
    sort_dir?: 'asc' | 'desc';
  }): Promise<EmployeeListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params.status) searchParams.set('status', params.status);
    if (params.department) searchParams.set('department', params.department);
    if (params.search) searchParams.set('search', params.search);
    if (params.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params.sort_dir) searchParams.set('sort_dir', params.sort_dir);

    return fetchApi<EmployeeListResponse>(`/users/employees?${searchParams.toString()}`);
  },

  async getEmployee(employeeId: string): Promise<Employee> {
    return fetchApi<Employee>(`/users/employees/${employeeId}`);
  },

  // Reports
  async getInactiveLicenseReport(days: number = 30, department?: string): Promise<InactiveLicenseReport> {
    const params = new URLSearchParams();
    params.set('days', days.toString());
    if (department) params.set('department', department);
    return fetchApi<InactiveLicenseReport>(`/reports/inactive?${params.toString()}`);
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
};
