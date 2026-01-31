import { getRequestConfig } from 'next-intl/server';
import { cookies, headers } from 'next/headers';

export const locales = ['en', 'de'] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = 'en';

async function getMessages(locale: string) {
  try {
    return (await import(`../../messages/${locale}.json`)).default;
  } catch {
    return (await import(`../../messages/${defaultLocale}.json`)).default;
  }
}

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const headersList = await headers();

  // Try to get locale from cookie first
  let locale = cookieStore.get('locale')?.value;

  // Fall back to Accept-Language header
  if (!locale || !locales.includes(locale as Locale)) {
    const acceptLanguage = headersList.get('accept-language');
    if (acceptLanguage) {
      const preferredLocale = acceptLanguage
        .split(',')
        .map((lang) => lang.split(';')[0].trim().substring(0, 2))
        .find((lang) => locales.includes(lang as Locale));
      locale = preferredLocale || defaultLocale;
    } else {
      locale = defaultLocale;
    }
  }

  return {
    locale,
    messages: await getMessages(locale),
  };
});
