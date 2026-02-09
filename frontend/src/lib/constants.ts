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
