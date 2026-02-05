/**
 * Locale configuration and detection utilities.
 * Single source of truth for supported locales.
 */

// Supported locales for the application
export const SUPPORTED_LOCALES = ['en', 'de'] as const;
export type SupportedLocale = typeof SUPPORTED_LOCALES[number];

// Default locale when none is detected
export const DEFAULT_LOCALE: SupportedLocale = 'en';

/**
 * Detect the preferred locale from an Accept-Language header.
 *
 * Parses the header value and returns the first supported locale found,
 * or the default locale if none match.
 *
 * @param acceptLanguageHeader - The Accept-Language header value
 * @returns The detected locale
 */
export function detectLocaleFromHeader(acceptLanguageHeader: string | null): SupportedLocale {
  if (!acceptLanguageHeader) {
    return DEFAULT_LOCALE;
  }

  // Parse Accept-Language header: "en-US,en;q=0.9,de;q=0.8" -> ["en", "de"]
  const preferredLocale = acceptLanguageHeader
    .split(',')
    .map((lang) => lang.split(';')[0].trim().substring(0, 2))
    .find((lang): lang is SupportedLocale =>
      SUPPORTED_LOCALES.includes(lang as SupportedLocale)
    );

  return preferredLocale ?? DEFAULT_LOCALE;
}
