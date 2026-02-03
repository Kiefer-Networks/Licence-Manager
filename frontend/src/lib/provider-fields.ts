/**
 * Provider credential field definitions.
 * Shared between provider creation and editing.
 */

export interface ProviderTypeDefinition {
  value: string;
  label: string;
  fields: string[];
  type?: 'api' | 'manual';
}

export const hrisProviderTypes: ProviderTypeDefinition[] = [
  { value: 'hibob', label: 'HiBob', fields: ['auth_token'] },
  { value: 'personio', label: 'Personio', fields: ['client_id', 'client_secret'] },
];

export const licenseProviderTypes: ProviderTypeDefinition[] = [
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
  { value: 'huggingface', label: 'Hugging Face', fields: ['access_token', 'organization'], type: 'api' },
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

export const allProviderTypes = [...hrisProviderTypes, ...licenseProviderTypes];

/**
 * Get credential fields for a provider type.
 */
export function getProviderFields(providerName: string): string[] {
  const provider = allProviderTypes.find(p => p.value === providerName);
  return provider?.fields || [];
}

/**
 * Keys for translatable credential field labels.
 */
export const FIELD_LABEL_KEYS: Record<string, string> = {
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
  organization: 'organization',
  server_url: 'serverUrl',
  service_account_json: 'serviceAccountJson',
  sign_in_address: 'signInAddress',
  technical_account_id: 'technicalAccountId',
  tenant_id: 'tenantId',
  user_token: 'userToken',
};

/**
 * Get translated field label.
 */
export function getFieldLabel(field: string, t: (key: string) => string): string {
  const key = FIELD_LABEL_KEYS[field];
  if (key) {
    return t(key);
  }
  return field.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
}

/**
 * Fields that should use a textarea instead of input.
 */
export const TEXTAREA_FIELDS = ['service_account_json'];

/**
 * Fields that should show as password type.
 * Note: URLs, IDs, and identifiers are NOT secrets.
 */
export const SECRET_FIELDS = [
  'access_token',
  'admin_api_key',
  'api_key',
  'api_secret',
  'api_token',
  'auth_token',
  'bot_token',
  'client_secret',
  'user_token',
  'service_account_json',
];

/**
 * Check if a field is a secret that should be masked.
 */
export function isSecretField(field: string): boolean {
  return SECRET_FIELDS.includes(field);
}
