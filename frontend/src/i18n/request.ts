import { getRequestConfig } from 'next-intl/server';
import { cookies, headers } from 'next/headers';
import {
  SUPPORTED_LOCALES,
  DEFAULT_LOCALE,
  detectLocaleFromHeader,
  type SupportedLocale,
} from '@/lib/locales';

// Re-export for backwards compatibility
export const locales = SUPPORTED_LOCALES;
export type Locale = SupportedLocale;
export const defaultLocale = DEFAULT_LOCALE;

async function getMessages(locale: string) {
  try {
    return (await import(`../../messages/${locale}.json`)).default;
  } catch {
    return (await import(`../../messages/${DEFAULT_LOCALE}.json`)).default;
  }
}

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const headersList = await headers();

  // Try to get locale from cookie first
  let locale = cookieStore.get('locale')?.value;

  // Fall back to Accept-Language header detection
  if (!locale || !SUPPORTED_LOCALES.includes(locale as SupportedLocale)) {
    const acceptLanguage = headersList.get('accept-language');
    locale = detectLocaleFromHeader(acceptLanguage);
  }

  return {
    locale,
    messages: await getMessages(locale),
    timeZone: 'Europe/Berlin',
  };
});
