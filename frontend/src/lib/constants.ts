/**
 * Application constants.
 * Centralized definitions to avoid duplication across components.
 */

/**
 * Provider types that support license removal via the UI.
 * These providers allow users to be removed directly from the license management interface.
 */
export const REMOVABLE_PROVIDERS = ['cursor'] as const;

/**
 * Type for removable provider names.
 */
export type RemovableProvider = (typeof REMOVABLE_PROVIDERS)[number];

/**
 * Check if a provider supports license removal.
 */
export function isRemovableProvider(providerType: string): boolean {
  return REMOVABLE_PROVIDERS.includes(providerType.toLowerCase() as RemovableProvider);
}

/**
 * Providers where licenses are tied to users (seat-based) vs transferable (license-based).
 * Seat-based: user IS the license holder, can only activate/deactivate.
 * License-based: licenses can be reassigned to different users.
 */
export const SEAT_BASED_PROVIDERS = [
  'slack',
  'cursor',
  'google_workspace',
  'microsoft',
  'figma',
  'miro',
  'github',
  'gitlab',
  'mattermost',
  'openai',
  '1password',
] as const;

/**
 * Type for seat-based provider names.
 */
export type SeatBasedProvider = (typeof SEAT_BASED_PROVIDERS)[number];

/**
 * Check if a provider uses seat-based licensing by default.
 */
export function isSeatBasedProvider(providerName: string): boolean {
  return SEAT_BASED_PROVIDERS.includes(providerName as SeatBasedProvider);
}

/**
 * License model options for provider settings.
 * Values correspond to the backend license_model enum.
 */
export const LICENSE_MODEL_OPTIONS = [
  { value: 'seat_based', labelKey: 'seatBased' },
  { value: 'license_based', labelKey: 'licenseBased' },
] as const;

/**
 * Figma-specific license type constants.
 * Used when the provider is Figma and license type needs manual selection.
 */
export const FIGMA_LICENSE_TYPES = [
  'Figma Viewer',
  'Figma Collaborator',
  'Figma Dev Mode',
  'Figma Full Seat',
] as const;
