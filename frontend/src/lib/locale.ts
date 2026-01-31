/**
 * Locale utilities for internationalization.
 *
 * Provides consistent locale handling across the application.
 * Detects user's preferred locale from browser settings.
 */

// Supported locales in the application
export const SUPPORTED_LOCALES = ['en-US', 'en-GB', 'de-DE', 'de-AT', 'de-CH', 'fr-FR', 'es-ES'] as const;
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

// Default locale as fallback
export const DEFAULT_LOCALE: SupportedLocale = 'en-US';

/**
 * Get the user's preferred locale from browser settings.
 * Falls back to DEFAULT_LOCALE if no supported locale is found.
 */
export function getUserLocale(): string {
  if (typeof window === 'undefined') {
    // Server-side rendering - use default
    return DEFAULT_LOCALE;
  }

  // Try to get from navigator
  const browserLocales = navigator.languages || [navigator.language];

  for (const locale of browserLocales) {
    // Check exact match
    if (SUPPORTED_LOCALES.includes(locale as SupportedLocale)) {
      return locale;
    }

    // Check language prefix match (e.g., 'de' matches 'de-DE')
    const langPrefix = locale.split('-')[0];
    const matchedLocale = SUPPORTED_LOCALES.find((supported) =>
      supported.startsWith(langPrefix + '-')
    );
    if (matchedLocale) {
      return matchedLocale;
    }
  }

  return DEFAULT_LOCALE;
}

// Cache the locale to avoid repeated lookups
let cachedLocale: string | null = null;

/**
 * Get the current locale (cached).
 * Call resetLocaleCache() if you need to refresh the cached value.
 */
export function getLocale(): string {
  if (cachedLocale === null) {
    cachedLocale = getUserLocale();
  }
  return cachedLocale;
}

/**
 * Reset the cached locale value.
 * Useful when locale preferences change.
 */
export function resetLocaleCache(): void {
  cachedLocale = null;
}
